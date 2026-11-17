# backend/app/services/file_service.py
import os
import zipfile
import tempfile

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

class FileService:
    
    @staticmethod
    def extract_text_from_pdf(file_path: str) -> str:
        """Extrae el texto legible de un informe en PDF del estudiante."""
        if not PdfReader:
            raise ImportError("La librería pypdf no está instalada.")
        
        text = ""
        reader = PdfReader(file_path)
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return text

    @staticmethod
    def extract_zip_content(zip_path: str, extract_to: str = None) -> str:
        """Descomprime archivos ZIP o de código fuente en un directorio temporal."""
        if extract_to is None:
            extract_to = tempfile.mkdtemp()
            
        if not zipfile.is_zipfile(zip_path):
            raise ValueError("El archivo proporcionado no es un ZIP válido.")
            
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
            
        return extract_to