#!/usr/bin/env python
##############################################################################
# DESCRIPTION
##############################################################################

"""
XRootD probe, using gfal2, NAP, and compatible with python3

"""

import sys
import time
import tempfile
import datetime
import filecmp
import gfal2
import nap.core
import shutil
import os
import uuid

try:
    from urlparse import urlparse
except BaseException:
    from urllib.parse import urlparse


PROBE_VERSION = "v0.0.1"


# ########################################################################### #
app = nap.core.Plugin(description="NAGIOS XRootD probe", version=PROBE_VERSION)
app.add_argument("-E", "--endpoint", help="base URL to test")
app.add_argument("-X", "--x509", help="location of x509 certificate proxy file")
app.add_argument(
    "--se-timeout",
    dest="se_timeout",
    type=int,
    help="storage operations timeout",
    default=60,
)

gfal2.set_verbose(gfal2.verbose_level.normal)

# Service version(s)
workdir_metric = tempfile.mkdtemp()

# files and patterns
_fileTest = workdir_metric + "/testFile.txt"
_fileTestIn = workdir_metric + "/testFileIn.txt"
_filePattern = "testfile-put-%s-%s.txt"  # time, uuid

_fileDictionary = {}

# Instantiate gfal2
ctx = gfal2.creat_context()

# GFAL version
gfal2_ver = "gfal2 " + gfal2.get_version()


def parse_args(args, io):
    if not args.endpoint:
        return 1
    if args.x509:
        cred = gfal2.cred_new("X509_CERT", args.x509)
        gfal2.cred_set(ctx, "root://", cred)
        gfal2.cred_set(ctx, "xroot://", cred)


@app.metric(seq=1, metric_name="LsDir", passive=True)
def metricLsDir(args, io):
    """
    List content of the top level folder using gfal2.listdir().
    """
    if parse_args(args, io):
        io.status = nap.CRITICAL
        io.summary = "Argument Endpoint (-E, --endpoint) is missing"
        return
    try:
        ctx.listdir(str(args.endpoint))
        io.summary = "Storage Path[%s] Directory successfully listed" % str(
            args.endpoint
        )
        io.status = nap.OK
    except gfal2.GError as e:
        er = e.message
        if er:
            io.status = nap.CRITICAL
            io.summary = "[Err:%s];" % str(er)
        else:
            io.status = nap.CRITICAL
            io.summary = "Error"
    except Exception as e:
        io.set_status(
            nap.CRITICAL,
            "problem invoking gfal2 listdir(): %s:%s" % (str(e), sys.exc_info()[0]),
        )


@app.metric(seq=2, metric_name="Put", passive=True)
def metricPut(args, io):
    """Copy a local file to the storage path."""

    # verify lsdir test succeeded
    results = app.metric_results()
    if results[0][1] != nap.OK:
        io.set_status(nap.WARNING, "lsdir skipped")
        return

    # generate source file
    try:
        src_file = _fileTest
        fp = open(src_file, "w")
        for s in "1234567890":
            fp.write(s + "\n")
        fp.close()

        fn = _filePattern % (str(int(time.time())), str(uuid.uuid1()))

        dest_file = args.endpoint + "/" + fn
        _fileDictionary[args.endpoint] = {}
        _fileDictionary[args.endpoint]["fn"] = fn
    except IOError as e:
        io.set_status(nap.CRITICAL, "Error creating source file")

    # Set transfer parameters
    params = ctx.transfer_parameters()
    params.create_parent = True
    params.timeout = args.se_timeout
    start_transfer = datetime.datetime.now()

    stMsg = "File was copied to the XRootD endpoint"

    try:
        ctx.filecopy(params, "file://" + str(src_file), str(dest_file))
        total_transfer = datetime.datetime.now() - start_transfer
        io.summary = stMsg + ": Transfer time: " + str(total_transfer)
        io.status = nap.OK
    except gfal2.GError as e:
        io.status = nap.CRITICAL
        er = e.message
        if er:
            io.summary = "[Err:%s]" % str(er)
        else:
            io.summary = "Error"
    except Exception as e:
        io.set_status(
            nap.CRITICAL,
            "problem invoking gfal2 filecopy(): %s:%s" % (str(e), sys.exc_info()[0]),
        )


@app.metric(seq=3, metric_name="Ls", passive=True)
def metricLs(args, io):
    """Stat (previously copied) file(s) on the XRootd endpoint."""

    # verify previous test succeeded
    results = app.metric_results()
    if results[1][1] != nap.OK:
        io.set_status(nap.WARNING, "VOLs skipped")
        return

    if len(_fileDictionary.keys()) == 0:
        io.set_status(nap.WARNING, "No endpoints found to test")
        return

    endpoints = []

    for endpt in _fileDictionary.keys():
        dest_filename = (_fileDictionary[endpt])["fn"]
        dest_file = endpt + "/" + dest_filename
        endpoints.append(dest_file)

    for url in endpoints:
        try:
            statp = ctx.stat(str(url))

            io.summary = "File successfully listed"
            io.status = nap.OK
        except gfal2.GError as e:
            er = e.message
            io.status = nap.CRITICAL
            if er:
                io.summary = "[Err:%s];" % str(er)
            else:
                io.summary = "Error"

        except Exception as e:
            io.set_status(
                nap.CRITICAL,
                "problem invoking gfal2 stat(): %s:%s" % (str(e), sys.exc_info()[0]),
            )


@app.metric(seq=4, metric_name="Get", passive=True)
def metricGet(args, io):
    """Copy given remote file(s) from XRootD to a local file."""

    # verify previous test succeeded
    results = app.metric_results()
    if results[2][1] != nap.OK:
        io.set_status(nap.WARNING, "Get skipped")
        return

    if len(_fileDictionary.keys()) == 0:
        io.set_status(nap.WARNING, "No endpoints found to test")
        return

    for endpt in _fileDictionary.keys():

        src_filename = (_fileDictionary[endpt])["fn"]
        src_file = endpt + "/" + src_filename

        dest_file = "file://" + _fileTestIn

        # Set transfer parameters
        params = ctx.transfer_parameters()
        params.timeout = args.se_timeout

        params.overwrite = True

        stMsg = "File was copied from XRootD."
        start_transfer = datetime.datetime.now()
        try:
            ctx.filecopy(params, str(src_file), str(dest_file))
            if filecmp.cmp(_fileTest, _fileTestIn):
                # Files match
                io.status = nap.OK
                total_transfer = datetime.datetime.now() - start_transfer
                io.summary = (
                    stMsg
                    + ": Diff successful."
                    + " Transfer time: "
                    + str(total_transfer)
                )
            else:
                # Files do not match
                io.status = nap.CRITICAL
                io.summary = "Files differ!"

        except gfal2.GError as e:
            io.status = nap.CRITICAL
            er = e.message
            if er:
                io.summary = "[Err:%s]" % str(er)
            else:
                io.summary = "Error"
        except Exception as e:
            io.set_status(
                nap.CRITICAL,
                "problem invoking gfal2 filecopy(): %s:%s"
                % (str(e), sys.exc_info()[0]),
            )


@app.metric(seq=5, metric_name="Del", passive=True)
def metricDel(args, io):
    """Delete given file(s) from XRootD."""

    # skip only if the put failed
    results = app.metric_results()
    if results[3][1] != nap.OK:
        io.set_status(nap.WARNING, "Del skipped")
        return

    if len(_fileDictionary.keys()) == 0:
        io.set_status(nap.CRITICAL, "No endpoints found to test")

    for endpt in _fileDictionary.keys():

        src_filename = (_fileDictionary[endpt])["fn"]
        src_file = endpt + "/" + src_filename
        stMsg = "File was deleted from the XRootD endpoint."
        try:
            ctx.unlink(str(src_file))
            io.status = nap.OK
            io.summary = stMsg
        except gfal2.GError as e:
            er = e.message
            if er:
                io.summary = "[Err:%s]" % str(er)
            else:
                io.summary = "Error"
            io.status = nap.CRITICAL
        except Exception as e:
            io.set_status(
                nap.CRITICAL,
                "problem invoking gfal2 unlink(): %s:%s" % (str(e), sys.exc_info()[0]),
            )


@app.metric(seq=6, metric_name="All", passive=False)
def metricAlll(args, io):
    """Active metric to combine the result from the previous passive ones"""

    results = app.metric_results()

    statuses = [e[1] for e in results]

    if all(st == 0 for st in statuses):
        io.set_status(nap.OK, "All fine")
    elif nap.CRITICAL in statuses:
        io.set_status(nap.CRITICAL, "Critical error executing tests")
    else:
        io.set_status(nap.WARNING, "Some of the tests returned a warning")

    try:
        shutil.rmtree(workdir_metric)
    except OSError as e:
        pass


if __name__ == "__main__":
    app.run()
