"""
Setup module for the sphinx based documentation.
"""

# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

with open("README.rst", encoding="utf-8") as f:
    readme = f.read()

with open("LICENSE", encoding="utf-8") as f:
    license_mrf = f.read()

setup(
    name="Microservice Reconstruction Framework",
    version="0.0.1",
    description="Repository of the Microservice Reconstruction Framework",
    long_description=readme,
    author="Philip Wizenty",
    author_email="Philip Wizenty",
    url="https://github.com/pwizenty/microservice-reconstruction-framework",
    license_mrf=license,
    packages=find_packages(where="mrf"),
    package_dir={"": "mrf"},
)
