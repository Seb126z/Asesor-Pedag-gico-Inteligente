"""Servicios extraídos de las rutas: cálculo de notas, niveles, datos semilla y análisis de archivos."""
import zipfile
from types import SimpleNamespace

import pytest

from app.services.evidence_text import analyze_upload
from app.services.grading import FALLBACK_MODEL, InvalidResult, build_ai_result, grade_manual_result
from app.services.rubrics import score_level, validate_rubric
from app.services.seed import LABORATORIES

RUBRIC = [{"name": "Algoritmo", "weight": 40}, {"name": "Agente", "weight": 60}]


def test_nota_manual_usa_pesos_oficiales():
    assert grade_manual_result(RUBRIC, [{"score": 5}, {"criterio": " agente ", "score": 2.5}]) == 3.5


@pytest.mark.parametrize("crit", [
    [{"score": 5}],                                   # faltan criterios
    "no es lista",
    [{"score": 5}, "no es objeto"],
    [{"score": 5}, {"criterio": "Otro", "score": 3}],  # nombre distinto
    [{"score": 5}, {"score": "x"}],                   # no numérico
    [{"score": 5}, {"score": 5.1}],                   # fuera de rango
])
def test_nota_manual_rechaza_resultados_invalidos(crit):
    with pytest.raises(InvalidResult):
        grade_manual_result(RUBRIC, crit)


def test_resultado_ia_empareja_por_nombre_y_marca_criterios_faltantes():
    lab = SimpleNamespace(name="Lab", rubric_version="1.0", rubric=RUBRIC)
    ai = {"crit": [{"name": "ALGORITMO", "score": 9, "justification": "ok"}], "fallback": False}
    result = build_ai_result(lab, ai, "a.txt", True, "modelo-x")
    algoritmo, agente = result["crit"]
    assert algoritmo["score"] == 5.0 and algoritmo["nivel"] == "Sobresaliente"   # se acota a 5
    assert agente["score"] == 0.0 and agente["brecha"] == "Criterio sin evaluar"
    assert result["preliminary_grade"] == 2.0 and result["modelo"] == "modelo-x"


def test_resultado_ia_de_respaldo_se_identifica():
    lab = SimpleNamespace(name="Lab", rubric_version="1.0", rubric=RUBRIC)
    assert build_ai_result(lab, {"fallback": True}, "a.txt", True, "m")["modelo"] == FALLBACK_MODEL


@pytest.mark.parametrize("score,level", [(5, "Sobresaliente"), (4.5, "Sobresaliente"), (3.5, "Alto"),
                                         (2.5, "Básico"), (0.1, "Bajo"), (0, "Sin evidencia")])
def test_niveles(score, level):
    assert score_level(score) == level


def test_rubricas_semilla_son_validas():
    assert len(LABORATORIES) == 6
    assert all(validate_rubric(rubric)["valid"] for *_, rubric in LABORATORIES)


def test_analisis_de_zip_lista_codigo_sin_extraer(tmp_path):
    path = tmp_path / "entrega.zip"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("src/main.py", "print(1)")
        zf.writestr("img/foto.png", b"\x89PNG")
    info = analyze_upload(path, "entrega.zip")
    assert info == {"total_files": 2, "code_files_found": ["src/main.py"]}
    assert not (tmp_path / "src").exists()
    bad = tmp_path / "roto.zip"
    bad.write_bytes(b"no zip")
    assert "error" in analyze_upload(bad, "roto.zip")
