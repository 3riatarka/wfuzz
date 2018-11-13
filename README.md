# About this fork

This fork implements the `database` option, which saves some of the information outputted to a SQlite3.
This file can (and should) be opened with [CherryTree](https://www.giuspen.com/cherrytree/) v0.38.6 or greater.
To use it, set the database option and pass the database file as an argument:
```
wfuzz -w wordlist.txt --database database.ctb http://domain.tld/FUZZ
```
The script tries to create the file if it doesn't exist. If it already exists, check if it is a readable/writable SQlite3 file.

The output filters (hc, hl, hw and hh) works here too: those records which match the filter won't be written to the database.

This option impacts slightly the performance of the original program.

# DISCLAIMER

CherryTree v0.38.6 adds two columns to the node table of its database. If you use this fork to append information to a .ctb database created with CherryTree v<0.38.6 __IT CAN RENDER THE FILE INCONSISTENT__. 

You can still recover the information stored with an sqlite3 client, but please, 
__DO NOT USE THIS WITH CHERRYTREE FILES PRIOR TO VERSION 0.38.6__.

# Wfuzz - The Web Fuzzer

<a href="https://pypi.python.org/pypi/wfuzz"><img src="https://img.shields.io/pypi/v/wfuzz.svg"></a>
<a href="https://pypi.python.org/pypi/wfuzz"><img src="https://img.shields.io/pypi/pyversions/wfuzz.svg"></a>
<a href="https://codecov.io/github/xmendez/wfuzz"><img src="https://codecov.io/github/xmendez/wfuzz/coverage.svg?branch=master"></a>

Wfuzz has been created to facilitate the task in web applications assessments and it is based on a simple concept: it replaces any reference to the FUZZ keyword by the value of a given payload.

A payload in Wfuzz is a source of data.

This simple concept allows any input to be injected in any field of an HTTP request, allowing to perform complex web security attacks in different web application components such as: parameters, authentication, forms, directories/files, headers, etc.

Wfuzz is more than a web content scanner:

* Wfuzz could help you to secure your web applications by finding and exploiting web application vulnerabilities. Wfuzz’s web application vulnerability scanner is supported by plugins.

* Wfuzz is a completely modular framework and makes it easy for even the newest of Python developers to contribute. Building plugins is simple and takes little more than a few minutes.

* Wfuzz exposes a simple language interface to the previous HTTP requests/responses performed using Wfuzz or other tools, such as Burp. This allows you to perform manual and semi-automatic tests with full context and understanding of your actions, without relying on a web application scanner underlying implementation.


It was created to facilitate the task in web applications assessments, it's a tool by pentesters for pentesters ;)

## Installation 

To install WFuzz, simply use pip:

```
pip install wfuzz
```
## Documentation

Documentation is available at http://wfuzz.readthedocs.io

## Download 

Check github releases. Latest is available at https://github.com/xmendez/wfuzz/releases/latest
