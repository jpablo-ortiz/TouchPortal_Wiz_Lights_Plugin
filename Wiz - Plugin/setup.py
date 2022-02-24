from distutils.core import setup

import py2exe

setup(
    name="Wiz",
    version="1.0",
    description="Wiz Touch Portal Plugin",
    author="Juan Pablo Ortiz - Lomito",
    scripts=["wiz.py"],
    console=["wiz.py"],
    options={"py2exe": {"bundle_files": 1}},
    zipfile=None,
)

# Para ejecutar el setup.py
# En la consola poner: python setup.py py2exe
