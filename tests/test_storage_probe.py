"""Tests for plugins/storage_probe.py."""

import io
import os
from types import SimpleNamespace
from unittest import mock

import pytest


class FakeIO:
    """Minimal stand-in for the nap io object."""

    def __init__(self):
        self.status = None
        self.summary = None

    def set_status(self, status, summary):
        self.status = status
        self.summary = summary


def set_results(plugin, *statuses):
    names = ["LsDir", "Put", "Ls", "Get", "Del", "All"]
    plugin.app._metric_results = list(zip(names, statuses))


def write_file(path, content):
    with io.open(path, "w") as f:
        f.write(content)


@pytest.fixture
def args():
    return SimpleNamespace(
        endpoint="https://example.org/storage",
        x509=None,
        token=None,
        se_timeout=60,
        skip_ls_dir=False,
        read_only=False,
    )


# ------------------------------------------------------------------------- #
# parse_args
# ------------------------------------------------------------------------- #
class TestParseArgs:
    def test_missing_endpoint_returns_1(self, plugin, args):
        args.endpoint = None
        assert plugin.parse_args(args, FakeIO()) == 1

    @pytest.mark.parametrize(
        "endpoint,expected",
        [
            ("https://example.org/storage/", "https://example.org/storage"),
            ("davs://example.org/storage/", "davs://example.org/storage"),
        ],
    )
    def test_strips_trailing_slash(self, plugin, args, endpoint, expected):
        args.endpoint = endpoint
        assert plugin.parse_args(args, FakeIO()) is None
        assert args.endpoint == expected

    def test_sets_x509_credentials(self, plugin, gfal2_mod, args):
        args.x509 = "/tmp/x509up_u1000"
        assert plugin.parse_args(args, FakeIO()) is None
        gfal2_mod.cred_new.assert_called_once_with("X509_CERT", "/tmp/x509up_u1000")
        protos = [call.args[1] for call in gfal2_mod.cred_set.call_args_list]
        assert protos == ["https://", "davs://", "root://", "xroot://"]

    def test_sets_bearer_credentials(self, plugin, gfal2_mod, args):
        args.token = "secret"
        assert plugin.parse_args(args, FakeIO()) is None
        gfal2_mod.cred_new.assert_called_once_with("BEARER", "secret")
        protos = [call.args[1] for call in gfal2_mod.cred_set.call_args_list]
        assert protos == ["https://", "davs://", "root://", "xroot://"]


# ------------------------------------------------------------------------- #
# metricLsDir
# ------------------------------------------------------------------------- #
class TestMetricLsDir:
    def test_missing_endpoint_critical(self, plugin, args):
        args.endpoint = None
        io = FakeIO()
        plugin.metricLsDir(args, io)
        assert io.status == plugin.nap.CRITICAL
        assert "missing" in io.summary

    def test_success(self, plugin, args):
        io = FakeIO()
        plugin.metricLsDir(args, io)
        assert io.status == plugin.nap.OK
        assert "successfully listed" in io.summary
        plugin.ctx.listdir.assert_called_once_with(args.endpoint)

    def test_skipped(self, plugin, args):
        args.skip_ls_dir = True
        io = FakeIO()
        plugin.metricLsDir(args, io)
        assert io.status == plugin.nap.OK
        assert io.summary == "LsDir test skipped"
        plugin.ctx.listdir.assert_not_called()

    def test_gerror_critical(self, plugin, args):
        plugin.ctx.listdir.side_effect = plugin.gfal2.GError("boom")
        io = FakeIO()
        plugin.metricLsDir(args, io)
        assert io.status == plugin.nap.CRITICAL
        assert io.summary == "boom"

    def test_generic_exception_critical(self, plugin, args):
        plugin.ctx.listdir.side_effect = RuntimeError("boom")
        io = FakeIO()
        plugin.metricLsDir(args, io)
        assert io.status == plugin.nap.CRITICAL
        assert "problem invoking gfal2 listdir" in io.summary


# ------------------------------------------------------------------------- #
# metricPut
# ------------------------------------------------------------------------- #
class TestMetricPut:
    def test_skipped_when_lsdir_not_ok(self, plugin, args):
        set_results(plugin, plugin.nap.CRITICAL)
        io = FakeIO()
        plugin.metricPut(args, io)
        assert io.status == plugin.nap.WARNING
        assert io.summary == "lsdir skipped"
        plugin.ctx.filecopy.assert_not_called()

    def test_read_only(self, plugin, args):
        args.read_only = True
        set_results(plugin, plugin.nap.OK)
        io = FakeIO()
        plugin.metricPut(args, io)
        assert io.status == plugin.nap.OK
        assert io.summary == "read-only endpoint"
        plugin.ctx.filecopy.assert_not_called()

    def test_success(self, plugin, args):
        set_results(plugin, plugin.nap.OK)
        io = FakeIO()
        plugin.metricPut(args, io)
        assert io.status == plugin.nap.OK
        assert "File was copied to the Storage endpoint" in io.summary
        plugin.ctx.filecopy.assert_called_once()
        assert args.endpoint in plugin._fileDictionary
        assert "fn" in plugin._fileDictionary[args.endpoint]

    def test_gerror_critical(self, plugin, args):
        set_results(plugin, plugin.nap.OK)
        plugin.ctx.filecopy.side_effect = plugin.gfal2.GError("boom")
        io = FakeIO()
        plugin.metricPut(args, io)
        assert io.status == plugin.nap.CRITICAL
        assert "[Err:boom]" in io.summary

    def test_source_file_io_error(self, plugin, args):
        set_results(plugin, plugin.nap.OK)
        with mock.patch("builtins.open", side_effect=IOError("nope")):
            io = FakeIO()
            plugin.metricPut(args, io)
        assert io.status == plugin.nap.CRITICAL


# ------------------------------------------------------------------------- #
# metricLs
# ------------------------------------------------------------------------- #
class TestMetricLs:
    def test_skipped_when_put_not_ok(self, plugin, args):
        set_results(plugin, plugin.nap.OK, plugin.nap.CRITICAL)
        io = FakeIO()
        plugin.metricLs(args, io)
        assert io.status == plugin.nap.WARNING
        assert io.summary == "VOLs skipped"
        plugin.ctx.stat.assert_not_called()

    def test_read_only(self, plugin, args):
        args.read_only = True
        set_results(plugin, plugin.nap.OK, plugin.nap.OK)
        io = FakeIO()
        plugin.metricLs(args, io)
        assert io.status == plugin.nap.OK
        assert io.summary == "read-only endpoint"
        plugin.ctx.stat.assert_not_called()

    def test_no_endpoints(self, plugin, args):
        set_results(plugin, plugin.nap.OK, plugin.nap.OK)
        io = FakeIO()
        plugin.metricLs(args, io)
        assert io.status == plugin.nap.WARNING
        assert io.summary == "No endpoints found to test"

    def test_success(self, plugin, args):
        plugin._fileDictionary[args.endpoint] = {"fn": "testfile.txt"}
        set_results(plugin, plugin.nap.OK, plugin.nap.OK)
        io = FakeIO()
        plugin.metricLs(args, io)
        assert io.status == plugin.nap.OK
        assert io.summary == "File successfully listed"
        plugin.ctx.stat.assert_called_once()

    def test_gerror_critical(self, plugin, args):
        plugin._fileDictionary[args.endpoint] = {"fn": "testfile.txt"}
        plugin.ctx.stat.side_effect = plugin.gfal2.GError("boom")
        set_results(plugin, plugin.nap.OK, plugin.nap.OK)
        io = FakeIO()
        plugin.metricLs(args, io)
        assert io.status == plugin.nap.CRITICAL
        assert "[Err:boom]" in io.summary


# ------------------------------------------------------------------------- #
# metricGet
# ------------------------------------------------------------------------- #
class TestMetricGet:
    def test_skipped_when_ls_not_ok(self, plugin, args):
        set_results(plugin, plugin.nap.OK, plugin.nap.OK, plugin.nap.CRITICAL)
        io = FakeIO()
        plugin.metricGet(args, io)
        assert io.status == plugin.nap.WARNING
        assert io.summary == "Get skipped"
        plugin.ctx.filecopy.assert_not_called()

    def test_read_only(self, plugin, args):
        args.read_only = True
        set_results(plugin, plugin.nap.OK, plugin.nap.OK, plugin.nap.OK)
        io = FakeIO()
        plugin.metricGet(args, io)
        assert io.status == plugin.nap.OK
        assert io.summary == "read-only endpoint"

    def test_no_endpoints(self, plugin, args):
        set_results(plugin, plugin.nap.OK, plugin.nap.OK, plugin.nap.OK)
        io = FakeIO()
        plugin.metricGet(args, io)
        assert io.status == plugin.nap.WARNING
        assert io.summary == "No endpoints found to test"

    def test_success_diff_ok(self, plugin, args):
        plugin._fileDictionary[args.endpoint] = {"fn": "testfile.txt"}
        content = "1\n2\n3\n4\n5\n6\n7\n8\n9\n0\n"
        write_file(plugin._fileTest, content)
        write_file(plugin._fileTestIn, content)
        set_results(plugin, plugin.nap.OK, plugin.nap.OK, plugin.nap.OK)
        io = FakeIO()
        plugin.metricGet(args, io)
        assert io.status == plugin.nap.OK
        assert "Diff successful" in io.summary

    def test_files_differ_critical(self, plugin, args):
        plugin._fileDictionary[args.endpoint] = {"fn": "testfile.txt"}
        write_file(plugin._fileTest, "content-a")
        write_file(plugin._fileTestIn, "content-b")
        set_results(plugin, plugin.nap.OK, plugin.nap.OK, plugin.nap.OK)
        io = FakeIO()
        plugin.metricGet(args, io)
        assert io.status == plugin.nap.CRITICAL
        assert io.summary == "Files differ!"

    def test_gerror_critical(self, plugin, args):
        plugin._fileDictionary[args.endpoint] = {"fn": "testfile.txt"}
        plugin.ctx.filecopy.side_effect = plugin.gfal2.GError("boom")
        set_results(plugin, plugin.nap.OK, plugin.nap.OK, plugin.nap.OK)
        io = FakeIO()
        plugin.metricGet(args, io)
        assert io.status == plugin.nap.CRITICAL
        assert io.summary == "[Err:boom]"


# ------------------------------------------------------------------------- #
# metricDel
# ------------------------------------------------------------------------- #
class TestMetricDel:
    def test_skipped_when_get_not_ok(self, plugin, args):
        set_results(plugin, plugin.nap.OK, plugin.nap.OK, plugin.nap.OK, plugin.nap.CRITICAL)
        io = FakeIO()
        plugin.metricDel(args, io)
        assert io.status == plugin.nap.WARNING
        assert io.summary == "Del skipped"
        plugin.ctx.unlink.assert_not_called()

    def test_read_only(self, plugin, args):
        args.read_only = True
        set_results(plugin, plugin.nap.OK, plugin.nap.OK, plugin.nap.OK, plugin.nap.OK)
        io = FakeIO()
        plugin.metricDel(args, io)
        assert io.status == plugin.nap.OK
        assert io.summary == "read-only endpoint"
        plugin.ctx.unlink.assert_not_called()

    def test_no_endpoints(self, plugin, args):
        set_results(plugin, plugin.nap.OK, plugin.nap.OK, plugin.nap.OK, plugin.nap.OK)
        io = FakeIO()
        plugin.metricDel(args, io)
        assert io.status == plugin.nap.CRITICAL
        assert io.summary == "No endpoints found to test"

    def test_success(self, plugin, args):
        plugin._fileDictionary[args.endpoint] = {"fn": "testfile.txt"}
        set_results(plugin, plugin.nap.OK, plugin.nap.OK, plugin.nap.OK, plugin.nap.OK)
        io = FakeIO()
        plugin.metricDel(args, io)
        assert io.status == plugin.nap.OK
        assert "deleted" in io.summary
        plugin.ctx.unlink.assert_called_once()

    def test_gerror_critical(self, plugin, args):
        plugin._fileDictionary[args.endpoint] = {"fn": "testfile.txt"}
        plugin.ctx.unlink.side_effect = plugin.gfal2.GError("boom")
        set_results(plugin, plugin.nap.OK, plugin.nap.OK, plugin.nap.OK, plugin.nap.OK)
        io = FakeIO()
        plugin.metricDel(args, io)
        assert io.status == plugin.nap.CRITICAL
        assert io.summary == "[Err:boom]"


# ------------------------------------------------------------------------- #
# metricAlll
# ------------------------------------------------------------------------- #
class TestMetricAll:
    def test_all_ok(self, plugin, args):
        set_results(plugin, plugin.nap.OK, plugin.nap.OK, plugin.nap.OK, plugin.nap.OK)
        io = FakeIO()
        plugin.metricAlll(args, io)
        assert io.status == plugin.nap.OK
        assert io.summary == "All fine"

    def test_any_critical(self, plugin, args):
        set_results(plugin, plugin.nap.OK, plugin.nap.CRITICAL, plugin.nap.OK, plugin.nap.OK)
        io = FakeIO()
        plugin.metricAlll(args, io)
        assert io.status == plugin.nap.CRITICAL
        assert io.summary == "Critical error executing tests"

    def test_warning(self, plugin, args):
        set_results(plugin, plugin.nap.OK, plugin.nap.WARNING, plugin.nap.OK, plugin.nap.OK)
        io = FakeIO()
        plugin.metricAlll(args, io)
        assert io.status == plugin.nap.WARNING
        assert io.summary == "Some of the tests returned a warning"

    def test_cleans_up_workdir(self, plugin, args):
        set_results(plugin, plugin.nap.OK, plugin.nap.OK, plugin.nap.OK, plugin.nap.OK)
        io = FakeIO()
        plugin.metricAlll(args, io)
        assert not os.path.exists(plugin.workdir_metric)
