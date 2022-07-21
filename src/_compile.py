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
        if not os.path.exists(self.pdir):
            self.logger.error("No such file or directory: %s", self.pdir)
            sys.exit(1)
        self.cdir = os.path.abspath(compile_dir)
        self.threads = threads
        self.compile_file = []
        self.edir = [] if exclude_dir is None else exclude_dir
        self.efile = [] if exclude_file is None else exclude_file
        self.interpreter = interpreter
        self.cc = c

    def list_compile_files(self):
        if os.path.isfile(self.pdir):
            copy(self.pdir, self.cdir)
        elif os.path.isdir(self.pdir):
            mkdir(self.cdir)
            cpcmd = "cp -r %s/* %s" % (self.pdir, self.cdir)
            self.call(cpcmd)
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

    def compile(self, pyf):
        self.logger.info("start compile %s file", pyf)
        fin = False
        with tempdir() as td:
            tf = os.path.join(td, "ccbuild_%s" % getGID())
            self.write_setup(tf)
            cmd = [self.interpreter, tf, pyf]
            _so = self.call(cmd, out=True, shell=False,
                            msg=pyf, c=self.cc, tmdir=td)
            if _so:
                new_file_name = pyf[:-3] + ".so"
                shutil.move(_so, new_file_name)
                if os.path.isfile(new_file_name):
                    os.remove(pyf)
                fin = True
        if os.path.isfile(pyf[:-3]+".c"):
            os.remove(pyf[:-3]+".c")
        if fin:
            self.logger.info("finished %s", pyf)

    def __call__(self, pyfile):
        return self.compile(pyfile)

    def compile_all(self):
        if len(self.compile_file) == 0:
            self.list_compile_files()
        p = mp.Pool(self.threads)
        p.map(self, self.compile_file)
        self.clean_tmp()
        self.clean_source()

    def call(self, cmd, out=False, shell=True, msg="", c=False, tmdir=None):
        if not out:
            with open(os.devnull, "w") as fo:
                subprocess.check_call(cmd, shell=shell, stdout=fo, stderr=fo)
            return
        try:
            out = subprocess.check_output(
                cmd, shell=shell, stderr=subprocess.PIPE)
        except Exception:
            if tmdir and os.path.isdir(tmdir):
                shutil.rmtree(tmdir)
            if msg:
                self.logger.error("compile error %s" % msg)
            if not c:
                self.safe_exit_when_error()
            return
        dotso = re.findall(" \-o (.+\.so)\n", out.decode())
        return dotso[0]

    def safe_exit_when_error(self):
        self.clean_tmp()
        self.clean_source()
        clean_process()

    @staticmethod
    def clean_tmp():
        for c in glob.glob("/tmp/*/ccbuild_%s" % getGID()):
            if os.path.isdir(os.path.dirname(c)):
                shutil.rmtree(os.path.dirname(c))

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
                    quiet=True),
                    script_args=["build_ext",
                                 "-b", os.path.dirname(__file__),
                                 "-t", os.path.dirname(__file__)]
                )
                ''')
            fo.write(ctx.strip() + "\n")

    @property
    def logger(self):
        return mp.get_logger()
