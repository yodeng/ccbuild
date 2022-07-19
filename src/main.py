#!/usr/bin/env python
# coding:utf-8

from .utils import *
from ._compile import *


def main():
    args = Argparse()
    log = Mylog(multi=True)
    if not check_cython(args.python):
        log.error("No module named cython for %s", args.python)
        sys.exit(1)
    cp = CompileProject(args.input, args.output,
                        args.exclude_dir, args.exclude_file, args.python, args.threads, args.compile_continue)
    cp.list_compile_files()
    log.info("detect %s files for compile, Interpreter: %s",
             len(cp.compile_file), args.python)
    cp.compile_all()
    cp.clean_source()


if __name__ == "__main__":
    main()
