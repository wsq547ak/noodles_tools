import unittest
import io

from PIL import Image

from services.randomStu.recognition import (
    build_recognition_prompt,
    parse_students_json,
    prepare_low_detail_image,
)


class RecognitionTests(unittest.TestCase):
    def test_prompt_requires_complete_students_json(self):
        prompt = build_recognition_prompt()
        self.assertIn("完整且可解析的 JSON", prompt)
        self.assertIn('"students"', prompt)

    def test_parse_students_json_normalizes_and_deduplicates(self):
        content = """```json
        {"students":[
          {"number":"001","name":" 张三 "},
          {"number":"001","name":"张三"},
          {"number":2,"name":"李四"},
          {"number":"3","name":""}
        ]}
        ```"""
        self.assertEqual(
            parse_students_json(content),
            [
                {"number": "001", "name": "张三"},
                {"number": "2", "name": "李四"},
            ],
        )

    def test_parse_students_json_rejects_missing_array(self):
        with self.assertRaises(ValueError):
            parse_students_json('{"result":[]}')

    def test_low_detail_image_is_limited_to_512_pixels(self):
        source = io.BytesIO()
        Image.new("RGB", (1600, 900), "white").save(source, format="JPEG")

        result = prepare_low_detail_image(source.getvalue())
        with Image.open(io.BytesIO(result)) as image:
            self.assertEqual(image.format, "PNG")
            self.assertEqual(image.size, (512, 288))


if __name__ == "__main__":
    unittest.main()
