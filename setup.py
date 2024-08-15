# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

with open('README.rst') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='Microservice Reconstruction Framework',
    version='0.0.1',
    description='Repository of the Microservice Reconstruction Framework',
    long_description=readme,
    author='Philip Wizenty',
    author_email='Philip Wizenty',
    url='https://github.com/pwizenty/microservice-reconstruction-framework',
    license=license,
    packages=find_packages(exclude=('tests', 'docs'))
)