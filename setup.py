from setuptools import setup

import bisemantic

setup(
    name="bisemantic",
    version=bisemantic.__version__,
    packages=["bisemantic"],
    url="https://github.com/wpm/bisemantic",
    license="",
    entry_points={
        "console_scripts": ["bisemantic=bisemantic.console:main"],
    },
    author="W.P. McNeill",
    author_email="billmcn@gmail.com",
    description="Text pair classifier",
    install_requires=["pandas", "spacy", "keras>=2.0.5", "numpy", "toolz"]
)
