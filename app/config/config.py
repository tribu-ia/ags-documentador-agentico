from functools import lru_cache
from typing import Optional, Any
from pydantic_settings import BaseSettings
from dataclasses import dataclass, field, fields
from dotenv import load_dotenv
from langchain_core.runnables import RunnableConfig
import os

# Cargar las variables del archivo .env
load_dotenv()


@dataclass(kw_only=True)
class LangGraphConfig:
    """Configuración específica para LangGraph"""
    number_of_queries: int = 2
    tavily_topic: str = "general"
    tavily_days: str = None

    @classmethod
    def from_runnable_config(
            cls, config: Optional[RunnableConfig] = None
    ) -> "LangGraphConfig":
        """Crear configuración desde RunnableConfig de LangGraph"""
        configurable = (
            config["configurable"] if config and "configurable" in config else {}
        )
        values: dict[str, Any] = {
            f.name: os.environ.get(f.name.upper(), configurable.get(f.name))
            for f in fields(cls)
            if f.init
        }
        return cls(**{k: v for k, v in values.items() if v})


class Settings(BaseSettings):
    tavily_api_key: str
    openai_api_key: str
    google_api_key: str
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    # Azure OpenAI Settings
    azure_openai_api_key: Optional[str] = None
    azure_openai_api_base: Optional[str] = None
    azure_openai_api_version: Optional[str] = "2024-02-15"
    azure_openai_deployment_name: Optional[str] = None
    # LLM Configuration
    default_llm_type: str = "gpt-4o-mini"
    GPT_4O_MINI: str = "gpt-4o-mini"
    default_temperature: float = 0
    # Monitoring Configuration
    langchain_project: str
    langsmith_tracing: bool = True
    langsmith_api_key: str
    langsmith_endpoint: str
    langsmith_project: str
    # Report configuration
    report_structure: str = """# Guía Completa para Analizar Soluciones Basadas en Agentes

## Introducción

Esta guía proporciona un enfoque estructurado para analizar y presentar soluciones basadas en agentes. Al seguir estas pautas, crearás análisis consistentes y valiosos que ayudarán a nuestra comunidad a comprender y comparar diferentes herramientas y productos en el ecosistema de agentes de IA.

## Antes de Comenzar

Antes de iniciar tu análisis, asegúrate de tener:
- Acceso a la documentación de la solución
- Comprensión básica del propósito de la solución
- Capacidad para probar o implementar la solución (si es posible)
- Conocimiento del público objetivo y casos de uso
- Comprensión de soluciones similares en el espacio

## Proceso de Análisis

### Paso 1: Clasificación Inicial

Comienza determinando dónde encaja la solución en el ecosistema. Esto proporciona un contexto importante para el resto de tu análisis.

#### Categoría Principal:
- **Herramienta de Desarrollo**: Marcos de trabajo o bibliotecas utilizadas para construir sistemas de agentes
- **Plataforma**: Entornos para desplegar y gestionar agentes
- **Producto Final**: Soluciones basadas en agentes listas para usar

#### Nivel de Implementación:
- **Bajo Nivel**: Herramientas de implementación directa de agentes
- **Nivel Medio**: Orquestación y gestión de agentes
- **Alto Nivel**: Soluciones completas basadas en agentes

Documenta tu clasificación y proporciona una breve explicación de tu elección.

### Paso 2: Análisis de Preguntas Fundamentales

#### "¿Qué hace?"

Céntrate en proporcionar información clara y concreta sobre las capacidades de la solución.

**Elementos requeridos**:
- Escribe una declaración del problema en una oración
- Identifica el tipo de usuario principal
- Enumera las capacidades clave (mínimo 3, máximo 5)
- Documenta los tipos de entrada/salida soportados
- Define el alcance de la funcionalidad

**Formato de ejemplo**:
```markdown
### Propósito Principal
Esta solución [describir función principal] para [usuario objetivo] mediante [mecanismo clave].

### Capacidades Clave
1. [Capacidad 1]: [Breve explicación]
2. [Capacidad 2]: [Breve explicación]
3. [Capacidad 3]: [Breve explicación]

### Alcance Técnico
- Entradas: [Listar tipos de entrada soportados]
- Salidas: [Listar tipos de salida soportados]
- Cobertura Funcional: [Describir alcance]
```

#### "¿Cómo funciona?"

Céntrate en la arquitectura técnica y los detalles de implementación.

**Elementos requeridos**:
- Identificar el patrón de arquitectura central
- Explicar el modelo de organización de agentes
- Describir componentes técnicos clave
- Listar dependencias externas
- Explicar el modelo de interacción

**Formato de ejemplo**:
```markdown
### Arquitectura Técnica
La solución emplea [patrón de arquitectura] con [características clave].

### Estructura de Componentes
- Componentes Principales:
  - [Componente 1]: [Propósito]
  - [Componente 2]: [Propósito]
  - [Componente 3]: [Propósito]

### Dependencias y Requisitos
- Requeridos: [Listar dependencias necesarias]
- Opcionales: [Listar mejoras opcionales]
```

#### "¿Cuándo deberías usarlo?"

Céntrate en escenarios de aplicación práctica y limitaciones.

**Elementos requeridos**:
- Documenta tres casos de uso específicos
- Lista prerrequisitos técnicos
- Define la escala operativa
- Identifica escenarios no adecuados
- Compara con alternativas

**Formato de ejemplo**:
```markdown
### Casos de Uso Ideales
1. [Caso de Uso 1]
   - Escenario: [Descripción]
   - Beneficios: [Ventajas clave]
   - Requisitos: [Qué se necesita]

2. [Caso de Uso 2]
   - Escenario: [Descripción]
   - Beneficios: [Ventajas clave]
   - Requisitos: [Qué se necesita]

3. [Caso de Uso 3]
   - Escenario: [Descripción]
   - Beneficios: [Ventajas clave]
   - Requisitos: [Qué se necesita]

### Limitaciones y Restricciones
- Limitaciones Técnicas: [Lista]
- Restricciones de Escala: [Descripción]
- No Recomendado Para: [Lista de escenarios]
```

#### "¿Cómo se implementa?"

Céntrate en los aspectos prácticos de adoptar la solución.

**Elementos requeridos**:
- Describe el proceso básico de configuración
- Documenta métodos de integración
- Lista requisitos de recursos
- Estima cronograma de implementación
- Describe necesidades de mantenimiento

**Formato de ejemplo**:
```markdown
### Guía de Implementación
1. Proceso de Configuración:
   - Prerrequisitos: [Lista]
   - Pasos Básicos: [Lista numerada]
   - Verificación: [Cómo confirmar el éxito]

2. Métodos de Integración:
   - Opciones Disponibles: [Lista de métodos]
   - Enfoque Recomendado: [Mejor práctica]
   - Desafíos de Integración: [Problemas comunes]

3. Requisitos de Recursos:
   - Recursos Técnicos: [Lista]
   - Recursos Humanos: [Habilidades necesarias]
   - Inversión de Tiempo: [Estimaciones]
```

#### "¿Qué lo hace único?"

Céntrate en la diferenciación y posición en el mercado.

**Elementos requeridos**:
- Identifica diferenciadores clave
- Analiza ventajas competitivas
- Evalúa posición en el mercado
- Evalúa nivel de innovación
- Considera potencial futuro

#### "¿Cuál es la estructura de precios y evaluación?"

Céntrate en analizar los costos y evaluar la solución de manera integral.

**Elementos requeridos**:
- Analiza la estructura de precios y licenciamiento
- Documenta los costos asociados
- Examina el valor comercial

**Formato de ejemplo**:
```markdown
### Modelo de Precios
1. Estructura de Licenciamiento:
   - Tipos de Licencias: [Lista de opciones]
   - Modelo de Precios: [Descripción]
   - Términos y Condiciones: [Puntos clave]

2. Desglose de Costos:
   - Costos Base: [Detallar]
   - Costos Adicionales: [Lista]
   - Costos Ocultos: [Consideraciones]

3. Costo Total de Propiedad:
   - Costos Directos: [Lista]
   - Costos Indirectos: [Lista]
   - ROI Estimado: [Cálculo]
```

### Paso 3: Matriz de Evaluación

Completa la matriz de evaluación, puntuando cada dimensión de 1 a 5.

| Dimensión | Puntuación (1-5) | Evidencia | Notas |
|-----------|------------------|-----------|-------|
| **Capacidad Técnica** |  |  |  |
| Diseño de Arquitectura |  |  |  |
| Escalabilidad |  |  |  |
| Confiabilidad |  |  |  |
| Rendimiento |  |  |  |
| **Integración y Desarrollo** |  |  |  |
| Complejidad de Configuración |  |  |  |
| Calidad de Documentación |  |  |  |
| Curva de Aprendizaje |  |  |  |
| Opciones de Personalización |  |  |  |
| **Aspectos Operativos** |  |  |  |
| Necesidades de Mantenimiento |  |  |  |
| Capacidad de Monitoreo |  |  |  |
| Requisitos de Recursos |  |  |  |
| Eficiencia de Costos |  |  |  |
| **Valor Comercial** |  |  |  |
| Posición en el Mercado |  |  |  |
| Comunidad y Soporte |  |  |  |
| Nivel de Innovación |  |  |  |
| Potencial Futuro |  |  |  |

**Guía de Puntuación**:
- 1: Funcionalidad básica o limitada
- 2: Capacidades en desarrollo
- 3: Implementación competente
- 4: Características avanzadas
- 5: Innovación excepcional

### Paso 4: Documento Final

```markdown
# Análisis de [Nombre de la Solución]

## Clasificación
- Categoría: [Tipo]
- Nivel de Implementación: [Nivel]
- Usuarios Principales: [Público Objetivo]

## Análisis Principal
[Incluir hallazgos de preguntas fundamentales]

## Evaluación
[Incluir matriz completada]

## Resumen
- Fortalezas Clave:
- Limitaciones Notables:
- Mejor Utilizado Para:
- No Recomendado Para:

## Recursos Adicionales
[Incluir enlaces relevantes]
```

## Mejores Prácticas

### Sé Objetivo
- Respalda las afirmaciones con evidencia
- Reconoce tanto fortalezas como limitaciones
- Utiliza ejemplos específicos

### Sé Minucioso
- Completa todas las secciones de ser posible
- Proporciona ejemplos concretos

### Sé Claro
- Utiliza lenguaje simple
- Explica términos técnicos

### Sé Práctico
- Céntrate en la aplicación del mundo real
- Incluye ideas accionables
- Considera desafíos de implementación

## Errores Comunes a Evitar

### Análisis Superficial
- Evita simplemente repetir materiales de marketing
- Profundiza en las capacidades reales
- Prueba las afirmaciones cuando sea posible

### Evaluación Sesgada
- No sobrevender fortalezas
- No minimizar limitaciones
- Considerar diferentes perspectivas

### Información Incompleta
- Señala cuando falta información
- Explica el impacto de las brechas
- Sugiere áreas para investigación adicional

## Proceso de Revisión

Antes de enviar tu análisis:
- Verifica que todas las secciones estén completas
- Comprueba que la evidencia respalde las puntuaciones
- Valida la precisión técnica
- Revisa la claridad y consistencia
- Incluye todos los recursos relevantes

## Conclusión

Este marco asegura un análisis consistente de soluciones basadas en agentes. Síguelo para crear perspectivas valiosas para nuestra comunidad. Recuerda que el objetivo es ayudar a otros a comprender no solo qué hace una solución, sino cuándo y cómo usarla efectivamente.
"""

    number_of_queries: int = 3
    tavily_topic: str = "general"
    tavily_days: Optional[int] = 7

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()
