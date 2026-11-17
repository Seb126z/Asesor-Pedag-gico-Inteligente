# Contrato inicial de API

Base local: `http://127.0.0.1:8000`. La documentación interactiva se publica en `/docs`.

| Método | Ruta | Propósito |
|---|---|---|
| GET | `/api/health` | Estado del servicio |
| GET | `/api/laboratories` | Laboratorios, cohortes y rúbricas |
| GET | `/api/laboratories/{id}` | Detalle de laboratorio |
| PUT | `/api/laboratories/{id}/rubric` | Actualizar rúbrica (ponderaciones = 100 %) |
| POST | `/api/laboratories/{id}/evidence` | Cargar archivo multipart (`file`, `student`) |
| GET | `/api/laboratories/{id}/evidence` | Listar evidencias |
| GET | `/api/evidence/{id}/download` | Descargar evidencia |
| POST | `/api/laboratories/{id}/evaluations` | Guardar evaluación estructurada |
| PATCH | `/api/evaluations/{id}/approval` | Registrar decisión docente |
| GET | `/api/evaluations` | Consultar; filtros `student`, `laboratory_id`, `approved` |
| GET | `/api/analytics/summary` | Resumen de evaluaciones aprobadas por cohorte |
| GET | `/api/mindmap` | Nodos y relaciones de laboratorios/temas |

## Evaluación

`result.crit` debe incluir un elemento por criterio de la rúbrica vigente, en el mismo orden y con el mismo nombre. Cada elemento incluye `criterio` y `score` (0 a 5); puede añadir `evidencia`, `fortaleza`, `brecha` y `nivel`. El backend ignora el valor preliminar del cliente y recalcula la nota con los pesos oficiales. Si la versión de rúbrica cambió, la API responde `409 Conflict`.

La API no invoca todavía ningún LLM. El resultado del HTML es una simulación local y debe identificarse como tal.

## Analítica e informes

### `GET /api/analytics/report`

Devuelve un informe consolidado construido con las evaluaciones aprobadas por el docente y las evidencias registradas.

Parámetros opcionales:
- `cohort`: filtra por número de cohorte (por ejemplo, `1` o `2`).
- `student`: filtra por nombre exacto del estudiante.

La respuesta incluye totales, resultados por cohorte y laboratorio, fortalezas, brechas y recomendaciones de fortalecimiento. Las notas preliminares no se usan para calcular promedios.

`GET /api/analytics/summary` conserva la ruta anterior y devuelve la misma estructura ampliada.

## Mapa de competencias

### `GET /api/mindmap`

Devuelve `nodes` y `edges` para representar competencias, laboratorios, temáticas y evidencias. Acepta los mismos filtros opcionales `cohort` y `student`.

Los nodos de laboratorios y temáticas incluyen promedios cuando existen evaluaciones aprobadas. Los nodos de evidencias incluyen una ruta de descarga (`download_url`).
