"""Pytest fixtures for storage_probe tests.

The probe depends on the native libraries gfal2 and python-nap, which are
not available on a stock Python installation. These fixtures inject fake
modules into ``sys.modules`` before the plugin is imported so the probe logic
can be exercised with mocks.
"""

import importlib.util
import os
import sys
import types
from unittest import mock

import pytest

# ------------------------------------------------------------------------- #
# Fake gfal2 module
# ------------------------------------------------------------------------- #
fake_gfal2 = types.ModuleType("gfal2")
fake_gfal2.verbose_level = types.SimpleNamespace(normal=1)
fake_gfal2.set_verbose = mock.Mock()
fake_gfal2.get_version = mock.Mock(return_value="2.21.0")
fake_gfal2.cred_new = mock.Mock(return_value=mock.MagicMock(name="cred"))
fake_gfal2.cred_set = mock.Mock()


class GError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


fake_gfal2.GError = GError
fake_gfal2.creat_context = mock.Mock(return_value=mock.MagicMock(name="gfal2_ctx"))

# ------------------------------------------------------------------------- #
# Fake nap package
# ------------------------------------------------------------------------- #
fake_nap = types.ModuleType("nap")
fake_nap.__path__ = []
fake_nap.OK = 0
fake_nap.WARNING = 1
fake_nap.CRITICAL = 2

fake_nap_core = types.ModuleType("nap.core")


class FakePlugin:
    """Minimal stand-in for nap.core.Plugin."""

    def __init__(self, *args, **kwargs):
        self.metrics = []
        self._metric_results = []

    def add_argument(self, *args, **kwargs):
        pass

    def metric(self, **kwargs):
        def decorator(func):
            self.metrics.append((func, kwargs))
            return func

        return decorator

    def metric_results(self):
        return self._metric_results


fake_nap_core.Plugin = FakePlugin
fake_nap.core = fake_nap_core

sys.modules["gfal2"] = fake_gfal2
sys.modules["nap"] = fake_nap
sys.modules["nap.core"] = fake_nap_core


def _load_storage_probe():
    plugins_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(plugins_dir, "plugins", "storage_probe.py")
    spec = importlib.util.spec_from_file_location("storage_probe", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def plugin():
    return _load_storage_probe()


@pytest.fixture
def gfal2_mod():
    return fake_gfal2


@pytest.fixture(autouse=True)
def reset_state(plugin):
    plugin._fileDictionary.clear()
    plugin.app._metric_results = []
    for attr in ("listdir", "filecopy", "stat", "unlink"):
        child = getattr(plugin.ctx, attr)
        child.reset_mock()
        child.side_effect = None
    plugin.ctx.reset_mock()
    for name in ("cred_new", "cred_set", "set_verbose", "get_version"):
        getattr(fake_gfal2, name).reset_mock()
    yield
