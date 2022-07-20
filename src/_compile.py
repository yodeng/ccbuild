#!/usr/bin/env python

import os
import sys
import glob
import shutil
import logging
import fnmatch

import multiprocessing as mp

from .utils import *


class CompileProject(object):

    py_ext = ".py"

    def __init__(self, project_dir="", compile_dir="", exclude_dir=None, exclude_file=None, interpreter=sys.executable, threads=1, c=False):
        self.pdir = os.path.abspath(project_dir)
        self.cdir = os.path.abspath(compile_dir)
        self.threads = threads
        if not os.path.isdir(self.cdir):
            os.makedirs(self.cdir)
        if os.path.isfile(self.pdir):
            cpcmd = "cp %s %s" % (self.pdir, self.cdir)
        else:
            cpcmd = "cp -r %s/* %s" % (
                self.pdir, self.cdir)
        call(cpcmd)
        self.compile_file = []
        self.edir = [] if exclude_dir is None else exclude_dir
        self.efile = [] if exclude_file is None else exclude_file
        self.interpreter = interpreter
        self.cc = c
        mg = mp.Manager()
        self.lock = mg.Lock()
        self.tmdir = mg.list()

    def list_compile_files(self):
        for p, ds, fs in os.walk(self.cdir):
            dn = os.path.basename(p)
            for dp in self.edir:
                if fnmatch.fnmatch(dn, dp):
                    break
            else:
                for fp in self.efile:
                    for fn in fnmatch.filter(fs, fp):
                        fs.remove(fn)
                for f in fs:
                    if f.endswith(self.py_ext):
                        self.compile_file.append(os.path.join(p, f))

    def compile(self, pyf, remove=True):
        self.logger.info("start compile %s file", pyf)
        with tempdir() as td:
            with self.lock:
                self.tmdir.append(td)
            tf = os.path.join(td, "ccbuild.py")
            self.write_setup(tf)
            cmd = [self.interpreter, tf, pyf]
            call(cmd, shell=False, msg=pyf, c=self.cc,
                 tmpdir=self.tmdir)
        outfile = glob.glob(os.path.splitext(
            pyf)[0] + ".cpython*.so") or glob.glob(os.path.splitext(pyf)[0] + ".so")
        if len(outfile) == 0:
            return
        elif len(outfile) != 1:
            raise IOError("multi *.so file: %s" % outfile)
        outfile = outfile[0]
        if remove:
            p = outfile.rsplit(".", 2)
            n, ext = p[0], p[-1]
            new_file_name = os.path.join(os.path.dirname(pyf), n+"."+ext)
            shutil.move(outfile, new_file_name)
            os.remove(os.path.splitext(new_file_name)[0] + ".c")
            if os.path.isfile(pyf[:-3] + ".so"):
                os.remove(pyf)
            if os.path.isfile(pyf[:-3] + ".c"):
                os.remove(pyf[:-3] + ".c")
        self.logger.info("finished %s", pyf)

    def __call__(self, pyfile):
        return self.compile(pyfile, remove=True)

    def compile_all(self, remove=True):
        p = mp.Pool(self.threads)
        p.map(self, self.compile_file)
        return

    def clean_source(self):
        pass

    def write_setup(self, outfile):
        with open(outfile, "w") as fo:
            # fo.write("#!%s\n" % self.interpreter)
            ctx = text_wrap('''
                import sys
                import os
                from setuptools import setup
                from Cython.Build import cythonize

                py_file = sys.argv[1]
                sys.argv = sys.argv[:1]
                setup(ext_modules=cythonize(
                    py_file, language_level=str(sys.version_info.major), 
                    force=True,
                    nthreads=10,
                    quiet = True),
                    script_args=["build_ext", 
                        "-b", os.path.dirname(py_file), 
                        "-t", os.path.dirname(__file__)]
                    )                                      
                ''')
            fo.write(ctx.strip() + "\n")

    @property
    def logger(self):
        return mp.get_logger()
