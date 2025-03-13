import asyncio
import logging
import re
from typing import Any, Dict

from langgraph.types import interrupt

from app.utils.state import ReportState

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HumanReviewer:
    """Maneja la interacción de revisión humana en la generación del reporte."""

    def __init__(self, websocket=None):
        # No se almacena el websocket en el estado a checkpointear
        self.websocket = websocket

    async def request_review(self, state: ReportState) -> Dict[str, Any]:
        """Pausa el flujo y solicita validación humana del plan de reporte.

        Args:
            state: Estado actual que contiene el plan (secciones).

        Returns:
            Un interrupt con la solicitud de feedback.
        """
        sections = state["sections"]
        topic = state["topic"]

        # Convertir cada sección a un dict serializable
        sections_data = []

        # Crear mensaje de revisión detallado en formato Markdown
        message_markdown = f"""
**Revisión del Plan de Investigación para la Generación del Reporte**

Hola,

A continuación, se presenta el plan de investigación propuesto para generar el reporte. Este plan ha sido diseñado para cubrir de manera efectiva el tema solicitado y asegurar la calidad de la información en el reporte final.

**Tema del Reporte:** {topic}

**Descripción General del Plan de Investigación:**

Se utilizará una estrategia de investigación basada en la búsqueda web exhaustiva utilizando fuentes confiables y relevantes para el tema. El objetivo es recopilar información actualizada y diversa que permita desarrollar cada sección del reporte de forma completa y precisa.

**Secciones Propuestas para el Reporte:**

A continuación, se detallan las secciones propuestas para el reporte. Por favor, revisa cada sección y decide si el plan es adecuado o si deseas sugerir modificaciones.
        if self.websocket:
            await self.websocket.send_json(feedback_request)

        return interrupt(feedback_request)  
"""

        # Agregar detalles de cada sección al mensaje
        for i, section in enumerate(sections, 1):
            research_justification = (
                "Se realizará investigación específica para esta sección para obtener información actualizada y precisa."
                if section.research
                else "No requiere investigación adicional, se utilizará información ya disponible."
            )

            section_data = {
                "id": section.id,
                "name": section.name,
                "description": section.description,
                "research": section.research,
            }
            sections_data.append(section_data)

            message_markdown += f"""
**Sección {i}: {section.name}**
* **Descripción:** {section.description}
* **Justificación de la Investigación:** {research_justification}

---
"""

        # Agregar instrucciones claras para el usuario
        message_markdown += """
**Instrucciones:**

* **Para aprobar el plan:** Responde con **"aprobar"** o **"continuar"**.
* **Para sugerir modificaciones:** Responde especificando las secciones que deseas cambiar y tus sugerencias concretas. Por ejemplo: "Modificar Sección 1: Cambiar el enfoque a [nuevo enfoque]. Añadir una nueva sección sobre [nuevo tema]".

¿Deseas aprobar este plan de investigación o sugerir modificaciones?
"""
        user_feedback = state.get("user_feedback", "")
        review_count = state.get("review_count", 0)

        feedback_request = {
            "type": "human_review",
            "message": message_markdown,
            "plan": sections_data,
        }

        try:
            # Timeout ensures fallback response logic
            return await asyncio.wait_for(interrupt(feedback_request), timeout=30)
        except asyncio.TimeoutError:
            # Use interrupt even for timeout to ensure proper checkpointing
            return interrupt(
                {
                    "user_feedback": user_feedback
                    + f"\nrealimentacion #{review_count + 1}:\n"
                    + "si, me gusta",
                    "review_count": review_count + 1,
                }
            )
        except Exception as e:
            logger.error(f"Human in the Loop Error: {str(e)}", exc_info=True)
            raise

    # Normalize feedback by converting to lowercase and splitting into "words".
    def normalize_text(self, text):
        return re.findall(r"\b\w+\b", text.lower())

    def validate_input(self, state: ReportState) -> ReportState:
        """Actualiza el estado con la decisión según el feedback del usuario.

        Args:
            state: Estado actual que contiene el feedback del usuario.

        Returns:
            El estado actualizado, manteniendo todas las claves originales (incluyendo 'sections').
        """
        # Crear una copia del estado actual para preservar todos los valores
        feedback = state.get("user_feedback", "")

        # Inicializar o incrementar el contador de revisiones
        review_count = state.get("review_count", 0)

        # Lista de términos que indican aprobación (insensible a mayúsculas/minúsculas)
        approval_terms = [
            "sí",
            "si",
            "continuar",
            "yes",
            "aprobar",
            "apruebo",
            "aceptar",
            "acepto",
        ]

        tokens = self.normalize_text(feedback)
        # Verificar si el feedback contiene algún término de aprobación
        if feedback.lower() in approval_terms or any(
            term in tokens for term in approval_terms
        ):
            return {
                "decision": "approved",
                "review_count": review_count,
            }
            # No es necesario conservar el feedback completo si es aprobación
        else:
            # Actualizar el estado manteniendo los valores existentes
            return {
                "decision": "rejected",
                "user_feedback": feedback,
                "review_count": review_count,
            }
