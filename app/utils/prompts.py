# Planning prompts
REPORT_PLANNER_QUERY_WRITER = """Eres un escritor técnico experto, planificando un documento integral.

El documento se centrará en: {topic}

La estructura del documento debe seguir:
{report_organization}

Genera {number_of_queries} consultas de búsqueda que ayudarán a recopilar información completa para planificar las secciones del documento.

Cada consulta debe:
1. Ser específica al tema
2. Ayudar a cumplir con los requisitos de estructura del documento
3. Dirigirse a fuentes autorizadas
4. Incluir términos técnicos cuando sea apropiado

La consulta debe ser lo suficientemente específica para encontrar fuentes relevantes de alta calidad mientras cubre la amplitud necesaria para la estructura del documento.

IMPORTANTE: Todo el contenido debe estar en ESPAÑOL."""

REPORT_PLANNER_INSTRUCTIONS = """Eres un escritor técnico experto creando un esquema de documento.

Tema: {topic}

Organización del Documento: 
{report_organization}

Utiliza este contexto para informar la planificación de secciones:
{context}

Para cada sección, proporciona:
1. Nombre - Título claro de la sección
2. Descripción - Resumen de temas cubiertos
3. Investigación - Si se necesita investigación web (verdadero/falso)
4. Contenido - Dejar en blanco por ahora

Considera qué secciones requieren investigación web. Por ejemplo, la introducción y conclusión no requerirán investigación porque sintetizarán información de otras partes del documento.

IMPORTANTE: Todo el contenido debe estar en ESPAÑOL."""

# Research prompts
RESEARCH_QUERY_WRITER = """Your goal is to generate targeted web search queries that will gather comprehensive information for writing a technical report section.

Topic for this section:
{section_topic}

When generating {number_of_queries} search queries, ensure they:
1. Cover different aspects of the topic (e.g., core features, real-world applications, technical architecture)
2. Include specific technical terms related to the topic
3. Target recent information by including year markers where relevant (e.g., "2024")
4. Look for comparisons or differentiators from similar technologies/approaches
5. Search for both official documentation and practical implementation examples

Your queries should be:
- Specific enough to avoid generic results
- Technical enough to capture detailed implementation information
- Diverse enough to cover all aspects of the section plan
- Focused on authoritative sources (documentation, technical blogs, academic papers)"""

# Writing prompts
# SECTION_WRITER = """Write a section for a technical report.
#
# Section Topic: {section_topic}
# Section Description: {section_description}
#
# Use these guidelines:
# 1. Be technically precise
# 2. Include specific examples
# 3. Cite sources appropriately
# 4. Use clear structure
# 5. Focus on key insights
#
# Available source material:
# {context}"""

SECTION_WRITER = """Eres un escritor técnico experto elaborando una sección de un documento técnico.

Tema para esta sección:
{section_topic}

Pautas para escribir:

1. Precisión Técnica:
- Incluir números de versión específicos
- Referenciar métricas/comparativas concretas
- Citar documentación oficial
- Usar terminología técnica con precisión

2. Extensión y Estilo:
- Sin lenguaje de marketing
- Enfoque técnico
- Escribir en lenguaje claro y simple
- Comenzar con tu insight más importante en **negrita**

3. Estructura:
- Usar ## para título de sección (formato Markdown)
- Asegurar indentación y espaciado apropiado
- Terminar con ### Fuentes que referencia el material fuente siguiente formateado como:
  * Listar cada fuente con título, fecha y URL
  * Formato: `- Título : URL`

4. Enfoque de Escritura:
- Incluir al menos un ejemplo específico o caso de estudio
- Usar detalles concretos en lugar de declaraciones generales
- Hacer que cada palabra cuente
- Sin preámbulos antes de crear el contenido de la sección
- Enfocarse en tu punto más importante

5. Material fuente para ayudar a escribir la sección:
{context}

6. Verificaciones de Calidad:
- Uso cuidadoso de UN SOLO elemento estructural (tabla o lista) y solo si ayuda a clarificar tu punto
- Un ejemplo específico / caso de estudio
- Comienza con insight en negrita
- Sin preámbulos antes de crear el contenido de la sección
- Fuentes citadas al final

IMPORTANTE: Todo el contenido debe estar en ESPAÑOL."""


FINAL_SECTION_WRITER="""You are an expert technical writer crafting a section that synthesizes information from the rest of the report.

Section to write: 
{section_topic}

Available report content:
{context}

1. Section-Specific Approach:

For Introduction:
- Use # for report title (Markdown format)
- Write in simple and clear language
- Focus on the core motivation for the report in 1-2 paragraphs
- Use a clear narrative arc to introduce the report
- Include NO structural elements (no lists or tables)
- No sources section needed

For Conclusion/Summary:
- Use ## for section title (Markdown format)
- For comparative reports:
    * Must include a focused comparison table using Markdown table syntax
    * Table should distill insights from the report
    * Keep table entries clear and concise
- For non-comparative reports: 
    * Only use ONE structural element IF it helps distill the points made in the report:
    * Either a focused table comparing items present in the report (using Markdown table syntax)
    * Or a short list using proper Markdown list syntax:
      - Use `*` or `-` for unordered lists
      - Use `1.` for ordered lists
      - Ensure proper indentation and spacing
- End with specific next steps or implications
- No sources section needed

3. Writing Approach:
- Use concrete details over general statements
- Make every word count
- Focus on your single most important point

4. Quality Checks:

- For conclusion:, ## for section title, only ONE structural element at most, no sources section
- Markdown format
- Do not include word count or any preamble in your response"""

FINAL_REPORT_FORMAT = """
Eres un escritor técnico experto encargado de compilar un documento integral, profesional y estructurado sobre una herramienta o agente de IA. El documento debe seguir estrictamente las pautas y secciones a continuación.

## Estructura del Documento y Pautas:

### **Secciones Base (Obligatorias para Todos los Agentes):**
{report_organization}

### **Pautas Específicas para Diferentes Tipos de Agentes:**
- Para **Frameworks (ej., LangChain, Haystack, Rasa):**
    - Instalación detallada y dependencias (versiones, bibliotecas, entornos recomendados)
    - Explicación de arquitectura interna (ej., cadenas, memorias, herramientas)
    - Fragmentos de código reproducibles para ejecutar un agente básico
    - Pasos para integración con LLMs o servicios externos (ej., OpenAI, Llama2)

- Para **Plataformas Low-Code/No-Code (ej., Zapier con IA, Bubble):**
    - Instrucciones de incorporación a la plataforma (crear cuentas, activar plugins)
    - Flujos de trabajo visuales con diagramas o capturas de pantalla
    - Limitaciones del entorno visual (qué se puede y no se puede hacer sin programar)
    - Un ejemplo práctico completo de un flujo de trabajo visual

- Para **Productos con Agentes Internos (SaaS):**
    - Planes de suscripción e incorporación (ej., Gratuito, Pro)
    - Opciones de configuración para IA interna (ej., prompts o parámetros del modelo)
    - Prueba de funcionalidades clave (ej., chatbots internos, análisis automatizado)
    - Evaluación de usabilidad y UX (para usuarios no técnicos)
    - Modelo de precios y costos asociados

### **Estándares de Escritura:**
- **Claridad y Concisión:** Evitar jerga; usar explicaciones claras y simples
- **Formato Markdown:** Usar encabezados, listas y texto en negrita para mejor legibilidad
- **Ejemplos Reales:** Incluir ejemplos reproducibles, no solo conceptos teóricos
- **Enlaces Funcionales:** Verificar que todos los enlaces funcionen
- **Actualizaciones Periódicas:** Asegurar que la documentación se mantenga actualizada si la herramienta o proceso cambia

### Contexto Proporcionado:
{all_sections}

Ahora, usando las secciones y el contexto proporcionado, compila el documento final. Asegúrate de que el documento se adhiera a la estructura y estándares de calidad descritos anteriormente, con encabezados claros y un tono profesional.

IMPORTANTE: Todo el contenido debe estar en ESPAÑOL."""