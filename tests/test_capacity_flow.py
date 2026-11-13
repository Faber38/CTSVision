"""Worker-Verhalten ohne Qt, OCR-Modell, Spielsteuerung oder persönliche Daten."""
import ast
import csv
from pathlib import Path
import re
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, call

from jump_history import JumpHistory, JumpHistoryRecord

ROOT = Path(__file__).resolve().parents[1]


def load_worker(namespace):
    tree = ast.parse((ROOT / 'automation_gui.py').read_text())
    worker = next(n for n in tree.body if isinstance(n, ast.ClassDef)
                  and n.name == 'AutomationWorker')
    names = {'_normalize_capacity_text', '_parse_carrier_capacity',
             '_read_carrier_capacity', '_determine_tank_before_jump',
             '_write_jump_history', '_run_tank_routine', 'run'}
    methods = [n for n in worker.body if isinstance(n, ast.FunctionDef)
               and n.name in names]
    for method in methods:
        if method.name == 'run':
            method.decorator_list = []
    isolated = ast.Module(body=[ast.ClassDef(
        name='Worker', bases=[], keywords=[], body=methods, decorator_list=[])],
        type_ignores=[])
    exec(compile(ast.fix_missing_locations(isolated), 'capacity-flow', 'exec'), namespace)
    return namespace['Worker']()


class InlineThread:
    """Tankroutine deterministisch ausführen, ohne reale Threads zu starten."""
    def __init__(self, *, target, kwargs, **unused):
        self.target, self.kwargs = target, kwargs

    def start(self):
        self.target(**self.kwargs)

    def join(self, **unused):
        pass


class CapacityFlowTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.ocr = Mock()
        self.image = Mock(width=100, height=20)
        self.image.resize.return_value = self.image
        self.vision = Mock()
        self.vision.get_state.return_value = ('carrier_management_navigation', 0.99)
        self.vision.save_last_failure.return_value = None
        self.menu = Mock()
        self.tank = Mock(first_tank_level=800, last_tank_level=800,
                         tank_capacity=1000, refuel_performed=False, tank_read_count=1)
        self.ns = dict(
            __file__=str(self.directory / 'automation_gui.py'), Path=Path, re=re,
            time=Mock(monotonic=Mock(return_value=0)),
            threading=SimpleNamespace(Event=threading.Event, Thread=InlineThread),
            load_config=Mock(return_value={'references': {'ocr_carrier_capacity':
                dict(x=0, y=0, width=100, height=20)}}),
            find_elite_window=Mock(return_value=SimpleNamespace(desktop=1)),
            get_current_desktop=Mock(return_value=1),
            capture_window_region=Mock(return_value=self.image),
            Vision=Mock(return_value=self.vision), Navigator=Mock(),
            MenuController=Mock(return_value=self.menu),
            TankController=Mock(return_value=self.tank),
            press_key=Mock(), type_text=Mock(), click_reference_center=Mock(),
            JumpHistoryRecord=JumpHistoryRecord,
        )
        self.worker = load_worker(self.ns)
        w = self.worker
        for signal in ('log_message', 'failed', 'finished', 'completed',
                       'route_progress_updated', 'tank_status_changed'):
            setattr(w, signal, SimpleNamespace(emit=Mock()))
        w._get_capacity_ocr_engine = Mock(return_value=self.ocr)
        w.current_carrier_capacity = 12345
        w.current_carrier_capacity_maximum = 99999
        w.check_tank_before_jump = False
        w.initial_tank_level = None
        w.initial_refuel_performed = False
        w.tank_before_jump = 999
        w.inferred_refuel_before_jump = 999
        w.settings = {'auto_refuel_enabled': True}
        w._check_stop = Mock(return_value=False)
        w._select_carrier_target = Mock(return_value=True)
        w.carrier_jump_event = threading.Event()
        w.carrier_jump_event.set()
        self.jump = SimpleNamespace(system='Ziel', distance=100, fuel_used=20)
        w.route_manager = Mock(route_file=str(self.directory / 'route.csv'),
                               completed_jumps=0, points=[SimpleNamespace(system='Start')])
        w.route_manager.get_current_jump.return_value = self.jump
        w.jump_history = JumpHistory(self.directory / 'history.csv')

    @staticmethod
    def result(text):
        return SimpleNamespace(success=bool(text), text=text, confidence=0.99)

    def fail_ocr(self):
        self.ocr.read_image.return_value = self.result('unlesbar')

    def rows(self):
        with self.worker.jump_history.path.open(newline='') as handle:
            return list(csv.DictReader(handle, delimiter=';'))

    def test_success_on_each_attempt(self):
        for attempt in (1, 2, 3):
            with self.subTest(attempt=attempt):
                self.ocr.reset_mock()
                self.ns['time'].sleep.reset_mock()
                self.ocr.read_image.side_effect = [self.result('')] * (attempt - 1) + [self.result('18451/25000')]
                self.assertEqual(self.worker._read_carrier_capacity(), (18451, 25000))
                self.assertEqual(self.worker.current_carrier_capacity, 18451)
                self.assertEqual(self.ocr.read_image.call_count, attempt)
                self.assertEqual(self.ns['time'].sleep.call_count, attempt - 1)

    def test_failure_resets_previous_success_and_warns(self):
        self.ocr.read_image.return_value = self.result('18451/25000')
        self.worker._read_carrier_capacity()
        def unreadable(_path):
            self.assertIsNone(self.worker.current_carrier_capacity)
            self.assertEqual(self.worker.current_carrier_capacity_maximum, 25000)
            return self.result('')
        self.ocr.reset_mock()
        self.ocr.read_image.side_effect = unreadable
        self.assertEqual(self.worker._read_carrier_capacity(), (None, 25000))
        self.assertEqual(self.ocr.read_image.call_count, 3)
        messages = [c.args[0] for c in self.worker.log_message.emit.call_args_list]
        self.assertTrue(any('WARNUNG' in text and '3 OCR-Versuchen' in text for text in messages))
        self.assertEqual(self.ns['time'].sleep.call_args_list,
                         [call(0.75), call(0.75)])

    def test_three_failures_continue_full_jump_and_write_missing_capacity(self):
        self.fail_ocr()
        self.worker.run()
        self.assertEqual(self.ocr.read_image.call_count, 3)
        self.menu.open_galaxy_map.assert_called_once()
        self.worker._select_carrier_target.assert_called_once()
        self.tank.run.assert_called_once()
        self.worker.completed.emit.assert_called_once_with('Ziel')
        self.worker.failed.emit.assert_not_called()
        row = self.rows()[0]
        self.assertEqual(row['Used Capacity vor Sprung t'], '')
        self.assertEqual(row['Capacity Maximum t'], '25000')
        self.assertEqual(row['Verbrauch IST t'], '')
        self.assertEqual(row['Abweichung t'], '')

    def test_real_zero_survives_ocr_and_csv(self):
        self.ocr.read_image.return_value = self.result('0/25000')
        self.worker.run()
        self.assertEqual(self.worker.current_carrier_capacity, 0)
        self.assertEqual(self.rows()[0]['Used Capacity vor Sprung t'], '0')

    def test_window_and_desktop_errors_abort_before_navigation(self):
        for missing in (True, False):
            with self.subTest(missing_window=missing):
                self.ns['find_elite_window'].return_value = None if missing else SimpleNamespace(desktop=2)
                self.worker.run()
                self.menu.open_galaxy_map.assert_not_called()
                self.worker.completed.emit.assert_not_called()
                self.ocr.read_image.assert_not_called()
                message = self.worker.failed.emit.call_args.args[0]
                self.assertIn('Elite-Fenster' if missing else 'Arbeitsfläche', message)
                self.assertIsNone(self.worker.current_carrier_capacity)

    def test_capture_error_is_not_downgraded(self):
        self.ns['capture_window_region'].side_effect = RuntimeError('Fenster verloren')
        self.worker.run()
        self.assertIn('Fenster verloren', self.worker.failed.emit.call_args.args[0])
        self.menu.open_galaxy_map.assert_not_called()

    def test_navigation_error_still_aborts_after_capacity_warning(self):
        self.fail_ocr()
        self.menu.open_galaxy_map.side_effect = RuntimeError('Navigation fehlgeschlagen')
        self.worker.run()
        self.worker.completed.emit.assert_not_called()
        self.worker._select_carrier_target.assert_not_called()
        self.assertIn('Navigation fehlgeschlagen', self.worker.failed.emit.call_args.args[0])

    def test_tank_error_still_blocks_completion(self):
        self.fail_ocr()
        self.tank.run.side_effect = RuntimeError('Tankfehler')
        self.worker.run()
        self.worker.completed.emit.assert_not_called()
        self.assertIn('Tankprüfung fehlgeschlagen', self.worker.failed.emit.call_args.args[0])
        self.assertFalse(self.worker.jump_history.path.exists())

    def test_initial_tank_error_aborts_before_capacity_and_jump(self):
        self.worker.check_tank_before_jump = True
        self.tank.run.side_effect = RuntimeError('Tankfehler')
        self.worker.run()
        self.ocr.read_image.assert_not_called()
        self.worker._select_carrier_target.assert_not_called()
        self.worker.completed.emit.assert_not_called()
        self.assertIn('Tankfehler', self.worker.failed.emit.call_args.args[0])

    def determine(self, status, previous_capacity='20000', current_capacity=None):
        self.worker.current_carrier_capacity = current_capacity
        self.worker.jump_history.latest_for_route = Mock(return_value={
            'Tank nach Sprung t': '800', 'Used Capacity vor Sprung t': previous_capacity,
            'Nachgetankt nach Sprung': status})
        self.worker._determine_tank_before_jump()

    def test_unknown_refuel_status_does_not_infer_tank(self):
        for status in ('', 'unbekannt'):
            with self.subTest(status=status):
                self.determine(status, current_capacity=19900)
                self.assertIsNone(self.worker.tank_before_jump)
                self.assertIsNone(self.worker.inferred_refuel_before_jump)
                self.write_history(780)
                row = self.rows()[-1]
                for field in ('Tank vor Sprung t', 'Ermitteltes Nachtanken vor Sprung t',
                              'Verbrauch IST t', 'Abweichung t'):
                    self.assertEqual(row[field], '')

    def test_known_refuel_with_complete_capacity_data(self):
        self.determine('Ja', previous_capacity='20000', current_capacity=19900)
        self.assertEqual(self.worker.inferred_refuel_before_jump, 100)
        self.assertEqual(self.worker.tank_before_jump, 900)

    def test_missing_capacity_prevents_refuel_inference(self):
        for previous, current in (('20000', None), ('', 19900)):
            with self.subTest(previous=previous, current=current):
                self.determine('Ja', previous, current)
                self.assertIsNone(self.worker.tank_before_jump)
                self.assertIsNone(self.worker.inferred_refuel_before_jump)

    def test_known_no_refuel_allows_independent_consumption(self):
        self.determine('Nein')
        self.assertEqual(self.worker.tank_before_jump, 800)
        self.write_history(780)
        self.assertEqual(self.rows()[0]['Verbrauch IST t'], '20')
        self.assertEqual(self.rows()[0]['Abweichung t'], '0')

    def write_history(self, after):
        self.worker._write_jump_history(
            current_jump=self.jump, from_system='Start', system_name='Ziel',
            tank_result={'first_tank_level': after}, auto_refuel_enabled=True)

    def test_consumption_requires_both_tank_values(self):
        for before, after in ((None, 780), (800, None), (None, None)):
            self.worker.tank_before_jump = before
            self.write_history(after)
        for row in self.rows():
            self.assertEqual(row['Verbrauch IST t'], '')
            self.assertEqual(row['Abweichung t'], '')

    def test_zero_tank_and_zero_consumption_are_preserved(self):
        self.worker.tank_before_jump = 0
        self.jump.fuel_used = 0
        self.write_history(0)
        row = self.rows()[0]
        self.assertEqual(row['Tank vor Sprung t'], '0')
        self.assertEqual(row['Tank nach Sprung t'], '0')
        self.assertEqual(row['Verbrauch IST t'], '0')
        self.assertEqual(row['Abweichung t'], '0')

    def test_missing_plan_skips_only_deviation(self):
        self.worker.tank_before_jump = 800
        self.jump.fuel_used = None
        self.write_history(780)
        row = self.rows()[0]
        self.assertEqual(row['Verbrauch IST t'], '20')
        self.assertEqual(row['Abweichung t'], '')


if __name__ == '__main__':
    unittest.main()
