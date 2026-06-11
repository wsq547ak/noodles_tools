from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from services.picZip.core import (
    SUPPORTED_MIME_TYPES,
    CompressionProfile,
    PngCompressionMode,
    compress_image_bytes,
)


class CompressionRequestHandler(BaseHTTPRequestHandler):
    server_version = "TinyCompressor/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/health":
            self._write_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return

        self._write_json(HTTPStatus.OK, {"status": "ok"})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/compress":
            self._write_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return

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


if __name__ == "__main__":
    run(
        host=os.environ.get("PICZIP_HOST", "127.0.0.1"),
        port=int(os.environ.get("PICZIP_PORT", "5001")),
    )
