#!/usr/bin/env python
# coding:utf-8

import os
import re
import sys
import time
import shutil
import weakref
import logging
import argparse
import tempfile
import textwrap
import contextlib
import subprocess

import multiprocessing as mp

from setuptools import setup
from concurrent.futures import ProcessPoolExecutor

from Cython.Build import cythonize

from ._version import __version__


def text_wrap(text):
    return textwrap.dedent(text).strip()


class Tempdir(object):

    def __init__(self, suffix=None, prefix=None, dir=None, persistent=False):
        self.persistent = persistent
        self.name = tempfile.mkdtemp(suffix, prefix, dir)
        self._finalizer = weakref.finalize(
            self, self._cleanup, self.name)

    def _cleanup(self, name):
        if not self.persistent:
            shutil.rmtree(name)

    def __repr__(self):
        return "<{} {!r}>".format(self.__class__.__name__, self.name)

    def __enter__(self):
        return self.name

    def __exit__(self, exc, value, tb):
        self.cleanup()

    def cleanup(self):
        if self._finalizer.detach():
            try:
                shutil.rmtree(self.name)
            except:
                pass


def mkdir(path):
    if not os.path.isdir(path):
        os.makedirs(path)


def copy_to_dir(src, dst):
    mkdir(dst)
    if os.path.isfile(src):
        if os.path.abspath(dst) != os.path.abspath(os.path.dirname(src)):
            shutil.copyfile(src, os.path.join(dst, os.path.basename(src)))
        return
    for p in os.listdir(src):
        path = os.path.join(src, p)
        if path == os.path.abspath(dst):
            continue
        if os.path.isfile(path):
            shutil.copyfile(path, os.path.join(dst, p))
        elif os.path.isdir(path):
            shutil.copytree(path, os.path.join(dst, p))


def check_cython(python_exe):
    proc = subprocess.Popen([python_exe, "-c", "'import cython'"],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    if proc.returncode != 0:
        return False
    return True


def Mylog(logfile=None, level="info"):
    logger = logging.getLogger()
    if level.lower() == "info":
        logger.setLevel(logging.INFO)
        f = logging.Formatter(
            '[%(levelname)s %(asctime)s] %(message)s')
    elif level.lower() == "debug":
        logger.setLevel(logging.DEBUG)
        f = logging.Formatter(
            '[%(levelname)s %(threadName)s %(asctime)s %(funcName)s(%(lineno)d)] %(message)s')
    if logfile is None:
        h = logging.StreamHandler()
    else:
        h = logging.FileHandler(logfile, mode='w')
    h.setFormatter(f)
    logger.addHandler(h)
    return logger


def format_exclude(input_exc=None):
    out = []
    if input_exc is not None:
        for n, d in enumerate(input_exc[:]):
            d = os.path.basename(os.path.normpath(d))
            if d:
                out.append(d)
    return out


def Argparse():
    parser = argparse.ArgumentParser(
        description="Compile *.py projects to *.so for python source code protection.")
    parser.add_argument("-p", "--python", type=str,
                        help="python interpreter path to run you project after compile, %s by default" % sys.executable, default=sys.executable, metavar="<file>")
    parser.add_argument("-i", "--input", type=str,
                        help="input file or directory for compile", required=True, metavar="<file/dir>")
    parser.add_argument("-o", "--output", type=str, help="output compiled directory", required=True,
                        metavar="<dir>")
    parser.add_argument("-t", "--threads", type=int, help="thread core, 5 by default", default=5,
                        metavar="<int>")
    parser.add_argument("-c", "--compile-continue", action='store_true', default=False,
                        help="if compile fail, continue, default: exit program")
    parser.add_argument("--exclude-dir", type=str, help="skipped directorys(basename only), simple regular expression allowed('./?/*'), multi input can be separated by whitespace",
                        nargs="*", metavar="<dir>")
    parser.add_argument("--exclude-file", type=str, help="skipped files(basename only), simple regular expression allowed('./?/*'), multi input can be separated by whitespace",
                        nargs="*", metavar="<file>")
    parser.add_argument('-d', '--debug', action='store_true', default=False,
                        help="debug level, if set, more information will be output when compile error")
    parser.add_argument('-v', '--version',
                        action='version', version="v" + __version__)
    args = parser.parse_args()
    args.exclude_dir = format_exclude(args.exclude_dir) + ["__pycache__"]
    args.exclude_file = format_exclude(args.exclude_file) + ["__init__.py"]
    if args.python and which(args.python):
        args.python = which(args.python)
    return args


def canonicalize(path):
    return os.path.abspath(os.path.expanduser(path))


def which(program, paths=None):
    found_path = None
    fpath, fname = os.path.split(program)
    if fpath:
        program = canonicalize(program)
        if is_exe(program):
            found_path = program
    else:
        paths_to_search = []
        if isinstance(paths, (tuple, list)):
            paths_to_search.extend(paths)
        else:
            env_paths = os.environ.get("PATH", "").split(os.pathsep)
            paths_to_search.extend(env_paths)

        for path in paths_to_search:
            exe_file = os.path.join(canonicalize(path), program)
            if is_exe(exe_file):
                found_path = exe_file
                break
    return found_path


def is_exe(file_path):
    return (
        os.path.exists(file_path)
        and os.access(file_path, os.X_OK)
        and os.path.isfile(os.path.realpath(file_path))
    )
