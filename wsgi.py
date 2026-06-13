"""WSGI entry point for PythonAnywhere deployment."""
import sys
from pathlib import Path

project_home = Path(__file__).resolve().parent
if str(project_home) not in sys.path:
    sys.path.insert(0, str(project_home))

from app import create_app
flask_app, _ = create_app()
application = flask_app
