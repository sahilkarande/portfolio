# PythonAnywhere WSGI file.
# Copy this into the file linked from the Web tab ("WSGI configuration file"),
# replacing everything in it, and change USERNAME to your PythonAnywhere username.
import sys

PROJECT = "/home/USERNAME/portfolio"
if PROJECT not in sys.path:
    sys.path.insert(0, PROJECT)

from app import app as application  # noqa: E402,F401  (.env is loaded by portfolio/config.py)
