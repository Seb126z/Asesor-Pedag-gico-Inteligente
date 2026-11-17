"""Lectura de PDF y consulta real a un LLM (servidor falso compatible con la API de OpenAI)."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from fastapi.testclient import TestClient
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.main import app
from app.services.evidence_text import extract_text


def make_pdf(path, lines):
    c = canvas.Canvas(str(path), pagesize=letter)
    y = 700
    for line in lines:
        c.drawString(72, y, line)
        y -= 18
    c.save()


def test_extrae_texto_de_pdf(tmp_path):
    pdf = tmp_path / "informe.pdf"
    make_pdf(pdf, ["Implemente BFS y A* con heuristica", "Comparacion de tiempo y complejidad"])
    text, ok = extract_text(pdf, "informe.pdf")
    assert ok and "BFS" in text and "complejidad" in text


def test_pdf_sin_texto_no_se_inventa_contenido(tmp_path):
    pdf = tmp_path / "vacio.pdf"
    c = canvas.Canvas(str(pdf), pagesize=letter)
    c.rect(100, 100, 200, 200)  # solo gráficos, sin texto
    c.save()
    text, ok = extract_text(pdf, "vacio.pdf")
    assert ok is False and "no tiene texto seleccionable" in text


def test_pdf_corrupto_no_rompe(tmp_path):
    pdf = tmp_path / "roto.pdf"
    pdf.write_bytes(b"esto no es un pdf")
    assert extract_text(pdf, "roto.pdf")[1] is False


class FakeLLM(BaseHTTPRequestHandler):
    requests: list = []
    mode = "ok"

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeLLM.requests.append(body)
        if FakeLLM.mode == "down":
            self.send_response(500); self.end_headers(); return
        crit = [{"name": "Algoritmo de búsqueda", "score": 4.5, "justification": "Implementa BFS y A*."},
                {"name": "Diseño del agente", "score": 2.0, "justification": "No describe el agente."},
                {"name": "Análisis de resultados", "score": 4.0, "justification": "Compara tiempos."}]
        content = json.dumps({"summary": "Buen trabajo en búsqueda.", "crit": crit,
                              "strengths": ["BFS y A*"], "weaknesses": ["Falta el agente"]})
        payload = {"id": "x", "object": "chat.completion", "created": 0, "model": body["model"],
                   "choices": [{"index": 0, "finish_reason": "stop",
                                "message": {"role": "assistant", "content": content}}]}
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


@pytest.fixture()
def fake_llm(monkeypatch):
    server = HTTPServer(("127.0.0.1", 0), FakeLLM)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    FakeLLM.requests, FakeLLM.mode = [], "ok"
    monkeypatch.setenv("LLM_BASE_URL", f"http://127.0.0.1:{server.server_port}/v1")
    monkeypatch.setenv("LLM_MODEL", "modelo-prueba")
    yield FakeLLM
    server.shutdown()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def headers(client):
    t = client.post("/api/auth/login", data={"username": "estudiante@demo.local", "password": "estudiante123"}).json()["access_token"]
    return {"Authorization": f"Bearer {t}"}


def subir_pdf(client, h, tmp_path, lines):
    pdf = tmp_path / "entrega.pdf"
    make_pdf(pdf, lines)
    r = client.post("/api/laboratories/1/evidence", headers=h, files={"file": ("entrega.pdf", pdf.read_bytes(), "application/pdf")})
    assert r.status_code == 200


def test_ai_auto_envia_el_texto_del_pdf_al_modelo_y_calcula_la_nota(client, fake_llm, tmp_path):
    h = headers(client)
    subir_pdf(client, h, tmp_path, ["Implemente BFS y A* con heuristica de distancia"])
    r = client.post("/api/laboratories/1/evaluations/ai-auto", headers=h)
    assert r.status_code == 200, r.text
    data = r.json()
    # el PDF se leyó y viajó al modelo, junto con la rúbrica
    prompt = json.dumps(fake_llm.requests[0]["messages"], ensure_ascii=False)
    assert "BFS y A*" in prompt and "Algoritmo de búsqueda" in prompt
    assert fake_llm.requests[0]["model"] == "modelo-prueba"
    # respuesta del modelo usada, no el respaldo
    assert data["fallback"] is False and data["ai_analysis"]["modelo"] == "modelo-prueba"
    # nota calculada por el backend: 4.5*.4 + 2*.3 + 4*.3 = 3.6
    assert data["preliminary_grade"] == 3.6
    assert data["ai_analysis"]["crit"][1]["nivel"] == "Básico" or data["ai_analysis"]["crit"][1]["score"] == 2.0


def test_ai_auto_con_servidor_caido_usa_respaldo(client, fake_llm, tmp_path):
    fake_llm.mode = "down"
    h = headers(client)
    subir_pdf(client, h, tmp_path, ["Texto cualquiera de la entrega"])
    data = client.post("/api/laboratories/1/evaluations/ai-auto", headers=h).json()
    assert data["fallback"] is True and data["ai_analysis"]["modelo"] == "respaldo-sin-llm"


def test_archivo_ilegible_se_rechaza_sin_llamar_al_modelo(client, fake_llm):
    h = headers(client)
    client.post("/api/laboratories/3/evidence", headers=h, files={"file": ("datos.zip", b"PK\x03\x04", "application/zip")})
    r = client.post("/api/laboratories/3/evaluations/ai-auto", headers=h)
    assert r.status_code == 422 and fake_llm.requests == []


def test_mensaje_claro_si_falta_pypdf(tmp_path, monkeypatch):
    import app.services.evidence_text as et
    def sin_pypdf(path):
        raise ImportError("No module named 'pypdf'")
    monkeypatch.setattr(et, "_read_pdf", sin_pypdf)
    pdf = tmp_path / "a.pdf"
    make_pdf(pdf, ["hola"])
    text, ok = et.extract_text(pdf, "a.pdf")
    assert ok is False and "pip install -r requirements.txt" in text
