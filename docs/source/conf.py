"""
Configuration file for the Sphinx configuration.
Uses the Google documentation style.
"""

import sys
import os
from pathlib import Path

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

PROJECT = "Microservice Reconstruction Framework"
COPYRIGHT = "2024, Philip Wizenty"
AUTHOR = "Philip Wizenty"
RELEASE = "0.0.1"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.duration",
    "sphinx.ext.doctest",
    "sphinx.ext.autodoc",
    "sphinxcontrib-napoleon",
]

templates_path = ["_templates"]
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

HTML_THEME = "furo"
html_static_path = ["_static"]

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, os.path.abspath("../../mrf"))
