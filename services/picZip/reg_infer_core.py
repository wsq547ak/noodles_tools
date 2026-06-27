from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from urllib import error, request


DEFAULT_DEEPSEEK_MODEL = "deepseek-v4-flash"
DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"


@dataclass(frozen=True)
class RegexSeedExample:
    sample: str
    result: str


def normalize_examples(raw_examples: list[dict[str, object]]) -> list[RegexSeedExample]:
    normalized: list[RegexSeedExample] = []

    for raw in raw_examples:
        sample = str(raw.get("sample", "")).strip()
        result = str(raw.get("result", "")).strip()
        if sample:
            normalized.append(RegexSeedExample(sample=sample, result=result))

    return normalized


def validate_examples(examples: list[RegexSeedExample]) -> None:
    if len(examples) < 2:
        raise ValueError("请至少填写 2 条样本。")


def build_regex_inference_prompt(examples: list[RegexSeedExample]) -> str:
    prompt_examples = [
        {
            "sample": example.sample,
            "result": example.result,
        }
        for example in examples
    ]

    return "\n".join(
        [
            "你是一个正则表达式生成器。",
            "我会给你多组 sample 和 result，请生成一条尽量简洁、可复用的正则表达式。",
            "要求：",
            "1. 必须使用命名捕获组 (?<capture>...)",
            '2. 仅返回 JSON：{"pattern":"","flags":"","explanation":""}',
            "3. pattern 不要带前后斜杠",
            "4. explanation 用中文简要说明边界选择依据",
            "5. 如果无法稳定生成，也返回你认为最合理的表达式",
            "",
            "样本如下：",
            json.dumps(prompt_examples, ensure_ascii=False, indent=2),
        ]
    )


def infer_regex_with_ai(
    examples: list[RegexSeedExample],
    *,
    model: str = DEFAULT_DEEPSEEK_MODEL,
) -> dict[str, object]:
    validate_examples(examples)
    prompt = build_regex_inference_prompt(examples)
    inference = _request_deepseek_inference(prompt, model)
    _validate_inference(inference, examples)

    return {
        "inference": inference,
        "meta": {
            "provider": "deepseek",
            "model": model,
        },
    }


def _request_deepseek_inference(prompt: str, model: str) -> dict[str, str]:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise ValueError("缺少 DEEPSEEK_API_KEY 环境变量。")

    base_url = os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_DEEPSEEK_BASE_URL).rstrip("/")
    endpoint = f"{base_url}/chat/completions"
    payload = {
        "model": model,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是一个正则表达式生成器。"
                    "你只能返回 JSON，对象必须包含 pattern、flags、explanation 三个字段。"
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        endpoint,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=60) as response:
            response_body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"DeepSeek 请求失败: {exc.code} {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"DeepSeek 连接失败: {exc.reason}") from exc

    raw = json.loads(response_body)
    content = (
        raw.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )
    result = _parse_model_json(content)
    pattern = str(result.get("pattern", "")).strip()
    flags = str(result.get("flags", "")).strip()
    explanation = str(result.get("explanation", "")).strip()

    if not pattern:
        raise ValueError("模型没有返回有效的 pattern。")

    return {
        "pattern": pattern,
        "flags": flags,
        "explanation": explanation or "由 AI 根据样本推导生成。",
    }


def _parse_model_json(content: str) -> dict[str, object]:
    trimmed = content.strip()

    if trimmed.startswith("```"):
        trimmed = re.sub(r"^```(?:json)?\s*", "", trimmed)
        trimmed = re.sub(r"\s*```$", "", trimmed)

    try:
        parsed = json.loads(trimmed)
    except json.JSONDecodeError as exc:
        raise ValueError(f"模型返回的内容不是有效 JSON: {content}") from exc

    if not isinstance(parsed, dict):
        raise ValueError("模型返回的 JSON 不是对象。")

    return parsed


def _validate_inference(
    inference: dict[str, str],
    examples: list[RegexSeedExample],
) -> None:
    pattern = inference["pattern"]
    flags = _parse_python_flags(inference["flags"])

    try:
        regex = re.compile(pattern, flags)
    except re.error as exc:
        raise ValueError(f"模型返回的正则无法编译: {exc}") from exc

    for example in examples:
        matched = regex.search(example.sample)
        if not matched:
            actual = ""
        elif "capture" in matched.groupdict():
            actual = matched.group("capture") or ""
        elif matched.lastindex:
            actual = matched.group(1) or ""
        else:
            actual = matched.group(0) or ""

        if actual != example.result:
            raise ValueError(
                "模型返回的正则未通过样本校验: "
                f"sample={example.sample!r}, expected={example.result!r}, actual={actual!r}"
            )


def _parse_python_flags(flag_text: str) -> int:
    mapping = {
        "i": re.IGNORECASE,
        "m": re.MULTILINE,
        "s": re.DOTALL,
    }
    parsed = 0

    for flag in flag_text:
        if flag not in mapping:
            raise ValueError(f"暂不支持的正则 flag: {flag}")
        parsed |= mapping[flag]

    return parsed
