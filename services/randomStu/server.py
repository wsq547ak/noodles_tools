from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from services.randomStu.recognition import (
    DEFAULT_DEEPSEEK_MODEL,
    MAX_IMAGE_SIZE,
    recognize_students,
)

ENV_FILE = Path(__file__).with_name(".env")


class RandomStuRequestHandler(BaseHTTPRequestHandler):
    server_version = "RandomStu/0.1"

    def do_GET(self) -> None:
        if urlparse(self.path).path != "/tools/health":
            self._write_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return
        self._write_json(
            HTTPStatus.OK,
            {"status": "ok", "service": "randomStu", "model": DEFAULT_DEEPSEEK_MODEL},
        )

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/tools/randomStu/recognize":
            self._write_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return
        self._handle_recognize()

    def _handle_recognize(self) -> None:
        content_length = int(self.headers.get("content-length", "0"))
        if content_length > MAX_IMAGE_SIZE:
            self._write_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "图片不能超过 12 MB。"})
            return

        mime_type = self.headers.get("content-type", "").split(";", 1)[0].strip()
        image_data = self.rfile.read(content_length)
        try:
            result = recognize_students(image_data, mime_type)
        except ValueError as exc:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        except Exception as exc:
            self._write_json(HTTPStatus.BAD_GATEWAY, {"error": str(exc)})
            return

        self._write_json(HTTPStatus.OK, result)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _write_json(self, status: HTTPStatus, payload: dict[str, object]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def load_local_env() -> None:
    if not ENV_FILE.exists():
        return
    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def run(host: str = "127.0.0.1", port: int = 5002) -> None:
    server = ThreadingHTTPServer((host, port), RandomStuRequestHandler)
    print(f"RandomStu service listening on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    load_local_env()
    run(
        host=os.environ.get("RANDOMSTU_HOST", "127.0.0.1"),
        port=int(os.environ.get("RANDOMSTU_PORT", "5002")),
    )
