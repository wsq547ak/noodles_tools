from __future__ import annotations

import base64
import io
import shutil
import subprocess
from dataclasses import dataclass
from enum import StrEnum

from PIL import Image
from PIL import ImageChops
from PIL import PngImagePlugin

SUPPORTED_MIME_TYPES = {"image/png", "image/jpeg"}


class CompressionProfile(StrEnum):
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


class PngCompressionMode(StrEnum):
    STRICT = "strict"
    VISUAL = "visual"


@dataclass(frozen=True)
class CompressionOutput:
    data: bytes
    mime_type: str
    width: int
    height: int
    original_size: int
    compressed_size: int

    @property
    def bytes_saved(self) -> int:
        return self.original_size - self.compressed_size

    @property
    def compression_ratio(self) -> float:
        if self.original_size == 0:
            return 0.0
        return (self.bytes_saved / self.original_size) * 100

    @property
    def base64_data(self) -> str:
        return base64.b64encode(self.data).decode("ascii")


def _save_png(image: Image.Image, profile: CompressionProfile) -> bytes:
    del profile
    pnginfo = _build_pnginfo(image)
    save_kwargs: dict[str, object] = {
        "optimize": True,
        "compress_level": 9,
    }
    if pnginfo is not None:
        save_kwargs["pnginfo"] = pnginfo

    if "icc_profile" in image.info:
        save_kwargs["icc_profile"] = image.info["icc_profile"]

    if "gamma" in image.info:
        save_kwargs["gamma"] = image.info["gamma"]

    return _serialize(image, "PNG", **save_kwargs)


def _png_visual_configs(
    profile: CompressionProfile,
) -> list[tuple[int, Image.Dither, Image.Quantize]]:
    if profile == CompressionProfile.BALANCED:
        return [
            (256, Image.Dither.NONE, Image.Quantize.FASTOCTREE),
            (256, Image.Dither.FLOYDSTEINBERG, Image.Quantize.FASTOCTREE),
            (192, Image.Dither.NONE, Image.Quantize.FASTOCTREE),
            (192, Image.Dither.FLOYDSTEINBERG, Image.Quantize.FASTOCTREE),
            (160, Image.Dither.NONE, Image.Quantize.FASTOCTREE),
            (160, Image.Dither.FLOYDSTEINBERG, Image.Quantize.FASTOCTREE),
        ]

    return [
        (256, Image.Dither.NONE, Image.Quantize.FASTOCTREE),
        (256, Image.Dither.FLOYDSTEINBERG, Image.Quantize.FASTOCTREE),
        (224, Image.Dither.NONE, Image.Quantize.FASTOCTREE),
        (192, Image.Dither.NONE, Image.Quantize.FASTOCTREE),
        (192, Image.Dither.FLOYDSTEINBERG, Image.Quantize.FASTOCTREE),
        (160, Image.Dither.NONE, Image.Quantize.FASTOCTREE),
        (160, Image.Dither.FLOYDSTEINBERG, Image.Quantize.FASTOCTREE),
        (128, Image.Dither.NONE, Image.Quantize.FASTOCTREE),
        (128, Image.Dither.FLOYDSTEINBERG, Image.Quantize.FASTOCTREE),
        (96, Image.Dither.NONE, Image.Quantize.FASTOCTREE),
        (96, Image.Dither.FLOYDSTEINBERG, Image.Quantize.FASTOCTREE),
        (64, Image.Dither.NONE, Image.Quantize.FASTOCTREE),
        (64, Image.Dither.FLOYDSTEINBERG, Image.Quantize.FASTOCTREE),
        (48, Image.Dither.NONE, Image.Quantize.FASTOCTREE),
        (48, Image.Dither.FLOYDSTEINBERG, Image.Quantize.FASTOCTREE),
        (32, Image.Dither.NONE, Image.Quantize.FASTOCTREE),
        (32, Image.Dither.FLOYDSTEINBERG, Image.Quantize.FASTOCTREE),
        (24, Image.Dither.NONE, Image.Quantize.FASTOCTREE),
        (24, Image.Dither.FLOYDSTEINBERG, Image.Quantize.FASTOCTREE),
    ]


def _save_png_visual(image: Image.Image, profile: CompressionProfile) -> bytes:
    pngquant_bytes = _save_png_with_pngquant(image, profile)
    if pngquant_bytes is not None:
        return pngquant_bytes

    rgba_image = image.convert("RGBA")
    candidates: list[bytes] = []

    for colors, dither, method in _png_visual_configs(profile):
        quantized = rgba_image.quantize(colors=colors, method=method, dither=dither)
        candidates.append(
            _serialize(quantized, "PNG", optimize=True, compress_level=9)
        )

    return min(candidates, key=len)


def _save_png_with_pngquant(
    image: Image.Image,
    profile: CompressionProfile,
) -> bytes | None:
    pngquant_path = shutil.which("pngquant")
    if pngquant_path is None:
        return None

    quality_min, quality_max = _pngquant_quality_for_profile(profile)
    input_bytes = _serialize(image.convert("RGBA"), "PNG")
    command = [
        pngquant_path,
        "--quality",
        f"{quality_min}-{quality_max}",
        "--speed",
        "1",
        "--strip",
        "--output",
        "-",
        "--force",
        "--",
        "-",
    ]

    result = subprocess.run(
        command,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    if result.returncode != 0 or not result.stdout.startswith(b"\x89PNG\r\n\x1a\n"):
        return None

    return result.stdout


def _pngquant_quality_for_profile(
    profile: CompressionProfile,
) -> tuple[int, int]:
    if profile == CompressionProfile.BALANCED:
        return (70, 88)
    return (55, 80)


def _jpeg_configs_for_profile(
    profile: CompressionProfile,
) -> list[tuple[int, bool, int]]:
    if profile == CompressionProfile.BALANCED:
        return [
            (82, True, 2),
            (76, True, 2),
            (70, True, 2),
            (64, True, 2),
        ]

    return [
        (72, True, 2),
        (64, True, 2),
        (58, True, 2),
        (52, True, 2),
        (46, True, 2),
        (40, True, 2),
        (34, True, 2),
        (28, True, 2),
        (52, False, 2),
        (46, False, 2),
        (40, False, 2),
    ]


def _save_jpeg(image: Image.Image, profile: CompressionProfile) -> bytes:
    rgb_image = image.convert("RGB")
    candidate_sizes: list[bytes] = []

    for quality, progressive, subsampling in _jpeg_configs_for_profile(profile):
        candidate_sizes.append(
            _serialize(
                rgb_image,
                "JPEG",
                optimize=True,
                progressive=progressive,
                quality=quality,
                subsampling=subsampling,
            )
        )

    return min(candidate_sizes, key=len)


def _serialize(image: Image.Image, format_name: str, **save_kwargs: object) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format=format_name, **save_kwargs)
    return buffer.getvalue()


def _build_pnginfo(image: Image.Image) -> PngImagePlugin.PngInfo | None:
    text_keys = {
        "XML:com.adobe.xmp",
        "Description",
        "Comment",
        "Title",
        "Author",
        "Software",
    }
    pnginfo = PngImagePlugin.PngInfo()
    added = False

    for key in text_keys:
        value = image.info.get(key)
        if isinstance(value, str):
            pnginfo.add_text(key, value)
            added = True

    xmp_bytes = image.info.get("xmp")
    if isinstance(xmp_bytes, bytes):
        pnginfo.add_itxt("XML:com.adobe.xmp", xmp_bytes.decode("utf-8", errors="ignore"))
        added = True

    return pnginfo if added else None


def compress_image_bytes(
    data: bytes,
    mime_type: str,
    *,
    profile: CompressionProfile = CompressionProfile.AGGRESSIVE,
    png_mode: PngCompressionMode = PngCompressionMode.STRICT,
) -> CompressionOutput:
    if mime_type not in SUPPORTED_MIME_TYPES:
        raise ValueError(f"Unsupported MIME type: {mime_type}")

    with Image.open(io.BytesIO(data)) as image:
        width, height = image.size
        if mime_type == "image/png":
            if png_mode == PngCompressionMode.VISUAL:
                compressed = _save_png_visual(image, profile)
            else:
                compressed = _save_png(image, profile)
        else:
            compressed = _save_jpeg(image, profile)

    best_data = compressed if len(compressed) < len(data) else data

    return CompressionOutput(
        data=best_data,
        mime_type=mime_type,
        width=width,
        height=height,
        original_size=len(data),
        compressed_size=len(best_data),
    )
