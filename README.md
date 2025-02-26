# Agente Documentador LangGraph

Sistema de documentación automática basado en LangGraph que investiga y genera reportes técnicos detallados sobre herramientas, APIs y frameworks.

## 🌟 Características

- **Investigación automatizada**: Genera consultas de búsqueda inteligentes y recopila información relevante de múltiples fuentes.
- **Estructura modular**: Arquitectura basada en agentes para investigación, planificación y compilación.
- **Generación completa de informes**: Reportes completos con introducción, análisis y recomendaciones.
- **Multi-formato**: Generación de documentos en Markdown, PDF y DOCX.
- **Interfaz WebSocket**: Streaming en tiempo real del proceso de generación.
- **Contenido en español**: Optimizado para generar documentación técnica en español.

## 🏗️ Arquitectura

El sistema utiliza una arquitectura de agentes cooperativos basados en LangGraph:

### Componentes principales

1. **ResearchManager**: Gestiona el proceso de investigación sobre un tema específico.
2. **ReportPlanner**: Planifica la estructura del informe y crea las secciones necesarias.
3. **ReportWriter**: Redacta las secciones del informe utilizando la información recopilada.
4. **ReportCompiler**: Compila todas las secciones en un documento final coherente.

### Diagrama de flujo del proceso

```
[Inicio] → [Planificación] → [Investigación] → [Recopilación de datos] → [Redacción] → [Compilación] → [Reporte final]
```

## 🛠️ Tecnologías

- **LangGraph**: Framework para la orquestación de agentes de IA.
- **FastAPI**: Servidor web con soporte para WebSockets.
- **LangChain**: Integración con diversos LLMs y herramientas.
- **Google Gemini**: Modelo primario para generación de contenido.
- **Tavily**: API de búsqueda para investigación en la web.
- **Poetry**: Gestión de dependencias.
- **Docker**: Containerización para despliegue simplificado.

## 🚀 Instalación

### Prerrequisitos

- Python 3.11+
- Poetry
- Docker y Docker Compose (opcional)
- Claves de API para:
  - Google AI (Gemini)
  - Tavily
  - Jina AI (opcional)
  - OpenAI (opcional)

### Instalación con Poetry

```bash
# Clonar el repositorio
git clone https://github.com/tu-usuario/agente-documentador.git
cd agente-documentador

# Instalar dependencias
poetry install

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus claves de API

# Ejecutar la aplicación
poetry run uvicorn main:app --host 0.0.0.0 --port 8098 --reload
```

### Instalación con Docker

```bash
# Construir y ejecutar con Docker Compose
docker-compose up -d
```

## 💻 Uso

### API REST

```bash
# Verificar estado del servicio
curl http://localhost:8098/health

# Otras operaciones disponibles mediante WebSockets
```

### Conexión WebSocket

```javascript
// Ejemplo de conexión WebSocket
const socket = new WebSocket('ws://localhost:8098/ws');

// Iniciar investigación
socket.send(JSON.stringify({
  type: 'start_research',
  title: 'LangChain',
  description: 'Framework para desarrollo de aplicaciones basadas en LLMs',
  assignmentId: 'task-123'
}));

// Recibir actualizaciones en tiempo real
socket.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
};
```

## 📁 Estructura del proyecto

```
.
├── app/                    # Núcleo de la aplicación
│   ├── agents/             # Agentes de IA
│   ├── config/             # Configuración
│   ├── graph/              # Grafos de LangGraph
│   ├── services/           # Servicios externos (APIs)
│   └── utils/              # Utilidades
├── backend/                # Infraestructura backend
│   ├── server/             # Servidor web
│   └── websockets/         # Gestión de WebSockets
├── .env.example            # Plantilla de variables de entorno
├── Dockerfile              # Configuración de Docker
├── docker-compose.yml      # Configuración de Docker Compose
├── main.py                 # Punto de entrada principal
├── pyproject.toml          # Configuración de Poetry
└── README.md               # Este archivo
```

## 🧪 Desarrollo

### Comandos útiles

```bash
# Ejecutar la aplicación con recarga automática
make run-reload

# Ejecutar tests
make test

# Generar requirements.txt
make gen-req

# Limpiar archivos temporales
make clean

# Ejecutar agente LangGraph
make run-agent
```

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor, sigue estos pasos:

1. Haz fork del repositorio
2. Crea una rama para tu característica (`git checkout -b feature/amazing-feature`)
3. Haz commit de tus cambios (`git commit -m 'Add some amazing feature'`)
4. Haz push a la rama (`git push origin feature/amazing-feature`)
5. Abre un Pull Request


## ✉️ Contacto

Si tienes preguntas o comentarios, no dudes en abrir un issue en el repositorio.
