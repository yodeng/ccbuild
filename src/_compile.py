#!/usr/bin/env python

import os
import sys
import glob
import shutil
import logging
import fnmatch

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
        self.edir = exclude_dir or []
        self.efile = exclude_file or []
        self.interpreter = interpreter
        self.cc = c
        self.remove_src = self.pdir != self.cdir

    def list_compile_files(self):
        if os.path.isfile(self.pdir):
            if self.pdir.endswith(self.py_ext):
                copy_to_dir(self.pdir, self.cdir)
                py = os.path.join(self.cdir, os.path.basename(self.pdir))
                self.compile_file.append(py)
                if py == self.pdir:
                    self.remove_src = False
            return
        elif os.path.isdir(self.pdir):
            copy_to_dir(self.pdir, self.cdir)
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
                        if os.path.isfile(os.path.join(p, f).replace(self.cdir, self.pdir)):
                            self.compile_file.append(os.path.join(p, f))

    def compile(self, pyf):
        self.logger.info("start compile %s file", pyf)
        fin = False
        with Tempdir() as td:
            tf = os.path.join(td, "ccbuild.py")
            self.write_setup(tf)
            cmd = [self.interpreter, tf, pyf]
            _so = self.call(cmd, out=True, shell=False,
                            msg=pyf, c=self.cc)
            if _so:
                new_file_name = pyf[:-3] + ".so"
                shutil.move(_so, new_file_name)
                if os.path.isfile(new_file_name):
                    self.remove_file(pyf)
                fin = True
        self.remove_file(pyf[:-3]+".c")
        if fin:
            self.logger.info("finished %s", pyf)

    def __call__(self, pyfile):
        return self.compile(pyfile)

    def compile_all(self):
        if len(self.compile_file) == 0:
            self.list_compile_files()
        nproc = min(self.threads, len(self.compile_file))
        try:
            if nproc > 1:
                with ProcessPoolExecutor(nproc) as p:
                    p.map(self, self.compile_file)
            else:
                self.compile(self.compile_file[0])
        except:
            self.safe_exit()
        self.clean_source()

    def call(self, cmd, out=False, shell=True, msg="", c=False):
        if not out:
            with open(os.devnull, "w") as fo:
                subprocess.check_call(cmd, shell=shell, stdout=fo, stderr=fo)
            return
        try:
            p = subprocess.Popen(
                cmd, shell=shell, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            out, e = p.communicate()
            if p.returncode != 0:
                raise RuntimeError()
        except (BaseException, KeyboardInterrupt) as err:
            self.logger.debug(e.decode())
            if msg:
                self.logger.error("compile error %s" % msg)
            self.safe_exit()
            return
        dotso = re.findall(" \-o (.+\.so)\n", out.decode())
        return dotso[0]

    def safe_exit(self):
        if not self.cc:
            self.clean_source()
            self.clean_tmp()
            sys.exit(1)

    @staticmethod
    def clean_tmp():
        td = os.path.join(tempfile.gettempdir(), "*", "ccbuild.py")
        for c in glob.glob(td):
            if os.path.isdir(os.path.dirname(c)):
                try:
                    shutil.rmtree(os.path.dirname(c))
                except:
                    pass

    def clean_source(self):
        for p, ds, fs in os.walk(self.cdir):
            for d in ds:
                if d == "__pycache__":
                    shutil.rmtree(os.path.join(p, d))
            for f in fs:
                f = os.path.join(p, f)
                if f.endswith(".pyc"):
                    self.remove_file(f)
                elif f.endswith(".so"):
                    self.remove_file(f[:-3] + ".py")
                elif f.endswith(".py"):
                    if os.path.isfile(f[:-3] + ".so"):
                        self.remove_file(f)
                elif f.endswith(".c"):
                    if os.path.isfile(f[:-2]+".py") or os.path.isfile(f[:-2]+".so"):
                        self.remove_file(f)

    def remove_file(self, path):
        if os.path.isfile(path):
            if not path.endswith(".py") or self.remove_src:
                os.remove(path)

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
        return logging.getLogger()
