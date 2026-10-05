import io
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from runtime_logging import DurableOutput


class RuntimeLoggingTests(unittest.TestCase):
    def test_flask_banner_through_panel_stream(self):
        from flask.cli import show_server_banner
        from webui.runtime import ThreadFilterStream
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'runtime.log'
            with path.open('w', encoding='utf-8') as file:
                console = io.StringIO()
                stream = DurableOutput(console, file, threading.RLock())
                with self.assertRaises(TypeError):
                    stream.write(b'')
                with patch('sys.stdout', ThreadFilterStream(stream)):
                    show_server_banner(False, 'regression-test')
                self.assertIn('regression-test', path.read_text(encoding='utf-8'))
                self.assertIn('regression-test', console.getvalue())

    def test_partial_output_is_immediately_saved_and_synced(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'runtime.log'
            with path.open('w', encoding='utf-8') as file:
                console = io.StringIO()
                stream = DurableOutput(console, file, threading.RLock())
                with patch('runtime_logging.os.fsync') as sync:
                    stream.write('last event')
                    self.assertIn('last event', path.read_text(encoding='utf-8'))
                    sync.assert_called_once_with(file.fileno())
                stream.write('\nnext event\n')
                self.assertEqual(console.getvalue(), 'last event\nnext event\n')
                self.assertEqual(len(path.read_text(encoding='utf-8').splitlines()), 2)

    def test_missing_console_does_not_prevent_disk_logging(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'runtime.log'
            with path.open('w', encoding='utf-8') as file:
                stream = DurableOutput(None, file, threading.RLock())
                stream.write('background output\n')
                self.assertFalse(stream.isatty())
                self.assertIn('background output', path.read_text(encoding='utf-8'))
