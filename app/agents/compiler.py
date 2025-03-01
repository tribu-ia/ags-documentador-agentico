from typing import List
import asyncio
import re

from langchain_core.messages import SystemMessage, HumanMessage

from app.config.config import get_settings
from app.utils.llms import LLMConfig, LLMManager, LLMType
from app.utils.prompts import FINAL_SECTION_WRITER, FINAL_REPORT_FORMAT
from app.utils.state import ReportState, Section, SectionState
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class ReportCompiler:
    """Class responsible for compiling and formatting the final report."""

    def __init__(self, settings=None, websocket=None):
        """Initialize ReportCompiler with configuration settings.

        Args:
            settings: Optional application settings. If None, will load default settings.
            websocket: Optional websocket for streaming updates.
        """
        self.settings = settings or get_settings()
        self.websocket = websocket
        self.sources = set()  # Nuevo: Para almacenar las fuentes únicas

        # Initialize LLM manager with compilation-specific configuration
        llm_config = LLMConfig(
            temperature=0.7,  # Use deterministic output for compilation
            streaming=True,
            max_tokens=8192  # Larger context for final compilation
        )
        self.llm_manager = LLMManager(llm_config)
        self.primary_llm = self.llm_manager.get_llm(LLMType.GPT_4O_MINI)

    def format_sections(self, sections: List[Section]) -> str:
        """Format a list of sections into a structured string.

        Args:
            sections: List of sections to format

        Returns:
            str: Formatted string representation of sections
        """
        formatted_str = ""
        for idx, section in enumerate(sections, 1):
            formatted_str += f"""
                            {'=' * 60}
                            Section {idx}: {section.name}
                            {'=' * 60}
                            Description:
                            {section.description}
                            Requires Research: 
                            {section.research}
                            
                            Content:
                            {section.content if section.content else '[Not yet written]'}
                            """
        return formatted_str

    async def send_progress(self, message: str, data: dict = None):
        """Send progress updates through websocket"""
        if self.websocket:
            await self.websocket.send_json({
                "type": "compiler_progress",
                "message": message,
                "data": data
            })

    async def gather_completed_sections(self, state: dict) -> dict:
        """Gather and format completed sections for context."""
        try:
            await self.send_progress("Gathering completed sections")
            completed_sections = state.get("completed_sections", [])
            formatted_sections = self.format_sections(completed_sections)

            # Retornar estado completo actualizado
            return {
                **state,  # Mantener estado existente
                "report_sections_from_research": formatted_sections
            }

        except Exception as e:
            await self.send_progress("Error gathering sections", {"error": str(e)})
            raise

    async def write_final_sections(self, state: dict) -> dict:
        """Write final sections using completed research as context."""
        try:
            section = state["section"]
            context = state.get("report_sections_from_research", "")
            
            # Extraer y almacenar URLs del contexto
            urls = re.findall(r'URL: (https?://\S+)', context)
            self.sources.update(urls)
            
            await self.send_progress(f"Writing final section: {section.name}")

            system_instructions = FINAL_SECTION_WRITER.format(
                section_title=section.name,
                section_topic=section.description,
                context=context
            )

            section_content = await self.primary_llm.ainvoke([
                SystemMessage(content=system_instructions),
                HumanMessage(content="Generate a report section based on the provided sources.")
            ])

            section.content = section_content.content
            
            # Solo retornar los campos que necesitamos actualizar
            return {
                "completed_sections": state.get("completed_sections", []) + [section]
            }

        except Exception as e:
            await self.send_progress("Error writing section", {"error": str(e)})
            raise

    def compile_sections(self, state: dict) -> dict:
        """Compile all sections into a unified structure."""
        try:
            logger.debug("Compiling sections")
            sections = state["sections"]  # Acceder como diccionario
            completed_sections = {
                s.name: s.content
                for s in state["completed_sections"]  # Acceder como diccionario
            }

            # Update sections while maintaining order
            for section in sections:
                section.content = completed_sections[section.name]

            # Agregar sección de referencias
            references_section = "\n\nReferences:\n"
            for idx, source in enumerate(sorted(self.sources), 1):
                references_section += f"[{idx}] {source}\n"

            # Join sections
            all_sections = "\n\n".join([s.content for s in sections]) + references_section

            return {"final_report": all_sections}

        except Exception as e:
            logger.error(f"Error compiling sections: {str(e)}")
            raise

    async def compile_final_report(self, state: dict) -> dict:
        """Generate the final formatted report."""
        try:
            logger.debug("Starting final report compilation")
            await self.send_progress("Compiling final report")

            # First compile all sections
            compiled_sections = self.compile_sections(state)
            all_sections = compiled_sections["final_report"]

            # Asegurarse de que report_organization tenga un valor por defecto
            report_organization = {
                "introduction": "1. Introducción",
                "body": "2. Desarrollo",
                "conclusion": "3. Conclusión",
                #"references": "4. Referencias"
            }
            
            # Instrucciones más específicas con límite de palabras
            system_instructions = """
            Eres un editor experto encargado de formatear un informe técnico.
            
            Tu tarea es tomar las siguientes secciones y organizarlas en un documento cohesivo,
            manteniendo el contenido esencial de cada sección. El informe final no debe exceder las 32,000 palabras.
            
            Estructura del documento:
            {report_organization}
            
            Contenido de las secciones:
            {all_sections}
            
            Instrucciones específicas:
            0. Todo el contenido debe ser en ESPAÑOL 
            1. Mantén la información más relevante de cada sección
            2. Asegúrate de que los títulos de las secciones sean claros y consistentes
            3. Mejora las transiciones entre secciones
            4. Mantén el formato Markdown existente sin agregar etiquetas de INICIO o FIN Solo el CONTENIDO
            5. Prioriza mantener la información técnica y ejemplos importantes
            6. Asegúrate de que el informe esté completo y bien estructurado
            7. No excedas el límite de 32,000 palabras
            """

            logger.debug("Starting to stream final report")
            content_buffer = []
            
            # Configurar el modelo para manejar respuestas más largas
            async for chunk in self.primary_llm.astream([
                SystemMessage(content=system_instructions.format(
                    report_organization=report_organization,
                    all_sections=all_sections
                )),
                HumanMessage(content="Formatea las secciones del informe en un documento cohesivo y completo, respetando el límite de palabras.")
            ], max_tokens=12000):  # Aumentamos el límite de tokens de salida
                if hasattr(chunk, "content"):
                    content_buffer.append(chunk.content)
                    await self.send_progress("final_report_chunk", {
                        "type": "report_content",
                        "content": chunk.content,
                        "is_complete": False
                    })

            # Combinar todo el contenido del LLM
            llm_content = "".join(content_buffer)

            # Agregar la sección de referencias al final
            references_section = "\n\n## Referencias\n"
            for idx, source in enumerate(sorted(self.sources), 1):
                references_section += f"[{idx}] {source}\n"

            # Combinar el contenido del LLM con las referencias
            final_content = llm_content + references_section

            # Enviar el reporte completo
            await self.send_progress("final_report_complete", {
                "type": "report_content",
                "content": final_content,
                "is_complete": True
            })

            logger.debug("Final report streaming completed")
            return {"final_report": final_content}

        except Exception as e:
            logger.error(f"Error streaming report: {str(e)}")
            await self.send_progress("error", {"error": str(e)})
            raise

    def cleanup(self):
        """Cleanup method to clear LLM caches when done."""
        self.llm_manager.clear_caches()