"""Test the detach module."""
import detach
import os
import sys
import tempfile
import time
import unittest
from collections import deque
from multiprocessing import Event, Queue

parent_pid = os.getpid()


def parentonly(func):
    """Only execute the decorated function in the parent thread."""
    def wrapper(*args, **kwargs):
        pid = os.getpid()
        if pid == parent_pid:
            return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


class TestDetach(unittest.TestCase):
    """Test the `Dispatch` class."""

    def setUp(self):
        self.queue = Queue()
        self.put_event = Event()

    def put(self, item):
        """Put an item to the internal queue."""
        self.queue.put(item)

    def put_done(self):
        """Notify when all puts are complete."""
        self.put_event.set()

    def assertQueue(self, want, msg=None, timeout=2):
        """Drain the queue and compare its contents to want."""
        items = []
        self.assertTrue(self.put_event.wait(timeout))
        time.sleep(0.5)
        while not self.queue.empty():
            items.append(self.queue.get())
        self.assertEqual(items, list(want), msg)

    @parentonly
    def test_detach(self):
        """Detach()"""
        try:
            want = deque()
            with detach.Detach(None, sys.stderr, None) as d:
                if d.pid:
                    want.append(d.pid)
                else:
                    pid = os.getpid()
                    self.put(pid)
                    self.put_done()
            self.assertQueue(want)
        except SystemExit as e:
            self.assertEqual(e.code, 0)

    @parentonly
    def test_daemonize(self):
        """Detach(daemonize=True)"""
        try:
            with detach.Detach(None, sys.stderr) as d1:
                if not d1.pid:
                    with detach.Detach(None, sys.stderr, None, daemonize=True) as d2:
                        pass
                    self.queue.put('parent is still running')
        except SystemExit as e:
            self.assertEqual(e.code, 0)
        self.assertTrue(self.queue.empty())

    @parentonly
    def test_close_fds(self):
        """Detach(close_fds=True)"""
        try:
            fd = tempfile.NamedTemporaryFile(delete=False)

            with detach.Detach(None, sys.stderr, None, close_fds=True) as d:
                if d.pid:
                    fd.close()
                else:
                    self.assertRaises(IOError, fd.close)
        except SystemExit as e:
            self.assertEqual(e.code, 0)

    @parentonly
    def test_exclude_fds(self):
        """Detach(close_fds=True, exclude_fds=[fd])"""
        try:
            fd = tempfile.NamedTemporaryFile(delete=False)
            with detach.Detach(None, sys.stderr, None, close_fds=True, exclude_fds=[fd]) as d:
                if d.pid:
                    fd.close()
                else:
                    fd.close()
        except SystemExit as e:
            self.assertEqual(e.code, 0)


class TestCall(unittest.TestCase):
    """Test `call` function."""

    @parentonly
    def test_call(self):
        """call()"""
        try:
            fd = tempfile.NamedTemporaryFile(delete=False)
            want_pid = detach.call(['bash', '-c', 'echo "$$"'], stdout=fd)
            time.sleep(0.5)
            fd.seek(0)
            have_pid = int(fd.read().strip())
            self.assertEqual(have_pid, want_pid)
            fd.close()
        except SystemExit as e:
            self.assertEqual(e.code, 0)
