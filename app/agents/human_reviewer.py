from langgraph.types import interrupt
from typing import Dict, Any
from app.utils.state import ReportState, Section


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

        # Convertir cada sección a un dict serializable
        sections_data = []
        for section in sections:
            section_data = {
                "id": section.id,
                "name": section.name,
                "description": section.description,
                "research": section.research
            }
            sections_data.append(section_data)

        feedback_request = {
            "type": "human_review",
            "message": "¿Apruebas este plan? (Responde 'continuar' o sugiere cambios)",
            "plan": sections_data
        }

        if self.websocket:
            await self.websocket.send_json(feedback_request)

        return interrupt(feedback_request)  # Pausa la ejecución hasta recibir respuesta

    def validate_input(self, state: ReportState) -> ReportState:
        """Actualiza el estado con la decisión según el feedback del usuario.

        Args:
            state: Estado actual que contiene el feedback del usuario.

        Returns:
            El estado actualizado, manteniendo todas las claves originales (incluyendo 'sections').
        """
        feedback = state.get("user_feedback", "").lower()
        if feedback in ["sí", "si", "continuar", "yes"]:
            state["decision"] = "approved"
        else:
            state["decision"] = "rejected"
        return state

