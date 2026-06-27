from __future__ import annotations

import json
import os
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

ENV_FILE = Path(__file__).with_name(".env")


class CompressionRequestHandler(BaseHTTPRequestHandler):
    server_version = "TinyCompressor/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/tools/health":
            self._write_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return

        self._write_json(
            HTTPStatus.OK,
            {
                "status": "ok",
                "service": "picZip",
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
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return
        except NotImplementedError as error:
            self._write_json(HTTPStatus.NOT_IMPLEMENTED, {"error": str(error)})
            return
        except Exception as error:
            self._write_json(HTTPStatus.BAD_GATEWAY, {"error": str(error)})
            return

        self._write_json(HTTPStatus.OK, result)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _write_json(self, status: HTTPStatus, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run(host: str = "127.0.0.1", port: int = 5001) -> None:
    server = ThreadingHTTPServer((host, port), CompressionRequestHandler)
    print(f"Compression service listening on http://{host}:{port}")
    server.serve_forever()


def load_local_env() -> None:
    if not ENV_FILE.exists():
        return

    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


if __name__ == "__main__":
    load_local_env()
    run(
        host=os.environ.get("PICZIP_HOST", "127.0.0.1"),
        port=int(os.environ.get("PICZIP_PORT", "5001")),
    )
