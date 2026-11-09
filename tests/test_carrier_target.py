"""Isolierte Tests der echten Worker-Methode ohne Qt, OCR oder X11.

AST lädt nur die geprüfte Methode; die GUI-Imports würden andernfalls
Hardware- und OCR-Abhängigkeiten beim Teststart initialisieren.
"""
import ast
import json
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
TARGET = 'galaxiekarte_carrier_target'
SYMBOL = 'galaxiekarte_carrier_symbol'


class MouseControlError(RuntimeError):
    pass


class Clock:
    def __init__(self):
        self.now = 0.0
        self.on_sleep = lambda: None

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds
        self.on_sleep()


class CarrierTargetTests(unittest.TestCase):
    def setUp(self):
        tree = ast.parse((ROOT / 'automation_gui.py').read_text())
        worker = next(n for n in tree.body if isinstance(n, ast.ClassDef)
                      and n.name == 'AutomationWorker')
        method = next(n for n in worker.body if isinstance(n, ast.FunctionDef)
                      and n.name == '_select_carrier_target')
        self.clock = Clock()
        self.moves = []
        self.clicks = []
        self.stop = False
        self.current = None
        self.symbol_time = None
        self.checks = []
        self.worker = SimpleNamespace(
            _check_stop=lambda: self.stop, log_message=SimpleNamespace(emit=Mock()))
        namespace = dict(Vision=object, MouseControlError=MouseControlError, time=self.clock,
                         move_to_reference_center=self.move, left_click=self.click)
        exec(compile(ast.Module(body=[method], type_ignores=[]),
                     'automation_gui.py', 'exec'), namespace)
        self.select = namespace['_select_carrier_target']

    def move(self, name, after_delay):
        self.current = name
        self.moves.append(name)
        self.clock.sleep(after_delay)

    def click(self, after_delay):
        self.clicks.append(self.current)
        if self.current == SYMBOL:
            self.symbol_time = self.clock.now
        self.clock.sleep(after_delay)

    def run_flow(self, target=False, recovered=False, symbol=True, hook=None):
        def check(name, threshold):
            self.checks.append((name, threshold, self.clock.now))
            if hook:
                hook(name)
            matched = symbol if name == SYMBOL else (
                target or (recovered and SYMBOL in self.clicks))
            return matched, 0.99 if matched else 0.2
        return self.select(self.worker, SimpleNamespace(check=check))

    def test_visible_target_no_correction(self):
        self.assertTrue(self.run_flow(target=True))
        self.assertEqual(self.clicks, [TARGET])
        self.assertEqual(self.moves, [TARGET])

    def test_recovery_once_and_wait(self):
        self.assertTrue(self.run_flow(recovered=True))
        self.assertEqual(self.clicks, [SYMBOL, TARGET])
        after = [t for name, _, t in self.checks
                 if name == TARGET and t > self.symbol_time]
        self.assertGreaterEqual(after[0] - self.symbol_time, 1.0)
        self.assertIn((SYMBOL, 0.95), [(n, v) for n, v, _ in self.checks])
        self.assertTrue(all(v == 0.94 for n, v, _ in self.checks if n == TARGET))

    def test_persistent_failure(self):
        with self.assertRaisesRegex(RuntimeError, 'nach einem Korrekturklick'):
            self.run_flow()
        self.assertEqual(self.clicks, [SYMBOL])
        self.assertLess(self.clock.now, 25)

    def test_symbol_not_recognized(self):
        with self.assertRaisesRegex(RuntimeError, 'Carrier-Symbol nicht sicher'):
            self.run_flow(symbol=False)
        self.assertEqual(self.clicks, [])

    def test_missing_symbol_reference_or_image(self):
        for error in (KeyError(SYMBOL), FileNotFoundError(SYMBOL)):
            with self.subTest(error=type(error)):
                def fail(name):
                    if name == SYMBOL:
                        raise error
                with self.assertRaisesRegex(RuntimeError, 'Sprung-Wizard'):
                    self.run_flow(hook=fail)
                self.assertEqual(self.clicks, [])

    def test_stop_before_start(self):
        self.stop = True
        self.assertFalse(self.run_flow(target=True))
        self.assertEqual(self.moves, [])
        self.assertEqual(self.clicks, [])

    def test_missing_symbol_coordinates(self):
        def fail_move():
            if self.current == SYMBOL:
                raise MouseControlError('Referenz nicht gefunden')
        self.clock.on_sleep = fail_move
        with self.assertRaisesRegex(RuntimeError, 'Sprung-Wizard'):
            self.run_flow()
        self.assertEqual(self.clicks, [])

    def test_stop_during_target_polling(self):
        def stop(name):
            self.stop = True
        self.assertFalse(self.run_flow(hook=stop))
        self.assertEqual(self.clicks, [])

    def test_stop_before_jump_click(self):
        def stop(name):
            self.stop = True
        self.assertFalse(self.run_flow(target=True, hook=stop))
        self.assertEqual(self.clicks, [])

    def test_stop_before_correction_click(self):
        def stop(name):
            if name == SYMBOL:
                self.stop = True
        self.assertFalse(self.run_flow(hook=stop))
        self.assertEqual(self.clicks, [])

    def test_stop_during_correction_wait(self):
        def stop():
            if self.symbol_time is not None and self.clock.now > self.symbol_time:
                self.stop = True
        self.clock.on_sleep = stop
        self.assertFalse(self.run_flow(recovered=True))
        self.assertEqual(self.clicks, [SYMBOL])
        self.assertEqual(self.moves, [TARGET, SYMBOL])

    def test_vision_window_error_never_clicks(self):
        def fail(name):
            raise RuntimeError('Elite-Fenster wurde nicht gefunden.')
        with self.assertRaisesRegex(RuntimeError, 'Elite-Fenster'):
            self.run_flow(hook=fail)
        self.assertEqual(self.clicks, [])

    def test_catalog_contains_unique_symbol(self):
        catalog = json.loads((ROOT / 'config/reference_catalog.json').read_text())
        entries = [e for e in catalog if e['name'] == SYMBOL]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['group'], 'Galaxiekarte')
        self.assertTrue(entries[0]['description'])


if __name__ == '__main__':
    unittest.main()
