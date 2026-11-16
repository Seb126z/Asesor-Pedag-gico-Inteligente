# Arquitectura inicial

## Componentes

- **Frontend:** HTML, CSS y JavaScript nativo, conservando el prototipo proporcionado.
- **API:** FastAPI, con contratos Pydantic y documentación OpenAPI.
- **Persistencia:** SQLite mediante SQLAlchemy para facilitar el arranque local; PostgreSQL es una evolución prevista.
- **Archivos:** almacenamiento local por ahora, con validación de extensión y límite de tamaño. Para producción se requiere almacenamiento privado y control de acceso.
- **Evaluación:** el prototipo del navegador simula el análisis. El backend expone contratos para registrar resultados; no se conecta aún a un LLM.

## Flujo esperado

1. Se selecciona un laboratorio y se registra su rúbrica.
2. El backend valida que las ponderaciones sumen 100 %.
3. Se cargan las evidencias y quedan asociadas al laboratorio.
4. Un servicio de análisis futuro extraerá evidencias y consultará el modelo configurado.
5. La salida del modelo se valida estructuralmente.
6. El backend calcula la nota ponderada; el LLM no calcula la nota final.
7. El docente revisa, ajusta y aprueba.
8. Los resultados aprobados alimentan el informe y el mapa de competencias.

## Decisiones y límites

La base SQLite es adecuada para desarrollo local, no para concurrencia de producción. El CORS abierto, la ausencia de autenticación y el almacenamiento local de archivos son únicamente decisiones temporales de prototipo. No ejecutar código aportado por estudiantes dentro del proceso de la API.
