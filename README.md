# Nagios-plugins-xrootd
![CI](https://github.com/EGI-Foundation/nagios-plugins-xrootd/workflows/CI/badge.svg)


This is Nagios probe to monitor XRootD endpoints executing simple file operations.

It's based on the gfal2 library for the storage operations and the python-nap library for execution and reporting.

A X509 valid proxy certificate is needed to execute the probe (configured via X509_USER_PROXY variable).

The probes runs the following passive checks in sequence:

  * LsDir: list the folder 
  * Put: put a test file
  * Ls: list the file previously copied
  * Get: copy the file locally and check if content matches
  * Del: delete the file

the active check VOAll just combines the passive checks outcomes.

## Usage

```
usage: xrootd_probe.py [-h] [--version] [-H HOSTNAME] [-w WARNING] [-c CRITICAL]
                    [-d] [-p PREFIX] [-s SUFFIX] [-t TIMEOUT] [-C COMMAND]
                    [--dry-run] [-o OUTPUT] [-E ENDPOINT] [-X X509]
                    [--se-timeout SE_TIMEOUT]

NAGIOS XRootD probe

optional arguments:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  -H HOSTNAME, --hostname HOSTNAME
                        Host name, IP Address, or unix socket (must be an
                        absolute path)
  -w WARNING, --warning WARNING
                        Offset to result in warning status
  -c CRITICAL, --critical CRITICAL
                        Offset to result in critical status
  -d, --debug           Specify debugging mode
  -p PREFIX, --prefix PREFIX
                        Text to prepend to ever metric name
  -s SUFFIX, --suffix SUFFIX
                        Text to append to every metric name
  -t TIMEOUT, --timeout TIMEOUT
                        Global timeout for plugin execution
  -C COMMAND, --command COMMAND
                        Nagios command pipe for submitting passive results
  --dry-run             Dry run, will not execute commands and submit passive
                        results
  -o OUTPUT, --output OUTPUT
                        Plugin output format; valid options are nagios,
                        check_mk or passive (via command pipe); defaults to
                        nagios)
  -E ENDPOINT, --endpoint ENDPOINT
                        XRootD base SURL to test (Mandatory)
  -X X509, --x509 X509  location of x509 certificate proxy file
  --se-timeout SE_TIMEOUT
                        storage operations timeout

```
## Example

```
./plugins/xrootd_probe.py -E root://eospps.cern.ch:1094/eos/pps/opstest/ftstests/test_andrea -H eospps.cern.ch  --dry-run -X /tmp/x509up_u0  -d
Dec 01 18:40:53 DEBUG core[1559]: Call sequence: [(<function metricLsDir at 0x7f761240bc80>, 'LsDir', True), (<function metricPut at 0x7f761240bd08>, 'Put', True), (<function metricLs at 0x7f761240bd90>, 'Ls', True), (<function metricGet at 0x7f761240be18>, 'Get', True), (<function metricDel at 0x7f761240bea0>, 'Del', True), (<function metricAlll at 0x7f761240bf28>, 'All', False)]
Dec 01 18:40:53 DEBUG core[1559]:    Function call: metricLsDir
Dec 01 18:40:53 DEBUG core[1559]: b'OK - Storage Path[root://eospps.cern.ch:1094/eos/pps/opstest/ftstests/test_andrea] Directory successfully listed\\n'
Dec 01 18:40:53 DEBUG core[1559]: [1638384053] PROCESS_SERVICE_CHECK_RESULT;eospps.cern.ch;LsDir;0;OK - Storage Path[root://eospps.cern.ch:1094/eos/pps/opstest/ftstests/test_andrea] Directory successfully listed\n
Dec 01 18:40:53 DEBUG core[1559]:    Function call: metricPut
Dec 01 18:40:54 DEBUG core[1559]: b'OK - File was copied to the XRootD endpoint: Transfer time: 0:00:00.815718\\n'
Dec 01 18:40:54 DEBUG core[1559]: [1638384054] PROCESS_SERVICE_CHECK_RESULT;eospps.cern.ch;Put;0;OK - File was copied to the XRootD endpoint: Transfer time: 0:00:00.815718\n
Dec 01 18:40:54 DEBUG core[1559]:    Function call: metricLs
Dec 01 18:40:54 DEBUG core[1559]: b'OK - File successfully listed\\n'
Dec 01 18:40:54 DEBUG core[1559]: [1638384054] PROCESS_SERVICE_CHECK_RESULT;eospps.cern.ch;Ls;0;OK - File successfully listed\n
Dec 01 18:40:54 DEBUG core[1559]:    Function call: metricGet
Dec 01 18:40:54 DEBUG core[1559]: b'OK - File was copied from XRootD.: Diff successful. Transfer time: 0:00:00.127798\\n'
Dec 01 18:40:54 DEBUG core[1559]: [1638384054] PROCESS_SERVICE_CHECK_RESULT;eospps.cern.ch;Get;0;OK - File was copied from XRootD.: Diff successful. Transfer time: 0:00:00.127798\n
Dec 01 18:40:54 DEBUG core[1559]:    Function call: metricDel
Dec 01 18:40:54 DEBUG core[1559]: b'OK - File was deleted from the XRootD endpoint.\\n'
Dec 01 18:40:54 DEBUG core[1559]: [1638384054] PROCESS_SERVICE_CHECK_RESULT;eospps.cern.ch;Del;0;OK - File was deleted from the XRootD endpoint.\n
Dec 01 18:40:54 DEBUG core[1559]:    Function call: metricAlll
OK - All fine

```
##  rpm build
```
mkdir build
cd build
make rpm -f ../Makefile 
```

