import sphinx_rtd_theme

import jflib

html_theme = "sphinx_rtd_theme"
html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

extensions = []
extensions += ["sphinx.ext.autodoc"]
extensions += ["sphinx.ext.intersphinx"]
extensions += ["sphinx.ext.viewcode"]

templates_path = ["_templates"]
source_suffix = ".rst"

master_doc = "index"

project = "jflib"
copyright = "2019, Josef Friedrich"
author = "Josef Friedrich"
version = jflib.__version__
release = jflib.__version__
language = "en"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
pygments_style = "sphinx"
todo_include_todos = False
html_static_path = []
htmlhelp_basename = "jflibdoc"
autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "private-members": False,
    "special-members": False,
    "show-inheritance": False,
}
intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}
