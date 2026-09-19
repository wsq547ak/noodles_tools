from __future__ import annotations

import json
import os
import threading
import time
from http.cookies import SimpleCookie
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from services.picZip.core import (
    SUPPORTED_MIME_TYPES,
    CompressionProfile,
    PngCompressionMode,
    compress_image_bytes,
)
from services.picZip.reg_infer_core import (
    DEFAULT_DEEPSEEK_MODEL,
    infer_regex_with_ai,
    normalize_examples,
)
from services.randomStu.recognition import MAX_IMAGE_SIZE, recognize_students
from services.randomStu.auth import configured_password_hash, verify_password
from services.randomStu.store import RandomStuStore, RevisionConflictError

ENV_FILE = Path(__file__).with_name(".env")
RANDOM_STU_ENV_FILE = Path(__file__).parents[1] / "randomStu" / ".env"
SESSION_COOKIE = "randomstu_session"
MAX_STATE_BODY_SIZE = 2 * 1024 * 1024
LOGIN_WINDOW_SECONDS = 60
MAX_LOGIN_ATTEMPTS = 5
_login_attempts: dict[str, list[float]] = {}
_login_lock = threading.Lock()


class CompressionRequestHandler(BaseHTTPRequestHandler):
    server_version = "TinyToolsBackend/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/tools/randomStu/session":
            self._handle_random_stu_session()
            return

        if parsed.path == "/tools/randomStu/data":
            self._handle_random_stu_get_data()
            return

        if parsed.path != "/tools/health":
            self._write_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return

        self._write_json(
            HTTPStatus.OK,
            {
                "status": "ok",
                "service": "toolsBackend",
                "modules": ["picZip", "regInfer", "randomStu"],
                "regInferModel": DEFAULT_DEEPSEEK_MODEL,
            },
        )

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/tools/pic_compress":
            self._handle_pic_compress()
            return

        if parsed.path == "/tools/regInfer/ai":
            self._handle_reg_infer_ai()
            return

        if parsed.path == "/tools/randomStu/recognize":
            if not self._require_random_stu_session():
                return
            self._handle_random_stu_recognize()
            return

        if parsed.path == "/tools/randomStu/login":
            self._handle_random_stu_login()
            return

        if parsed.path == "/tools/randomStu/logout":
            self._handle_random_stu_logout()
            return

        self._write_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def do_PUT(self) -> None:
        if urlparse(self.path).path == "/tools/randomStu/data":
            self._handle_random_stu_save_data()
            return
        self._write_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def _handle_pic_compress(self) -> None:
        content_type = self.headers.get("content-type")
        if content_type not in SUPPORTED_MIME_TYPES:
            self._write_json(
                HTTPStatus.BAD_REQUEST,
                {"error": "Only image/png and image/jpeg are supported."},
            )
            return

        content_length = int(self.headers.get("content-length", "0"))
        payload = self.rfile.read(content_length)
        profile_name = self.headers.get("x-compression-profile", "aggressive")
        png_mode_name = self.headers.get("x-png-compression-mode", "strict")

        try:
            profile = CompressionProfile(profile_name)
            png_mode = PngCompressionMode(png_mode_name)
            result = compress_image_bytes(
                payload,
                content_type,
                profile=profile,
                png_mode=png_mode,
            )
        except ValueError as error:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return
        except Exception as error:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return

        self._write_json(
            HTTPStatus.OK,
            {
                "width": result.width,
                "height": result.height,
                "originalSize": result.original_size,
                "compressedSize": result.compressed_size,
                "bytesSaved": result.bytes_saved,
                "compressionRatio": result.compression_ratio,
                "base64Data": result.base64_data,
            },
        )

    def _handle_reg_infer_ai(self) -> None:
        content_length = int(self.headers.get("content-length", "0"))
        payload = self.rfile.read(content_length)

        try:
            body = json.loads(payload.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": "请求体不是有效 JSON。"})
            return

        examples = normalize_examples(body.get("examples", []))
        model = str(body.get("model") or DEFAULT_DEEPSEEK_MODEL).strip()

        try:
            result = infer_regex_with_ai(examples, model=model)
        except ValueError as error:
            self._write_json(
                HTTPStatus.BAD_REQUEST,
                {
                    "error": "样本边界不够明确，或推导结果不稳定。请补充 1 到 2 条更有区分度的样本后再试。",
                    "detail": str(error),
                },
            )
            return
        except NotImplementedError as error:
            self._write_json(HTTPStatus.NOT_IMPLEMENTED, {"error": str(error)})
            return
        except Exception as error:
            self._write_json(HTTPStatus.BAD_GATEWAY, {"error": str(error)})
            return

        self._write_json(HTTPStatus.OK, result)

    def _handle_random_stu_recognize(self) -> None:
        content_length = int(self.headers.get("content-length", "0"))
        if content_length > MAX_IMAGE_SIZE:
            self._write_json(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                {"error": "图片不能超过 12 MB。"},
            )
            return

        mime_type = self.headers.get("content-type", "").split(";", 1)[0].strip()
        image_data = self.rfile.read(content_length)
        try:
            result = recognize_students(image_data, mime_type)
        except ValueError as error:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return
        except Exception as error:
            self._write_json(HTTPStatus.BAD_GATEWAY, {"error": str(error)})
            return

        self._write_json(HTTPStatus.OK, result)

    def _handle_random_stu_session(self) -> None:
        store = RandomStuStore()
        authenticated = store.has_session(self._session_token())
        self._write_json(HTTPStatus.OK, {"authenticated": authenticated})

    def _handle_random_stu_login(self) -> None:
        client_key = self.headers.get("x-forwarded-for", self.client_address[0]).split(",", 1)[0].strip()
        if self._login_rate_limited(client_key):
            self._write_json(HTTPStatus.TOO_MANY_REQUESTS, {"error": "尝试次数过多，请一分钟后再试。"})
            return

        try:
            body = self._read_json_body(max_size=4_096)
        except ValueError as error:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return
        password = str(body.get("password", ""))
        password_hash = configured_password_hash()
        if not password_hash:
            self._write_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "服务器尚未配置访问密码。"})
            return
        if len(password) > 256 or not verify_password(password, password_hash):
            self._record_login_failure(client_key)
            self._write_json(HTTPStatus.UNAUTHORIZED, {"error": "密码错误，请重新输入。"})
            return

        self._clear_login_failures(client_key)
        token = RandomStuStore().create_session()
        self._write_json(
            HTTPStatus.OK,
            {"authenticated": True},
            headers={"Set-Cookie": self._session_cookie(token)},
        )

    def _handle_random_stu_logout(self) -> None:
        token = self._session_token()
        RandomStuStore().delete_session(token)
        self._write_json(
            HTTPStatus.OK,
            {"authenticated": False},
            headers={"Set-Cookie": self._session_cookie("", expired=True)},
        )

    def _handle_random_stu_get_data(self) -> None:
        if not self._require_random_stu_session():
            return
        state = RandomStuStore().get_state()
        self._write_json(
            HTTPStatus.OK,
            {"data": state.data, "revision": state.revision, "updatedAt": state.updated_at},
        )

    def _handle_random_stu_save_data(self) -> None:
        if not self._require_random_stu_session():
            return
        try:
            body = self._read_json_body(max_size=MAX_STATE_BODY_SIZE)
            data = body.get("data")
            expected_revision = int(body.get("revision", -1))
            if not isinstance(data, dict) or expected_revision < 0:
                raise ValueError("同步请求格式无效。")
            state = RandomStuStore().save_state(data, expected_revision)
        except RevisionConflictError as error:
            self._write_json(
                HTTPStatus.CONFLICT,
                {"error": str(error), "revision": error.current_revision},
            )
            return
        except (ValueError, TypeError) as error:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return

        self._write_json(
            HTTPStatus.OK,
            {"data": state.data, "revision": state.revision, "updatedAt": state.updated_at},
        )

    def _require_random_stu_session(self) -> bool:
        if RandomStuStore().has_session(self._session_token()):
            return True
        self._write_json(HTTPStatus.UNAUTHORIZED, {"error": "登录已失效，请重新输入密码。"})
        return False

    def _session_token(self) -> str:
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("cookie", ""))
        except Exception:
            return ""
        morsel = cookie.get(SESSION_COOKIE)
        return morsel.value if morsel else ""

    def _session_cookie(self, token: str, *, expired: bool = False) -> str:
        parts = [f"{SESSION_COOKIE}={token}", "Path=/", "HttpOnly", "SameSite=Strict"]
        if os.environ.get("RANDOMSTU_COOKIE_SECURE", "").lower() in {"1", "true", "yes"}:
            parts.append("Secure")
        if expired:
            parts.extend(["Max-Age=0", "Expires=Thu, 01 Jan 1970 00:00:00 GMT"])
        return "; ".join(parts)

    def _read_json_body(self, *, max_size: int) -> dict[str, object]:
        content_length = int(self.headers.get("content-length", "0"))
        if content_length <= 0 or content_length > max_size:
            raise ValueError("请求内容为空或过大。")
        try:
            body = json.loads(self.rfile.read(content_length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("请求内容不是有效 JSON。") from error
        if not isinstance(body, dict):
            raise ValueError("请求内容必须是 JSON 对象。")
        return body

    def _login_rate_limited(self, client_key: str) -> bool:
        cutoff = time.time() - LOGIN_WINDOW_SECONDS
        with _login_lock:
            attempts = [attempt for attempt in _login_attempts.get(client_key, []) if attempt > cutoff]
            _login_attempts[client_key] = attempts
            return len(attempts) >= MAX_LOGIN_ATTEMPTS

    def _record_login_failure(self, client_key: str) -> None:
        with _login_lock:
            _login_attempts.setdefault(client_key, []).append(time.time())

    def _clear_login_failures(self, client_key: str) -> None:
        with _login_lock:
            _login_attempts.pop(client_key, None)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _write_json(
        self,
        status: HTTPStatus,
        payload: dict[str, object],
        *,
        headers: dict[str, str] | None = None,
    ) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)


def run(host: str = "127.0.0.1", port: int = 5001) -> None:
    server = ThreadingHTTPServer((host, port), CompressionRequestHandler)
    print(f"Tools backend listening on http://{host}:{port}")
    server.serve_forever()


def load_local_env() -> None:
    for env_file in (ENV_FILE, RANDOM_STU_ENV_FILE):
        if not env_file.exists():
            continue
        for raw_line in env_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if value.strip():
                os.environ.setdefault(key.strip(), value.strip())


if __name__ == "__main__":
    load_local_env()
    run(
        host=os.environ.get("PICZIP_HOST", "127.0.0.1"),
        port=int(os.environ.get("PICZIP_PORT", "5001")),
    )
