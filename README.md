# Generador de Reportes Multiagente con LangGraph y FastAPI

Este proyecto es un sistema de generación de reportes basado en una arquitectura multiagente utilizando **LangGraph** y **FastAPI**. El sistema permite a los usuarios generar reportes técnicos de manera automatizada, proporcionando un tema y una estructura opcional.

## Características

- **Arquitectura Multiagente**:
  - **Planner**: Divide el tema en secciones y genera un plan para el reporte.
  - **Researcher**: Busca información relevante en la web para secciones específicas.
  - **Writer**: Genera contenido para las secciones del reporte.
  - **Compiler**: Ensambla todas las secciones en un reporte final coherente.

- **Integración con FastAPI**:
  - Endpoints RESTful para interactuar con el sistema.
  - Implementación sencilla y extensible.

- **Soporte para LangGraph**:
  - Flujos configurables para la coordinación de agentes.
  - Optimización de tareas concurrentes.

## Requisitos Previos

- Python 3.8 o superior
- Conexión a internet para búsqueda de información
- Clave API para servicios externos (como Tavily y OpenAI)

## Instalación

1. Clona el repositorio:
   ```bash
   git clone https://github.com/tu-usuario/tu-repositorio.git
   cd tu-repositorio
