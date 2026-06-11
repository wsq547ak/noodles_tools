import io
import unittest

from PIL import Image
from PIL import ImageChops
from PIL import ImageFilter

from services.picZip.core import (
    CompressionProfile,
    PngCompressionMode,
    compress_image_bytes,
)


def make_png_bytes(size=(128, 128), color_count=64):
    image = Image.new("RGBA", size)
    pixels = image.load()
    for x in range(size[0]):
      for y in range(size[1]):
        step = (x + y) % color_count
        pixels[x, y] = (
            (step * 17) % 255,
            (step * 31) % 255,
            (step * 47) % 255,
            255,
        )

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def make_jpeg_bytes(size=(256, 160), quality=96):
    image = Image.new("RGB", size)
    pixels = image.load()
    for x in range(size[0]):
      for y in range(size[1]):
        pixels[x, y] = ((x * 5) % 255, (y * 3) % 255, ((x + y) * 7) % 255)

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality)
    return buffer.getvalue()


def make_gradient_png_bytes(size=(256, 256)):
    image = Image.new("RGBA", size)
    pixels = image.load()
    for x in range(size[0]):
        for y in range(size[1]):
            pixels[x, y] = (
                (x * 3 + y) % 256,
                (y * 5 + x) % 256,
                (x * 7 + y * 11) % 256,
                255,
            )

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def make_soft_alpha_png_bytes(size=(256, 256)):
    image = Image.new("RGBA", size)
    pixels = image.load()
    for x in range(size[0]):
        for y in range(size[1]):
            pixels[x, y] = (
                (x * 5 + y * 3) % 256,
                (x * 2 + y * 7) % 256,
                (x * 11 + y * 13) % 256,
                255 if (x + y) % 5 else 230,
            )

    image = image.filter(ImageFilter.GaussianBlur(radius=0.5))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class CompressImageBytesTests(unittest.TestCase):
    def test_png_compression_keeps_dimensions_and_reduces_size(self):
        original = make_png_bytes()

        result = compress_image_bytes(original, "image/png")

        self.assertEqual(result.width, 128)
        self.assertEqual(result.height, 128)
        self.assertEqual(result.mime_type, "image/png")
        self.assertLess(result.compressed_size, result.original_size)

        compressed = Image.open(io.BytesIO(result.data))
        self.assertEqual(compressed.size, (128, 128))
        self.assertEqual(compressed.mode, "RGBA")

    def test_png_compression_is_pixel_identical(self):
        original = make_soft_alpha_png_bytes()

        result = compress_image_bytes(
            original,
            "image/png",
            profile=CompressionProfile.AGGRESSIVE,
            png_mode=PngCompressionMode.STRICT,
        )

        original_image = Image.open(io.BytesIO(original)).convert("RGBA")
        compressed_image = Image.open(io.BytesIO(result.data)).convert("RGBA")
        diff = ImageChops.difference(original_image, compressed_image)

        self.assertIsNone(diff.getbbox())

    def test_jpeg_compression_keeps_dimensions_and_reduces_size(self):
        original = make_jpeg_bytes()

        result = compress_image_bytes(original, "image/jpeg")

        self.assertEqual(result.width, 256)
        self.assertEqual(result.height, 160)
        self.assertEqual(result.mime_type, "image/jpeg")
        self.assertLess(result.compressed_size, result.original_size)

        compressed = Image.open(io.BytesIO(result.data))
        self.assertEqual(compressed.size, (256, 160))

    def test_aggressive_jpeg_profile_compresses_at_least_as_much_as_balanced(self):
        original = make_jpeg_bytes(size=(320, 240), quality=98)

        balanced = compress_image_bytes(
            original,
            "image/jpeg",
            profile=CompressionProfile.BALANCED,
        )
        aggressive = compress_image_bytes(
            original,
            "image/jpeg",
            profile=CompressionProfile.AGGRESSIVE,
        )

        self.assertEqual(aggressive.width, 320)
        self.assertEqual(aggressive.height, 240)
        self.assertLessEqual(aggressive.compressed_size, balanced.compressed_size)

    def test_aggressive_png_profile_keeps_pixels_identical_to_balanced(self):
        original = make_png_bytes(size=(160, 160), color_count=128)

        balanced = compress_image_bytes(
            original,
            "image/png",
            profile=CompressionProfile.BALANCED,
            png_mode=PngCompressionMode.STRICT,
        )
        aggressive = compress_image_bytes(
            original,
            "image/png",
            profile=CompressionProfile.AGGRESSIVE,
            png_mode=PngCompressionMode.STRICT,
        )

        self.assertEqual(aggressive.width, 160)
        self.assertEqual(aggressive.height, 160)
        balanced_image = Image.open(io.BytesIO(balanced.data)).convert("RGBA")
        aggressive_image = Image.open(io.BytesIO(aggressive.data)).convert("RGBA")
        diff = ImageChops.difference(balanced_image, aggressive_image)

        self.assertIsNone(diff.getbbox())

    def test_png_compression_preserves_rgb_mode_without_palette_conversion(self):
        image = Image.new("RGB", (120, 120))
        pixels = image.load()
        for x in range(120):
            for y in range(120):
                pixels[x, y] = ((x * 3) % 256, (y * 5) % 256, ((x + y) * 7) % 256)

        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        original = buffer.getvalue()

        result = compress_image_bytes(
            original,
            "image/png",
            profile=CompressionProfile.AGGRESSIVE,
            png_mode=PngCompressionMode.STRICT,
        )

        compressed = Image.open(io.BytesIO(result.data))
        self.assertEqual(compressed.mode, "RGB")
        self.assertNotEqual(compressed.mode, "P")

    def test_visual_png_mode_uses_palette_and_reduces_size_more_than_strict(self):
        original = make_soft_alpha_png_bytes(size=(512, 512))

        strict = compress_image_bytes(
            original,
            "image/png",
            profile=CompressionProfile.AGGRESSIVE,
            png_mode=PngCompressionMode.STRICT,
        )
        visual = compress_image_bytes(
            original,
            "image/png",
            profile=CompressionProfile.AGGRESSIVE,
            png_mode=PngCompressionMode.VISUAL,
        )

        visual_image = Image.open(io.BytesIO(visual.data))
        self.assertEqual(visual_image.mode, "P")
        self.assertLessEqual(visual.compressed_size, strict.compressed_size)
        self.assertLess(visual.compressed_size, int(strict.compressed_size * 0.7))

    def test_unsupported_mime_type_raises_error(self):
        with self.assertRaises(ValueError):
            compress_image_bytes(b"not-an-image", "image/gif")


if __name__ == "__main__":
    unittest.main()
