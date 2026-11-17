"""Pruebas de autenticación y roles. Requieren: python -m pip install pytest httpx"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:  # el "with" ejecuta el arranque (crea tablas y usuarios demo)
        yield c


def login(client, email, password):
    r = client.post("/api/auth/login", data={"username": email, "password": password})
    return r


def headers(client, email, password):
    token = login(client, email, password).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def sample_result():
    return {"crit": [{"score": 4}, {"score": 3}, {"score": 5}]}  # el Lab 1 tiene 3 criterios


def test_health_es_publico(client):
    assert client.get("/api/health").status_code == 200


def test_sin_token_no_hay_acceso(client):
    assert client.get("/api/laboratories").status_code == 401
    assert client.get("/api/evaluations").status_code == 401


def test_login_incorrecto(client):
    assert login(client, "docente@demo.local", "mala-clave").status_code == 401
    assert login(client, "noexiste@demo.local", "docente123").status_code == 401


def test_login_correcto_y_me(client):
    r = login(client, "docente@demo.local", "docente123")
    assert r.status_code == 200 and r.json()["user"]["role"] == "docente"
    me = client.get("/api/auth/me", headers=headers(client, "docente@demo.local", "docente123"))
    assert me.json()["email"] == "docente@demo.local"


def test_token_basura_se_rechaza(client):
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer abc.def.ghi"}).status_code == 401


def test_registro_crea_solo_estudiantes(client):
    r = client.post("/api/auth/register", json={"name": "Ana Prueba", "email": "ana@test.com", "password": "clave12345"})
    assert r.status_code == 201 and r.json()["user"]["role"] == "estudiante"
    again = client.post("/api/auth/register", json={"name": "Ana Prueba", "email": "ANA@test.com", "password": "clave12345"})
    assert again.status_code == 409
    corto = client.post("/api/auth/register", json={"name": "Ana", "email": "b@test.com", "password": "corta"})
    assert corto.status_code == 422


def test_estudiante_no_puede_editar_rubricas_ni_aprobar(client):
    est = headers(client, "estudiante@demo.local", "estudiante123")
    lab = client.get("/api/laboratories/1", headers=est).json()
    put = client.put("/api/laboratories/1/rubric", headers=est, json={"version": lab["rubric_version"], "criteria": lab["rubric"]})
    assert put.status_code == 403
    assert client.patch("/api/evaluations/1/approval", headers=est, json={"approved": True, "final_grade": 5}).status_code == 403


def test_docente_si_edita_rubricas(client):
    doc = headers(client, "docente@demo.local", "docente123")
    lab = client.get("/api/laboratories/1", headers=doc).json()
    put = client.put("/api/laboratories/1/rubric", headers=doc, json={"version": lab["rubric_version"], "criteria": lab["rubric"]})
    assert put.status_code == 200


def test_flujo_completo_evaluacion_y_aprobacion(client):
    est = headers(client, "estudiante@demo.local", "estudiante123")
    doc = headers(client, "docente@demo.local", "docente123")
    otro = headers(client, "ana@test.com", "clave12345")

    r = client.post("/api/laboratories/1/evaluations", headers=est,
                    json={"student": "Quien sea", "rubric_version": "1.0", "preliminary_grade": 0, "result": sample_result()})
    assert r.status_code == 200
    ev_id = r.json()["id"]
    assert r.json()["preliminary_grade"] == 4.0  # 4*0.4 + 3*0.3 + 5*0.3, calculado por el backend

    # Pendiente: el estudiante todavía no la ve; el docente sí.
    assert client.get("/api/evaluations", headers=est).json() == []
    assert client.get(f"/api/evaluations/{ev_id}", headers=est).status_code == 404
    pendientes = client.get("/api/evaluations?approved=false", headers=doc).json()
    assert any(e["id"] == ev_id for e in pendientes)

    # El docente aprueba con comentarios.
    ap = client.patch(f"/api/evaluations/{ev_id}/approval", headers=doc,
                      json={"approved": True, "final_grade": 4.0, "teacher_feedback": "Buen trabajo."})
    assert ap.status_code == 200 and ap.json()["teacher_feedback"] == "Buen trabajo."

    # Publicada: la ve su dueño, pero no otro estudiante.
    mias = client.get("/api/evaluations", headers=est).json()
    assert len(mias) == 1 and mias[0]["final_grade"] == 4.0
    assert client.get(f"/api/evaluations/{ev_id}", headers=est).status_code == 200
    assert client.get(f"/api/evaluations/{ev_id}", headers=otro).status_code == 404
    assert client.get("/api/evaluations", headers=otro).json() == []


def test_aprobar_exige_nota_final(client):
    doc = headers(client, "docente@demo.local", "docente123")
    est = headers(client, "estudiante@demo.local", "estudiante123")
    ev_id = client.post("/api/laboratories/1/evaluations", headers=est,
                        json={"rubric_version": "1.0", "preliminary_grade": 0, "result": sample_result()}).json()["id"]
    assert client.patch(f"/api/evaluations/{ev_id}/approval", headers=doc, json={"approved": True}).status_code == 422
