# AI Researcher at Tribu IA Latam | AI Builder | Machine Learning
# Alejandro Ospina Mejía - Fecha: 25/02/2025

# Estructura Detallada del Módulo Researcher 

## 📁 researcher/
### 📁 application/
#### 📁 decorators/
- Contiene decoradores para aspectos transversales de la aplicación
- `metrics_decorator.py`: Decorador para tracking de métricas de rendimiento

#### 📁 interfaces/
- Define las interfaces y contratos que deben implementar los servicios

#### 📁 use_cases/
Implementación de la lógica de negocio específica:
- `generate_initial_queries.py`: Generación de consultas iniciales
- `generate_queries.py`: Gestión de consultas
- `initialize_research.py`: Inicialización de investigación
- `manage_research_state.py`: Gestión de estados
- `recover_section_state.py`: Recuperación de estados
- `research_section.py`: Lógica de investigación
- `search_web_queries.py`: Búsquedas web con sistema de proveedores
- `validate_query.py`: Validación de consultas
- `web_search.py`: Búsqueda web
- `write_section.py`: Escritura de secciones

### 📁 domain/
#### 📁 entities/
Entidades principales del dominio:
- `metrics_data.py`: Estructura de datos para métricas
- `query_validation.py`: Validación de consultas
- `research_state_schema.py`: Schema de estado de investigación
- `research_status.py`: Estados de investigación
- `search_engine.py`: Motor de búsqueda
- `language_model.py`: Modelo de lenguaje

#### 📁 interfaces/
- Interfaces del dominio que definen contratos core
- `search_provider.py`: Nueva interfaz para proveedores de búsqueda

### 📁 infrastructure/
#### 📁 persistence/
- Implementaciones de persistencia de datos
- Repositorios concretos

#### 📁 repositories/
- Implementaciones concretas de los repositorios definidos en el dominio

#### 📁 services/
Implementaciones de servicios externos:
- `gemini_service.py`: Integración con Google Gemini AI
- `progress_notifier.py`: Notificaciones de progreso
- `prompt_generation_service.py`: Generación de prompts
- `search_provider_manager.py`: Nuevo gestor de proveedores de búsqueda
- `search_providers.py`: Implementaciones de proveedores de búsqueda
- `jina_service.py`: Integración con Jina AI para búsquedas web

### 📁 presentation/
Capa de presentación:
- `researcher.py`: Clase principal ResearchManager que:
  - Orquesta todos los casos de uso
  - Gestiona el flujo de investigación
  - Maneja la inicialización de servicios
  - Coordina las operaciones entre capas

## Sistema de Proveedores de Búsqueda

### 🔍 Nuevo Sistema de Proveedores
Implementado en `search_providers.py` y gestionado por `search_provider_manager.py`:

1. **Jerarquía de Proveedores**
   - GeminiGroundingProvider (Prioridad 1)
   - GeminiNormalProvider (Prioridad 2)
   - JinaProvider (Prioridad 3)
   - SerpProvider (Prioridad 4)
   - DuckDuckGoProvider (Prioridad 5)

2. **Gestión de Disponibilidad**
   - Verificación automática de disponibilidad
   - Cambio dinámico entre proveedores
   - Sistema de prioridades configurable

3. **Integración con Sistema Existente**
   - Compatibilidad con búsquedas existentes
   - Sistema de fallback en cascada
   - Mantenimiento de patrones de resiliencia

## Patrones de Resiliencia Implementados

### 🛡️ Configuración de Resiliencia
Implementada en `search_web_queries.py` con doble capa de protección:

1. **Sistema de Proveedores**
   - Gestión automática de fallos
   - Cambio dinámico entre proveedores
   - Priorización inteligente

2. **Bulkhead Pattern**
   - Control de concurrencia mediante `asyncio.Semaphore(3)`
   - Limita búsquedas web simultáneas
   - Previene sobrecarga del sistema

3. **Timeout Pattern**
   Configuraciones temporales:
   - Búsqueda web: 30 segundos
   - Operaciones default: 20 segundos

4. **Fallback Services**
   Sistema de respaldo en dos niveles:
   
   **Nivel 1: Sistema de Proveedores**
   - Gemini Grounding (principal)
   - Gemini Normal (primer respaldo)
   - Jina (segundo respaldo)
   - SERP API (tercer respaldo)
   - DuckDuckGo (cuarto respaldo)

   **Nivel 2: Sistema Legacy**
   - Jina (principal)
   - SERP API (primer respaldo)
   - DuckDuckGo (segundo respaldo)

## Patrones de Diseño Utilizados

- Clean Architecture
- Dependency Injection
- Repository Pattern
- Use Case Pattern
- Strategy Pattern (nuevo sistema de proveedores)
- SOLID Principles

## Flujo de Búsqueda

1. **Inicio de Búsqueda**
   - Recepción de consulta
   - Evaluación de complejidad

2. **Sistema de Proveedores**
   - Intento con proveedores en orden de prioridad
   - Gestión automática de fallos
   - Cambio dinámico entre proveedores

3. **Sistema de Fallback**
   - Activación si fallan todos los proveedores
   - Uso del sistema legacy como respaldo
   - Garantía de continuidad del servicio
