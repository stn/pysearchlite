from setuptools import setup

setup(
    setup_requires=["cffi>=1.0.0"],
    cffi_modules=["pysearchlite/gamma_codecs_cffi_builder.py:ffibuilder"],
    install_requires=["cffi>=1.0.0"],
)
