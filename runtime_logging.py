"""Durable console output and periodic diagnostics for interrupted runs."""
import atexit
import ctypes
from datetime import datetime
import faulthandler
import os
from pathlib import Path
import sys
import threading
import time


class DurableOutput:
    def __init__(self, console, file, lock):
        self.console = console
        self.file = file
        self.lock = lock
        self.encoding = 'utf-8'
        self.errors = 'replace'
        self.at_line_start = True

    def write(self, text):
        # Click probes write(b'') to distinguish binary and text streams.
        # Reject bytes even when empty so it keeps using text output.
        if not isinstance(text, str):
            raise TypeError('write() argument must be str, not bytes')
        if not text:
            return 0
        with self.lock:
            for part in text.splitlines(keepends=True):
                if self.at_line_start:
                    self.file.write(datetime.now().astimezone().isoformat(timespec='milliseconds') + ' ')
                self.file.write(part)
                self.at_line_start = part.endswith(('\n', '\r'))
            self.file.flush()
            os.fsync(self.file.fileno())
            if self.console is not None:
                try:
                    self.console.write(text)
                    self.console.flush()
                except (OSError, ValueError):
                    pass
        return len(text)

    def flush(self):
        with self.lock:
            self.file.flush()
            os.fsync(self.file.fileno())

    def isatty(self):
        return bool(self.console and self.console.isatty())

    def fileno(self):
        return self.file.fileno()

    def writable(self):
        return True


def memory_status():
    if os.name != 'nt':
        return 'RAM unavailable'

    class MemoryStatus(ctypes.Structure):
        _fields_ = [('length', ctypes.c_uint32), ('load', ctypes.c_uint32)] + [
            (name, ctypes.c_uint64) for name in
            ('total', 'free', 'page_total', 'page_free', 'virtual_total', 'virtual_free', 'extended')]

    status = MemoryStatus()
    status.length = ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return 'RAM unavailable'
    return f'RAM={status.load}% free={status.free / 2**30:.2f}GB total={status.total / 2**30:.2f}GB'


def start_logging(root=None):
    root = Path(root or Path.cwd()) / 'logs'
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f') + f'-{os.getpid()}'
    path = root / f'runtime-{stamp}.log'
    crash_path = root / f'threads-{stamp}.log'
    output = path.open('a', encoding='utf-8', errors='replace', buffering=1)
    crashes = crash_path.open('ab', buffering=0)
    lock = threading.RLock()
    original_stdout, original_stderr = sys.stdout, sys.stderr
    sys.stdout = DurableOutput(original_stdout, output, lock)
    sys.stderr = DurableOutput(original_stderr, output, lock)
    faulthandler.enable(file=crashes, all_threads=True)
    faulthandler.dump_traceback_later(120, repeat=True, file=crashes)
    stopped = threading.Event()

    def diagnostics():
        previous_cpu = time.process_time()
        previous_time = time.monotonic()
        while not stopped.wait(10):
            now, cpu = time.monotonic(), time.process_time()
            try:
                sys.stdout.write(f'[health] pid={os.getpid()} CPU={100 * (cpu-previous_cpu)/(now-previous_time):.1f}% '
                                 f'threads={threading.active_count()} {memory_status()}\n')
                os.fsync(crashes.fileno())
            except OSError:
                pass
            previous_cpu, previous_time = cpu, now

    def close():
        if stopped.is_set():
            return
        stopped.set()
        worker.join(timeout=2)
        faulthandler.cancel_dump_traceback_later()
        faulthandler.disable()
        with lock:
            sys.stdout, sys.stderr = original_stdout, original_stderr
            output.flush()
            os.fsync(output.fileno())
            os.fsync(crashes.fileno())
            output.close()
            crashes.close()

    worker = threading.Thread(target=diagnostics, daemon=True, name='runtime-log-health')
    worker.start()
    atexit.register(close)
    print(f'Live log: {path}; thread diagnostics: {crash_path}')
    return path, close
