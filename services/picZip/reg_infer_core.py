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
            "你是一个生产级正则表达式生成器。",
            "",
            "任务：",
            "我会提供多组 sample 和 result。",
            "你需要生成一个可在 JavaScript RegExp 中直接使用的正则表达式，用来从 sample 中提取 result。",
            "",
            "目标：",
            "1. 尽量泛化，不要只为当前样本硬编码。",
            "2. 尽量稳定、可维护、可解释。",
            "3. 优先返回简单、清晰、兼容性高的写法。",
            "4. 如果结果需要拼接多个命中片段，可以使用 g flag。",
            "5. 必须优先考虑线上可用性，避免使用低兼容、容易报错的特性。",
            "",
            "严格限制：",
            "1. 必须返回 JSON，不能返回任何额外文字。",
            '2. JSON 格式必须严格为：{"pattern":"","flags":"","explanation":""}',
            "3. pattern 里不要包含前后斜杠，只返回正则主体。",
            "4. flags 只能使用这些字符的任意组合：g i m s",
            "5. 必须优先使用命名捕获组：(?<capture>...)",
            "6. 不要使用以下特性：",
            r"   - \p{...}",
            r"   - \P{...}",
            r"   - \k<name>",
            "   - y",
            "   - u",
            "   - v",
            "   - d",
            "   - 复杂或可变长度 lookbehind",
            "   - 依赖特定运行时的实验性语法",
            "7. 如果不需要命名捕获组也能完成，请仍然优先包成 (?<capture>...)。",
            "8. explanation 必须用中文，简洁说明边界依据。",
            "9. 如果无法稳定生成，也必须返回你认为最稳妥、最简单、最不容易报错的表达式。",
            "10. 不要返回 Markdown，不要包裹 ```json。",
            "",
            "生成原则：",
            "1. 优先使用明确边界，如前后固定字符、分隔符、数字/字母范围。",
            "2. 优先使用非贪婪匹配，避免过宽。",
            "3. 优先使用字符类、锚点、分组，不要过度复杂化。",
            r'4. 若样本表现为“提取所有数字并拼接”，优先考虑 pattern: "(?<capture>\\d)"，flags: "g"。',
            r'5. 若样本表现为“提取单段连续数字”，优先考虑 pattern: "(?<capture>\\d+)"，flags: ""。',
            "6. 如果样本中存在不命中的情况，生成的表达式必须同时满足这些负样本。",
            "",
            "样本如下：",
            json.dumps(prompt_examples, ensure_ascii=False, indent=2),
        ]
    )


def build_regex_repair_prompt(
    examples: list[RegexSeedExample],
    *,
    previous_inference: dict[str, str],
    validation_error: str,
) -> str:
    prompt_examples = [
        {
            "sample": example.sample,
            "result": example.result,
        }
        for example in examples
    ]

    return "\n".join(
        [
            "你上一次生成的正则未通过校验，请修复后重新返回。",
            "仍然只能返回 JSON，格式必须严格为：",
            '{"pattern":"","flags":"","explanation":""}',
            "",
            "修复要求：",
            "1. 继续保持 JavaScript RegExp 兼容。",
            "2. flags 只能使用 g i m s。",
            "3. 优先使用命名捕获组 (?<capture>...)。",
            r"4. 禁止使用 \p{...}、\P{...}、\k<name>、u、y、v、d、复杂 lookbehind。",
            "5. 新结果必须能通过全部样本校验。",
            "6. 优先返回更简单、更稳定、更容易跨运行时兼容的写法。",
            "",
            "上一次返回：",
            json.dumps(previous_inference, ensure_ascii=False, indent=2),
            "",
            "校验错误：",
            validation_error,
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
    retried = False

    try:
        _validate_inference(inference, examples)
    except ValueError as first_error:
        retried = True
        retry_prompt = build_regex_repair_prompt(
            examples,
            previous_inference=inference,
            validation_error=str(first_error),
        )
        inference = _request_deepseek_inference(retry_prompt, model)
        _validate_inference(inference, examples)

    return {
        "inference": inference,
        "meta": {
            "provider": "deepseek",
            "model": model,
            "retried": retried,
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
    pattern = _to_python_regex_pattern(inference["pattern"])
    raw_flags = inference["flags"]
    flags = _parse_python_flags(raw_flags)
    is_global = "g" in raw_flags

    try:
        regex = re.compile(pattern, flags)
    except re.error as exc:
        raise ValueError(f"模型返回的正则无法编译: {exc}") from exc

    for example in examples:
        actual = _extract_with_regex(regex, example.sample, is_global=is_global)

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
        if flag == "g":
            continue
        if flag not in mapping:
            raise ValueError(f"暂不支持的正则 flag: {flag}")
        parsed |= mapping[flag]

    return parsed


def _to_python_regex_pattern(pattern: str) -> str:
    return re.sub(r"\(\?<([a-zA-Z_][a-zA-Z0-9_]*)>", r"(?P<\1>", pattern)


def _extract_with_regex(regex: re.Pattern[str], value: str, *, is_global: bool) -> str:
    if is_global:
        matched_chunks: list[str] = []
        for matched in regex.finditer(value):
            if "capture" in matched.groupdict():
                matched_chunks.append(matched.group("capture") or "")
            elif matched.lastindex:
                matched_chunks.append(matched.group(1) or "")
            else:
                matched_chunks.append(matched.group(0) or "")
        return "".join(matched_chunks)

    matched = regex.search(value)
    if not matched:
        return ""

    if "capture" in matched.groupdict():
        return matched.group("capture") or ""

    if matched.lastindex:
        return matched.group(1) or ""

    return matched.group(0) or ""
