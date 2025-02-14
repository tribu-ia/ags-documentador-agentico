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
- `search_web_queries.py`: Búsquedas web
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

#### 📁 repositories/
Interfaces de repositorios:
- `research_repository.py`: Interfaz principal para persistencia

#### 📁 interfaces/
- Interfaces del dominio que definen contratos core

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
- `jina_service.py`: Integración con Jina AI para búsquedas web

### 📁 presentation/
Capa de presentación:
- `researcher.py`: Clase principal ResearchManager que:
  - Orquesta todos los casos de uso
  - Gestiona el flujo de investigación
  - Maneja la inicialización de servicios
  - Coordina las operaciones entre capas

## Flujo de Datos y Dependencias

1. **Presentation Layer** (`researcher.py`)
   - Punto de entrada principal
   - Coordina casos de uso
   - Maneja dependencias

2. **Application Layer** (use_cases)
   - Implementa la lógica de negocio
   - Utiliza interfaces del dominio
   - Coordina entidades y servicios

3. **Domain Layer**
   - Define entidades core
   - Establece reglas de negocio
   - Define interfaces de repositorio

4. **Infrastructure Layer**
   - Implementa servicios externos
   - Proporciona persistencia de datos
   - Implementa notificaciones

## Responsabilidades Principales

- **Entidades**: Representan objetos del dominio
- **Casos de Uso**: Implementan lógica de negocio
- **Servicios**: Proporcionan funcionalidades externas
- **Repositorios**: Manejan persistencia de datos
- **ResearchManager**: Orquesta el flujo completo

## Patrones de Diseño Utilizados

- Clean Architecture
- Dependency Injection
- Repository Pattern
- Use Case Pattern
- SOLID Principles 

## Patrones de Resiliencia Implementados

### 🛡️ Configuración de Resiliencia
Implementada en `search_web_queries.py` para garantizar robustez en búsquedas web:

1. **Bulkhead Pattern**
   - Control de concurrencia mediante `asyncio.Semaphore(3)`
   - Limita búsquedas web simultáneas
   - Previene sobrecarga del sistema

2. **Timeout Pattern**
   Configuraciones temporales:
   - Búsqueda web: 30 segundos
   - Operaciones default: 20 segundos

3. **Retry Pattern**
   Para servicio Jina:
   - Máximo 3 intentos
   - Backoff exponencial
   - Reintentos específicos para errores de conexión

4. **Fallback Services**
   Servicios de búsqueda en cascada:
   - Jina (principal)
   - SERP API (primer respaldo)
   - DuckDuckGo (segundo respaldo)