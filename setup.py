import os
import sysconfig

from setuptools import setup
from setuptools.extension import Extension

PKG = "ccbuild"


def get_version():
    v = {}
    with open("src/_version.py") as fi:
        c = fi.read()
    exec(compile(c, "src/_version.py", "exec"), v)
    return v["__version__"]


def listdir(path):
    df = []
    for a, b, c in os.walk(path):
        if os.path.basename(a).startswith("__"):
            continue
        for i in c:
            if i.startswith("__"):
                continue
            p = os.path.join(a, i)
            df.append(p)
    return df


def getExtension():
    extensions = []
    for f in listdir("src"):
        e = Extension(PKG + "." + os.path.splitext(os.path.basename(f))[0],
                      [f, ], extra_compile_args=["-O3", ],)
        e.cython_directives = {
            'language_level': sysconfig._PY_VERSION_SHORT_NO_DOT[0]}
        extensions.append(e)
    return extensions


def getdes():
    des = ""
    with open(os.path.join(os.getcwd(), "README.md")) as fi:
        des = fi.read()
    return des


setup(
    name=PKG,
    version=get_version(),
    packages=[PKG],
    license="MIT",
    #package_dir={PKG: "src"},
    install_requires=["setuptools", "cython"],
    python_requires='>=2.7, <=3.10',
    ext_modules=getExtension(),
    long_description=getdes(),
    long_description_content_type='text/markdown',
    entry_points={
        'console_scripts': [
            '%s = %s.main:main' % (PKG, PKG),
        ]
    }
)
