"""Extracción de texto de evidencias para el evaluador.

Soporta texto plano/código y PDF con capa de texto (vía pypdf). Los PDF escaneados (solo imagen),
DOCX, ZIP, etc. siguen pendientes: en esos casos se informa que no hay texto en lugar de inventar contenido.
"""
import zipfile
from pathlib import Path

TEXT_SUFFIXES = {".txt", ".py", ".js", ".html", ".md", ".csv", ".json"}
CODE_SUFFIXES = (".py", ".js", ".java", ".cpp", ".txt", ".json", ".html", ".sql")
MAX_CHARS = 20_000
MAX_PDF_PAGES = 60
PREVIEW_CHARS = 600


def _read_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    if reader.is_encrypted:
        try:
            if not reader.decrypt(""):
                return ""
        except Exception:
            return ""
    parts, total = [], 0
    for number, page in enumerate(reader.pages[:MAX_PDF_PAGES], start=1):
        try:
            text = (page.extract_text() or "").strip()
        except Exception:
            continue
        if text:
            parts.append(f"--- Página {number} ---\n{text}")
            total += len(text)
        if total >= MAX_CHARS:
            break
    return "\n".join(parts)[:MAX_CHARS]


def extract_text(path: Path, original_name: str) -> tuple[str, bool]:
    """Devuelve (texto, se_extrajo_contenido)."""
    suffix = Path(original_name).suffix.lower()
    if path.is_file():
        if suffix in TEXT_SUFFIXES:
            with path.open("r", encoding="utf-8", errors="replace") as fh:
                text = fh.read(MAX_CHARS)
            if text.strip():
                return text, True
        elif suffix == ".pdf":
            try:
                text = _read_pdf(path)
            except ImportError:
                return ("[Falta instalar la librería pypdf en el servidor: ejecuta "
                        "`pip install -r requirements.txt` y reinicia el servidor.]"), False
            except Exception:
                text = ""
            if text.strip():
                return text, True
            return (f"[El PDF '{original_name}' no tiene texto seleccionable: parece un escaneo o una imagen "
                    "(o está dañado/protegido). Expórtalo de nuevo como PDF con texto, o sube un .txt.]"), False
    return (f"[Archivo '{original_name}': no se pudo extraer texto de este tipo de archivo. "
            "No hay contenido para evaluar.]"), False


def analyze_upload(path: Path, original_name: str) -> dict:
    """Resumen rápido del archivo recién subido (no lo modifica y no extrae el ZIP al disco)."""
    suffix = Path(original_name).suffix.lower()
    if suffix == ".pdf" or suffix in TEXT_SUFFIXES:
        preview, readable = extract_text(path, original_name)
        return {"readable": readable, "total_characters": len(preview) if readable else 0,
                "preview": preview[:PREVIEW_CHARS] if readable else None}
    if suffix == ".zip":
        try:
            with zipfile.ZipFile(path) as zf:
                names = [n for n in zf.namelist() if not n.endswith("/")]
        except zipfile.BadZipFile:
            return {"error": "El ZIP está dañado o no es válido"}
        code = [n for n in names if n.lower().endswith(CODE_SUFFIXES)]
        return {"total_files": len(names), "code_files_found": code[:50]}
    return {}
