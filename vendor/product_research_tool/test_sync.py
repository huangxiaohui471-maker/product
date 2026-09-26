import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sync import build_rows, merge_rows


class SyncTests(unittest.TestCase):
    def sample(self):
        return {
            "date": "2026/09/24",
            "window": ["2026/09/18", "2026/09/24"],
            "categories": [{
                "name": "眼部护理",
                "path": "个护家清/个人护理/眼部护理",
                "rows": [{
                    "product_id": "123", "name": "测试眼霜", "rank": 2,
                    "brand": "测试官方旗舰店", "leaf_category_id": 1000003550,
                    "price_bin": "¥99-¥149", "pay_lower": 1000000000,
                    "pay_upper": 2500000000,
                }],
            }],
        }

    def test_range_is_not_misrepresented_as_exact_sales(self):
        row = build_rows(self.sample())[0]
        self.assertIsNone(row["销售额"])
        self.assertIsNone(row["销量"])
        self.assertIsNone(row["环比增速"])
        self.assertIsNone(row["品牌"])
        self.assertEqual(row["店铺"], "测试官方旗舰店")
        self.assertEqual(row["成交金额下界元"], 10000000)
        self.assertEqual(row["成交金额上界元"], 25000000)
        self.assertEqual(row["三级类目"], "眼霜")

    def test_merge_is_idempotent_and_preserves_other_sources(self):
        original = [{"数据来源": "蝉妈妈", "国家/地区": "中国", "商品ID": "123"}]
        incoming = build_rows(self.sample())
        once = merge_rows(original, incoming)
        twice = merge_rows(once, incoming)
        self.assertEqual(len(once), 2)
        self.assertEqual(once, twice)
        self.assertEqual(once[0], original[0])

    def test_empty_capture_cannot_replace_snapshot(self):
        sample = self.sample()
        sample["categories"][0]["rows"] = []
        with self.assertRaises(ValueError):
            build_rows(sample)


if __name__ == "__main__":
    unittest.main()
