import unittest
from scraper import _parse_price, _clean, _parse_area, _parse_rooms

class TestParserFunctions(unittest.TestCase):
    def test_parse_price_valid(self):
        self.assertEqual(_parse_price("635 000 zł"), 635000)
        self.assertEqual(_parse_price("0 zł"), None)
        self.assertEqual(_parse_price("-100 zł"), None)
        self.assertEqual(_parse_price("  123  zł  "), 123)
    def test_parse_price_invalid(self):
        self.assertIsNone(_parse_price(""))
        self.assertIsNone(_parse_price("abc"))
        self.assertIsNone(_parse_price("-"))

    def test_clean(self):
        self.assertEqual(_clean("\xa0test\xa0"), "test")
        self.assertEqual(_clean("  spaced  "), "spaced")
        self.assertEqual(_clean(""), "")

    def test_parse_area(self):
        self.assertEqual(_parse_area("50 m²"), 50.0)
        self.assertEqual(_parse_area("50,25 m²"), 50.25)
        self.assertIsNone(_parse_area("abc"))
        self.assertIsNone(_parse_area("-1 m²"))

    def test_parse_rooms(self):
        self.assertEqual(_parse_rooms("3"), 3)
        self.assertEqual(_parse_rooms("3 pok."), 3)
        self.assertEqual(_parse_rooms("   2  pok"), 2)
        self.assertIsNone(_parse_rooms("abc"))
        self.assertIsNone(_parse_rooms("-1"))

if __name__ == "__main__":
    unittest.main()
