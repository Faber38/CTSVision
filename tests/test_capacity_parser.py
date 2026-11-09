"""Kapazitätsparser isoliert laden: kein Qt, OCR-Modell oder X11 nötig."""
import ast
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_parser():
    tree = ast.parse((ROOT / 'automation_gui.py').read_text())
    worker = next(n for n in tree.body if isinstance(n, ast.ClassDef)
                  and n.name == 'AutomationWorker')
    methods = [n for n in worker.body if isinstance(n, ast.FunctionDef)
               and n.name in ('_normalize_capacity_text', '_parse_carrier_capacity')]
    isolated = ast.Module(body=[ast.ClassDef(
        name='Parser', bases=[], keywords=[], body=methods, decorator_list=[])],
        type_ignores=[])
    namespace = {'re': re}
    exec(compile(ast.fix_missing_locations(isolated), 'capacity-parser', 'exec'), namespace)
    return namespace['Parser']


class CapacityParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parser = load_parser()

    def check_cases(self, cases):
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(self.parser._parse_carrier_capacity(text), (expected, 25000))

    def reject_cases(self, cases):
        for text in cases:
            with self.subTest(text=text), self.assertRaises(RuntimeError):
                self.parser._parse_carrier_capacity(text)

    def test_normal_and_boundaries(self):
        self.check_cases([('23387 / 25000', 23387), ('0/25000', 0),
                          ('1/25000', 1), ('999/25000', 999),
                          ('24999/25000', 24999), ('25000/25000', 25000)])

    def test_shifted_separator_with_labels(self):
        for prefix in ('', 'USED CAPACITY ', 'Used Capacity: ', 'KAPAZITÄT: ',
                       'BELEGTE KAPAZITÄT\n'):
            for suffix in ('', ' EINHEITEN', ' UNITS', '\nEinheiten\n'):
                self.check_cases([(prefix + '233872/5000' + suffix, 23387)])

    def test_normal_with_labels(self):
        self.check_cases([('USED CAPACITY: 23387/25000 UNITS', 23387),
                          ('23387/25000 EINHEITEN', 23387)])

    def test_known_extra_digit(self):
        self.check_cases([('22387/725000', 22387),
                          ('USED CAPACITY: 22387/725000 EINHEITEN', 22387)])

    def test_ocr_characters_only_in_number_fields(self):
        self.check_cases([('USED CAPACITY: 2I387 | 25OOO UNITS', 21387),
                          ('233872\\5000 EINHEITEN', 23387),
                          ('233872:5000', 23387)])

    def test_above_capacity(self):
        self.reject_cases(['25001/25000', '30000/25000', '30001/25000',
                           '250012/5000', '300002/5000', '25001/725000'])

    def test_ambiguous_or_multiple_fields(self):
        self.reject_cases(['23387/25000 12345/25000',
                           '23387/25000\n23387/25000',
                           'USED CAPACITY 233872/5000 42 UNITS',
                           '1 USED CAPACITY 233872/5000',
                           '1000 23387/25000', '23387/25000/25000'])

    def test_arbitrary_digits_and_unknown_text(self):
        self.reject_cases(['2338725000', '23387 25000', 'abc23387/25000',
                           '23387/25000credits', 'RANDOM 23387/25000',
                           '23387/25000 TOTAL 123', 'OIL/25000', '', 'no numbers'])

    def test_unsupported_repairs(self):
        self.reject_cases(['23387/5000', '2338725/000', '23387/2500',
                           '23387/99925000', '23387/025000', '023387/25000',
                           '-23387/25000', '+23387/25000', '23387.5/25000',
                           '233872//5000', '23387/26000'])


if __name__ == '__main__':
    unittest.main()
