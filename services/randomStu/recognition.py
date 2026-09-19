from __future__ import annotations

import io
import json
import os
import re
import ssl
import uuid
from urllib import error, request
from urllib.parse import quote

import certifi
from PIL import Image, ImageOps, UnidentifiedImageError

DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_DEEPSEEK_MODEL = "deepseek-flash"
MAX_IMAGE_SIZE = 12 * 1024 * 1024
SUPPORTED_MIME_TYPES = {"image/gif", "image/jpeg", "image/png", "image/webp"}


def recognize_students(
    image_data: bytes,
    mime_type: str,
    *,
    model: str = DEFAULT_DEEPSEEK_MODEL,
) -> dict[str, object]:
    if mime_type not in SUPPORTED_MIME_TYPES:
        raise ValueError("仅支持 PNG、JPEG、WebP 和 GIF 图片。")
    if not image_data:
        raise ValueError("上传的图片为空。")
    if len(image_data) > MAX_IMAGE_SIZE:
        raise ValueError("图片不能超过 12 MB。")

    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise ValueError("缺少 DEEPSEEK_API_KEY 环境变量。")

    base_url = os.environ.get(
        "DEEPSEEK_BASE_URL", DEFAULT_DEEPSEEK_BASE_URL
    ).rstrip("/")
    low_detail_image = prepare_low_detail_image(image_data)
    file_id = upload_image_file(low_detail_image, api_key, base_url)
    try:
        content = request_recognition(file_id, api_key, base_url, model)
    finally:
        delete_uploaded_file(file_id, api_key, base_url)

    students = parse_students_json(content)
    if not students:
        raise ValueError("没有从图片中识别到有效的学生姓名。")

    return {
        "students": students,
        "meta": {
            "provider": "deepseek",
            "model": model,
            "count": len(students),
            "transport": "files_api",
            "detail": "low",
        },
    }


def prepare_low_detail_image(image_data: bytes) -> bytes:
    try:
        with Image.open(io.BytesIO(image_data)) as source:
            source.seek(0)
            image = ImageOps.exif_transpose(source).convert("RGBA")
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("上传的文件不是有效图片。") from exc

    image.thumbnail((512, 512), Image.Resampling.LANCZOS)
    background = Image.new("RGBA", image.size, "white")
    background.alpha_composite(image)
    output = io.BytesIO()
    background.convert("RGB").save(output, format="PNG", optimize=True)
    return output.getvalue()


def upload_image_file(image_data: bytes, api_key: str, base_url: str) -> str:
    boundary = f"----randomstu-{uuid.uuid4().hex}"
    fields = [
        ("purpose", "user_data"),
        ("expires_after[anchor]", "created_at"),
        ("expires_after[seconds]", "3600"),
    ]
    chunks: list[bytes] = []
    for name, value in fields:
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                value.encode(),
                b"\r\n",
            ]
        )
    chunks.extend(
        [
            f"--{boundary}\r\n".encode(),
            b'Content-Disposition: form-data; name="file"; filename="roster-low.png"\r\n',
            b"Content-Type: image/png\r\n\r\n",
            image_data,
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )
    api_request = request.Request(
        f"{base_url}/files",
        data=b"".join(chunks),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    raw = send_json_request(api_request, timeout=120, action="上传图片")
    file_id = str(raw.get("id", "")).strip()
    if not file_id.startswith("file-api-"):
        raise RuntimeError("DeepSeek Files API 没有返回有效的 file_id。")
    return file_id


def request_recognition(
    file_id: str,
    api_key: str,
    base_url: str,
    model: str,
) -> str:
    payload = {
        "model": model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是学生名单表格识别助手。你只能输出完整、合法的 JSON，"
                    "不能输出 Markdown、解释文字或省略号。"
                ),
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": build_recognition_prompt()},
                    {"type": "file", "file_id": file_id},
                ],
            },
        ],
    }
    api_request = request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    raw = send_json_request(api_request, timeout=120, action="识别名单")
    return str(raw.get("choices", [{}])[0].get("message", {}).get("content", ""))


def delete_uploaded_file(file_id: str, api_key: str, base_url: str) -> None:
    api_request = request.Request(
        f"{base_url}/files/{quote(file_id, safe='')}",
        headers={"Authorization": f"Bearer {api_key}"},
        method="DELETE",
    )
    try:
        send_json_request(api_request, timeout=30, action="删除临时图片")
    except (RuntimeError, ValueError):
        # The one-hour Files API expiry remains the cleanup fallback.
        return


def send_json_request(
    api_request: request.Request,
    *,
    timeout: int,
    action: str,
) -> dict[str, object]:
    try:
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        with request.urlopen(api_request, timeout=timeout, context=ssl_context) as response:
            response_body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"DeepSeek {action}失败: {exc.code} {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"DeepSeek 连接失败: {exc.reason}") from exc

    try:
        parsed = json.loads(response_body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"DeepSeek {action}返回了无效 JSON。") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError(f"DeepSeek {action}返回格式错误。")
    return parsed


def build_recognition_prompt() -> str:
    return "\n".join(
        [
            "请识别图片中的学生名单表格，提取每一行的序号和姓名。",
            "务必检查整张图片，从第一行识别到最后一行，不得只返回部分内容。",
            "忽略班级、标题、性别、成绩、备注等其他字段。",
            "看不清的序号使用空字符串；看不清姓名的行不要猜测，也不要输出。",
            "序号必须作为字符串输出，以保留 001 之类的前导零。",
            "必须返回完整且可解析的 JSON，禁止 Markdown、注释、省略号和额外文字。",
            'JSON 格式严格为：{"students":[{"number":"1","name":"张三"}]}',
        ]
    )


def parse_students_json(content: str) -> list[dict[str, str]]:
    trimmed = content.strip()
    if trimmed.startswith("```"):
        trimmed = re.sub(r"^```(?:json)?\s*", "", trimmed)
        trimmed = re.sub(r"\s*```$", "", trimmed)

    try:
        parsed = json.loads(trimmed)
    except json.JSONDecodeError as exc:
        raise ValueError("模型返回的名单不是有效 JSON。") from exc

    raw_students = parsed.get("students") if isinstance(parsed, dict) else None
    if not isinstance(raw_students, list):
        raise ValueError("模型返回的 JSON 缺少 students 数组。")

    students: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for raw_student in raw_students[:500]:
        if not isinstance(raw_student, dict):
            continue
        number = str(raw_student.get("number", "")).strip()
        name = str(raw_student.get("name", "")).strip()
        if not name:
            continue
        identity = (number, name)
        if identity in seen:
            continue
        seen.add(identity)
        students.append({"number": number, "name": name})

    return students
