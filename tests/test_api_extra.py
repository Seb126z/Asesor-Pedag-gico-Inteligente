"""Evidencias, evaluación con IA (modo respaldo), analítica con permisos y migración de esquema."""
import sqlite3

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def auth(client, email, password):
    token = client.post("/api/auth/login", data={"username": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def upload(client, headers, lab=1, name="informe.txt", content=b"Implemente BFS y A* con heuristica"):
    return client.post(f"/api/laboratories/{lab}/evidence", headers=headers,
                       files={"file": (name, content, "text/plain")})


def test_subida_requiere_sesion_y_tipo_valido(client):
    assert client.post("/api/laboratories/1/evidence",
                       files={"file": ("a.txt", b"x", "text/plain")}).status_code == 401
    est = auth(client, "estudiante@demo.local", "estudiante123")
    assert upload(client, est, name="virus.exe").status_code == 415
    assert upload(client, est, lab=999).status_code == 404


def test_estudiante_solo_ve_y_descarga_sus_evidencias(client):
    est = auth(client, "estudiante@demo.local", "estudiante123")
    doc = auth(client, "docente@demo.local", "docente123")
    client.post("/api/auth/register", json={"name": "Otra Persona", "email": "otra@test.com", "password": "clave12345"})
    otra = auth(client, "otra@test.com", "clave12345")

    ev_id = upload(client, est).json()["id"]
    assert ev_id in [e["id"] for e in client.get("/api/laboratories/1/evidence", headers=est).json()]
    assert client.get("/api/laboratories/1/evidence", headers=otra).json() == []
    assert any(e["id"] == ev_id for e in client.get("/api/laboratories/1/evidence", headers=doc).json())

    ok = client.get(f"/api/evidence/{ev_id}/download", headers=est)
    assert ok.status_code == 200 and b"BFS" in ok.content
    assert client.get(f"/api/evidence/{ev_id}/download", headers=otra).status_code == 404
    assert client.get(f"/api/evidence/{ev_id}/download").status_code == 401


def test_evaluacion_con_nombre_de_criterio_distinto_se_rechaza(client):
    est = auth(client, "estudiante@demo.local", "estudiante123")
    crit = [{"criterio": "Otro", "score": 4}, {"criterio": "Diseño del agente", "score": 3},
            {"criterio": "Análisis de resultados", "score": 5}]
    r = client.post("/api/laboratories/1/evaluations", headers=est,
                    json={"rubric_version": "1.0", "preliminary_grade": 0, "result": {"crit": crit}})
    assert r.status_code == 422


def test_evaluacion_puntaje_fuera_de_rango(client):
    est = auth(client, "estudiante@demo.local", "estudiante123")
    r = client.post("/api/laboratories/1/evaluations", headers=est,
                    json={"rubric_version": "1.0", "preliminary_grade": 0,
                          "result": {"crit": [{"score": 9}, {"score": 3}, {"score": 5}]}})
    assert r.status_code == 422


def test_ai_auto_sin_evidencia_pide_subir_archivo(client):
    client.post("/api/auth/register", json={"name": "Sin Archivos", "email": "sin@test.com", "password": "clave12345"})
    h = auth(client, "sin@test.com", "clave12345")
    assert client.post("/api/laboratories/2/evaluations/ai-auto", headers=h).status_code == 422


def test_ai_auto_usa_respaldo_marcado_y_nota_del_backend(client):
    est = auth(client, "estudiante@demo.local", "estudiante123")
    upload(client, est, lab=1)
    r = client.post("/api/laboratories/1/evaluations/ai-auto", headers=est)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["fallback"] is True and data["ai_analysis"]["modelo"] == "respaldo-sin-llm"
    assert data["preliminary_grade"] == 3.5  # 3.5 en todos los criterios, ponderado por el backend
    assert [c["criterio"] for c in data["ai_analysis"]["crit"]][0] == "Algoritmo de búsqueda"
    # Pendiente de aprobación: el estudiante no la ve todavía
    assert all(e["id"] != data["evaluation_id"] for e in client.get("/api/evaluations", headers=est).json())


def test_analitica_requiere_sesion_y_aisla_estudiantes(client):
    assert client.get("/api/analytics/report").status_code == 401
    assert client.get("/api/mindmap").status_code == 401
    est = auth(client, "estudiante@demo.local", "estudiante123")
    doc = auth(client, "docente@demo.local", "docente123")
    otra = auth(client, "otra@test.com", "clave12345")

    nodos_est = [n for n in client.get("/api/mindmap", headers=est).json()["nodes"] if n["type"] == "evidence"]
    nodos_otra = [n for n in client.get("/api/mindmap", headers=otra).json()["nodes"] if n["type"] == "evidence"]
    nodos_doc = [n for n in client.get("/api/mindmap", headers=doc).json()["nodes"] if n["type"] == "evidence"]
    assert nodos_est and not nodos_otra and len(nodos_doc) >= len(nodos_est)
    assert client.get("/api/analytics/report", headers=otra).json()["totals"]["evidences"] == 0


def test_migracion_agrega_columnas_a_base_antigua(tmp_path, monkeypatch):
    """Una base creada con el esquema anterior (sin student_id, teacher_feedback...) debe repararse sola."""
    db_file = tmp_path / "vieja.db"
    con = sqlite3.connect(db_file)
    con.executescript("""
        CREATE TABLE laboratories (id INTEGER PRIMARY KEY, cohort INTEGER NOT NULL, name VARCHAR(180) NOT NULL,
            topics JSON NOT NULL, rubric_version VARCHAR(20) NOT NULL, rubric JSON NOT NULL, description TEXT NOT NULL);
        CREATE TABLE evidences (id INTEGER PRIMARY KEY, laboratory_id INTEGER NOT NULL, student VARCHAR(160) NOT NULL,
            original_name VARCHAR(255) NOT NULL, stored_name VARCHAR(255) NOT NULL UNIQUE,
            content_type VARCHAR(120) NOT NULL, uploaded_at DATETIME NOT NULL);
        CREATE TABLE evaluations (id INTEGER PRIMARY KEY, laboratory_id INTEGER NOT NULL, student VARCHAR(160) NOT NULL,
            rubric_version VARCHAR(20) NOT NULL, model_name VARCHAR(120) NOT NULL, preliminary_grade FLOAT NOT NULL,
            final_grade FLOAT, approved BOOLEAN NOT NULL, result JSON NOT NULL, created_at DATETIME NOT NULL);
    """)
    con.commit()
    con.close()

    import app.core.database as database
    engine = create_engine(f"sqlite:///{db_file}")
    monkeypatch.setattr(database, "engine", engine)
    database.ensure_schema()
    insp = inspect(engine)
    assert {"student_id"} <= {c["name"] for c in insp.get_columns("evidences")}
    assert {"student_id", "teacher_feedback", "approved_by", "approved_at"} <= {c["name"] for c in insp.get_columns("evaluations")}
    assert insp.has_table("users")
