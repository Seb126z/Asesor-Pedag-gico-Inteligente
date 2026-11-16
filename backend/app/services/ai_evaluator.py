from pydantic import BaseModel, Field
from typing import List
import os
import json

# Esquema estricto que obliga a la IA a retornar un JSON con formato válido (Tarea 5)
class CriterioResultadoIA(BaseModel):
    name: str = Field(description="Nombre exacto del criterio evaluado según la rúbrica")
    score: float = Field(ge=0.0, le=5.0, description="Puntuación preliminar de 0.0 a 5.0")
    justification: str = Field(description="Justificación técnica basada en la evidencia del estudiante")

class EvaluacionEstructuradaIA(BaseModel):
    summary: str = Field(description="Resumen global del desempeño del estudiante en el laboratorio")
    crit: List[CriterioResultadoIA]
    strengths: List[str]
    weaknesses: List[str]

def evaluar_evidencia_con_ia(texto_o_codigo_evidencia: str, rubrica_laboratorio: list, model_name: str = "llama3.2") -> dict:
    """
    Conecta con el modelo de IA (Ollama local o nube compatible con OpenAI) 
    y valida la salida mediante Structured Outputs con Pydantic (Tareas 4 y 5).
    """
    try:
        from openai import OpenAI
        # Configuración por defecto para Ollama local (puerto 11434) o LM Studio
        client = OpenAI(
            base_url=os.getenv("LLM_BASE_URL", "http://localhost:11434/v1"),
            api_key=os.getenv("LLM_API_KEY", "ollama")
        )
        
        prompt = f"""
        Analiza la siguiente evidencia del estudiante en función de esta rúbrica de evaluación:
        RÚBRICA: {json.dumps(rubrica_laboratorio)}
        
        EVIDENCIA DEL ESTUDIANTE:
        {texto_o_codigo_evidencia}
        """

        response = client.beta.chat.completions.parse(
            model=model_name,
            messages=[
                {"role": "system", "content": "Eres un profesor e ingeniero de software experto, estricto y objetivo."},
                {"role": "user", "content": prompt}
            ],
            response_format=EvaluacionEstructuradaIA,
        )
        
        return response.choices[0].message.parsed.model_dump()
        
    except Exception as e:
        # Fallback de seguridad: Si la IA local no responde, genera un mock estructurado para no bloquear al equipo
        print(f"[Aviso IA]: No se pudo conectar al LLM local ({e}). Usando modo seguro de respaldo.")
        mock_crit = [{"name": item.get("name"), "score": 3.5, "justification": "Evaluación preliminar por defecto (Sin conexión activa a LLM local)."} for item in rubrica_laboratorio]
        return {
            "summary": "Análisis preliminar generado automáticamente por respaldo del sistema.",
            "crit": mock_crit,
            "strengths": ["Estructura de entrega correcta"],
            "weaknesses": ["Validación de IA pendiente de ejecución en firme"]
        }