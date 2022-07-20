#!/usr/bin/env python
# coding:utf-8

import os
import re
import sys
import time
import shutil
import logging
import argparse
import tempfile
import textwrap
import contextlib
import subprocess

import multiprocessing as mp

from setuptools import setup

from types import MethodType
from Cython.Build import cythonize

from ._version import __version__

PY = sys.version_info

if PY.major == 2:
    from copy_reg import pickle
elif PY.major == 3:
    from copyreg import pickle


class WorkerStopException(Exception):
    pass


def clean_process():
    p = os.getpid()
    g = os.getpgid(p)
    os.killpg(g, 15)


def pickle_method(method):
    func_name = method.im_func.__name__
    obj = method.im_self
    cls = method.im_class
    return unpickle_method, (func_name, obj, cls)


def unpickle_method(func_name, obj, cls):
    for cls in cls.mro():
        try:
            func = cls.__dict__[func_name]
        except KeyError:
            pass
        else:
            break
    return func.__get__(obj, cls)


def text_wrap(text):
    return textwrap.dedent(text).strip()


@contextlib.contextmanager
def tempdir(*args, **kwargs):
    tmpdir = tempfile.mkdtemp(*args, **kwargs)
    try:
        yield tmpdir
    finally:
        try:
            shutil.rmtree(tmpdir)
        except:
            pass


def call(cmd, out=False, shell=True, msg="", c=False, tmdir=None):
    log = mp.get_logger()
    if not out:
        with open(os.devnull, "w") as fo:
            subprocess.check_call(cmd, shell=shell, stdout=fo, stderr=fo)
        return
    try:
        out = subprocess.check_output(cmd, shell=shell, stderr=subprocess.PIPE)
    except Exception as err:
        if msg:
            log.error("compile error %s" % msg)
        if not c:
            if tmdir and os.path.isfile(tmdir):
                shutil.rmtree(tmdir)
            raise WorkerStopException()
        return
    dotso = re.findall(" \-o (.+\.so)\n", out.decode())
    return dotso[0]


def check_cython(python_exe):
    proc = subprocess.Popen([python_exe, "-m", "cython"],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    out = stdout+stderr
    if "--version" in out.decode():
        return True
    return False


def Mylog(logfile=None, multi=False, level="info"):
    if multi:
        logger = mp.get_logger()
    else:
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
        h = logging.StreamHandler(sys.stdout)  # default: sys.stderr
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
        description="For compile *.py projects to *.so")
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
