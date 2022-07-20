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
        fin = False
        with tempdir() as td:
            with self.lock:
                self.tmdir.append(td)
            tf = os.path.join(td, "ccbuild.py")
            self.write_setup(tf)
            cmd = [self.interpreter, tf, pyf]
            so = call(cmd, out=True, shell=False, msg=pyf, c=self.cc, tmdir=td)
            if so:
                new_file_name = pyf[:-3] + ".so"
                shutil.move(so, new_file_name)
                if os.path.isfile(new_file_name):
                    os.remove(pyf)
                fin = True
        if fin:
            self.logger.info("finished %s", pyf)

    def __call__(self, pyfile):
        return self.compile(pyfile, remove=True)

    def compile_all(self, remove=True):
        mg = mp.Manager()
        self.lock = mg.Lock()
        self.tmdir = mg.list()
        p = mp.Pool(self.threads)
        try:
            p.map(self, self.compile_file)
        except WorkerStopException:
            p.close()
            for d in self.tmdir:
                if os.path.isdir(d):
                    shutil.rmtree(d)
            mg.shutdown()
            self.clean_source()
            clean_process()
        return

    def clean_source(self):
        for p, ds, fs in os.walk(self.cdir):
            for d in ds:
                if d == "__pycache__":
                    shutil.rmtree(os.path.join(p, d))
            for f in fs:
                f = os.path.join(p, f)
                if f.endswith(".pyc") and os.path.isfile(f):
                    os.remove(f)
                elif f.endswith(".so"):
                    if os.path.isfile(f[:-3] + ".py"):
                        os.remove(f[:-3] + ".py")
                elif f.endswith(".py"):
                    if os.path.isfile(f[:-3] + ".so") and os.path.isfile(f):
                        os.remove(f)
                elif f.endswith(".c"):
                    if os.path.isfile(f) and (os.path.isfile(f[:-2]+".py") or os.path.isfile(f[:-2]+".so")):
                        os.remove(f)

    def write_setup(self, outfile):
        with open(outfile, "w") as fo:
            fo.write("#!/usr/bin/env python\n")
            ctx = text_wrap('''
                import sys
                import os
                from setuptools import setup
                from Cython.Build import cythonize

                py_file = os.path.abspath(sys.argv[1])
                sys.argv = sys.argv[:1]
                setup(ext_modules=cythonize(
                    py_file, language_level=str(sys.version_info.major), 
                    force=True,
                    nthreads=10,
                    quiet = True),
                    script_args=["build_ext", 
                        "-b", os.path.dirname(__file__), 
                        "-t", os.path.dirname(__file__)]
                    )                                      
                ''')
            fo.write(ctx.strip() + "\n")

    @property
    def logger(self):
        return mp.get_logger()
