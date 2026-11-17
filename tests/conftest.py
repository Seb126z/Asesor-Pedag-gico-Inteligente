"""Configuración común de pruebas: base de datos y carpeta de evidencias temporales.

Debe ejecutarse antes de importar `app`, por eso las variables de entorno se fijan aquí.
"""
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="asesor-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["UPLOAD_DIR"] = f"{_tmp}/evidencias"
os.environ["APP_ENV"] = "development"
os.environ["LLM_BASE_URL"] = "http://127.0.0.1:9/v1"  # puerto cerrado: el evaluador usa el respaldo
os.environ["LLM_TIMEOUT"] = "2"
