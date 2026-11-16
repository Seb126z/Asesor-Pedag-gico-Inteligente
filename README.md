# Asesor Pedagógico Inteligente

Prototipo web para organizar evidencias académicas, gestionar rúbricas, generar una evaluación preliminar explicable y consolidar el aprendizaje de laboratorios de IA.

## Estado de esta entrega

Esta carpeta combina el prototipo HTML entregado por el equipo con una API inicial en FastAPI y persistencia SQLite. La interfaz conserva los módulos de Proyecto, Rúbricas, Evaluación, Informe y Mapa mental. Se añadió conexión con el backend para comprobar su estado, almacenar archivos de evidencia y guardar/aprobar evaluaciones.

**Importante:** el evaluador que viene en el HTML es heurístico y simulado (búsqueda de palabras clave). No es un modelo de IA real y sus notas no deben tratarse como calificaciones académicas definitivas. La integración con un proveedor LLM, la extracción real de documentos y la verificación aislada de código están pendientes. La aprobación docente es una etapa de revisión del prototipo, no un flujo de autenticación institucional.

## Requisitos

- Python 3.10 o superior.
- Navegador moderno.
- Conexión a internet solo para instalar dependencias.

## Ejecución en Windows

Desde la raíz del proyecto:

```powershell
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cd backend
python run.py
```

Abrir http://127.0.0.1:8000. La documentación de la API está en http://127.0.0.1:8000/docs.

Para Linux/macOS, activar el entorno con `source .venv/bin/activate`.

## Estructura

```text
asesor-pedagogico/
├── backend/
│   ├── app/
│   │   ├── api/          # Endpoints REST
│   │   ├── core/         # Configuración y conexión a BD
│   │   ├── models/       # Entidades SQLAlchemy
│   │   ├── schemas/      # Contratos Pydantic
│   │   ├── services/     # Validación de rúbricas y cálculo
│   │   └── main.py       # Aplicación FastAPI y datos iniciales
│   ├── storage/evidencias/ # Archivos cargados (no versionar)
│   └── run.py
├── frontend/index.html   # Interfaz integrada desde el HTML de Claude
├── docs/                 # Documentación del proyecto
├── tests/
├── .env.example
└── requirements.txt
```

## API inicial

- `GET /api/health`: estado del servicio.
- `GET /api/laboratories`: laboratorios y rúbricas.
- `PUT /api/laboratories/{id}/rubric`: actualizar rúbrica validando el 100 %.
- `POST /api/laboratories/{id}/evidence`: cargar una evidencia.
- `GET /api/laboratories/{id}/evidence`: listar evidencias.
- `POST /api/laboratories/{id}/evaluations`: guardar resultado estructurado.
- `PATCH /api/evaluations/{id}/approval`: registrar aprobación y nota final docente.
- `GET /api/evaluations`: consultar evaluaciones.

## Próximas tareas prioritarias

1. Reemplazar datos demostrativos por las descripciones, objetivos, informes y rúbricas oficiales de cada laboratorio y cohorte.
2. Implementar autenticación, roles (estudiante/docente/administrador) y aislamiento de datos por usuario.
3. Extraer texto de PDF y código fuente; analizar ZIP de forma segura y registrar cada archivo.
4. Integrar proveedor LLM configurable con salida validada mediante Pydantic/JSON Schema. El backend debe calcular siempre la nota a partir de pesos y puntuaciones validadas.
5. Implementar verificación de sintaxis, análisis estático y pruebas en sandbox sin red, con límites de CPU, memoria, tiempo y permisos.
6. Persistir versiones inmutables de rúbricas y trazabilidad completa (modelo, versión, prompt, evidencias, verificaciones y ajustes docentes).
7. Completar exportación del informe y descarga del mapa mental.
8. Añadir pruebas automatizadas, despliegue HTTPS y almacenamiento seguro.

## Fuentes de alcance

La especificación funcional se basa en el documento `Proyecto_Final_IA_Asesor_Pedagogico_V3_Rubricas_Verificacion.pdf`. El diseño de interfaz parte de `Asesor Pedagógico Inteligente.html`, entregado por el equipo. Los datos de laboratorios y las descripciones de equipo que no están confirmados se mantienen como demostrativos y deben reemplazarse.
