from typing import List, Dict
import re

from langchain_core.messages import SystemMessage, HumanMessage

from app.config.config import get_settings
from app.utils.llms import LLMConfig, LLMManager, LLMType
from app.utils.state import TrendResearchState, ProductTrend
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TrendAnalysisCompiler:
    """Clase responsable de compilar y analizar datos de tendencias de productos."""

    def __init__(self, settings=None, websocket=None):
        """Inicializa el compilador de análisis de tendencias."""
        self.settings = settings or get_settings()
        self.websocket = websocket
        self.sources = set()

        llm_config = LLMConfig(
            temperature=0.5,
            streaming=True,
            max_tokens=8192
        )
        self.llm_manager = LLMManager(llm_config)
        self.primary_llm = self.llm_manager.get_llm(LLMType.GPT_4O_MINI)

    async def send_progress(self, message: str, data: dict = None):
        """Envía actualizaciones de progreso a través del websocket"""
        if self.websocket:
            await self.websocket.send_json({
                "type": "trend_compiler_progress",
                "message": message,
                "data": data
            })

    def format_trend_data(self, product_trends: List[ProductTrend]) -> str:
        """Formatea datos de tendencias en una estructura legible."""
        formatted_str = ""
        for idx, trend in enumerate(product_trends, 1):
            formatted_str += f"""
            {'=' * 60}
            Producto {idx}: {trend.product}
            {'=' * 60}
            
            Tendencias Actuales:
            {trend.current_trends}
            
            Volumen de Búsqueda:
            {trend.search_volume}
            
            Sentimiento en Redes:
            {trend.social_sentiment}
            
            Competencia:
            {trend.competition}
            
            Estacionalidad:
            {trend.seasonality}
            
            Datos Demográficos:
            {trend.demographics}
            
            Métricas Adicionales:
            {trend.additional_metrics}
            """
            
            # Recopilar URLs como fuentes
            urls = re.findall(r'URL: (https?://\S+)', trend.raw_data)
            self.sources.update(urls)
            
        return formatted_str

    async def gather_trend_data(self, state: dict) -> dict:
        """Recopila datos de tendencias de todos los productos investigados."""
        try:
            await self.send_progress("Recopilando datos de tendencias")
            product_research = state.get("product_research", [])
            formatted_data = self.format_trend_data(product_research)

            return {
                **state,
                "trend_data": formatted_data
            }
        except Exception as e:
            await self.send_progress("Error gathering trend data", {"error": str(e)})
            raise

    async def analyze_opportunities(self, state: dict) -> dict:
        """Analiza las oportunidades de mercado para cada producto."""
        try:
            trend_data = state.get("trend_data", "")
            
            system_instructions = """
            Eres un analista experto en marketing digital y tendencias de mercado.
            
            Analiza los datos de tendencias recopilados para los productos y evalúa:
            1. Volumen de búsqueda y crecimiento de tendencias
            2. Sentimiento positivo en redes sociales
            3. Nivel de competencia y saturación
            4. Potencial de conversión y ventas
            5. Estacionalidad y momentos óptimos
            6. Alineación con demografías objetivo
            7. Oportunidades específicas para marketing digital
            
            Para cada producto, asigna una puntuación de oportunidad (1-100) 
            y justifica tu evaluación con los datos proporcionados.
            """

            await self.send_progress("Analizando oportunidades de mercado")
            
            analysis_result = await self.primary_llm.ainvoke([
                SystemMessage(content=system_instructions),
                HumanMessage(content=f"Analiza los siguientes datos de tendencias:\n{trend_data}")
            ])

            return {
                "opportunity_analysis": analysis_result.content,
                "trend_data": trend_data
            }

        except Exception as e:
            await self.send_progress("Error analyzing opportunities", {"error": str(e)})
            raise

    async def compile_trend_report(self, state: dict) -> dict:
        """Compila el reporte final de análisis de tendencias."""
        try:
            analysis = state.get("opportunity_analysis", "")
            trend_data = state.get("trend_data", "")

            system_instructions = """
            Eres un consultor experto en marketing digital que debe crear un informe ejecutivo de tendencias.
            
            Genera un reporte detallado de análisis de tendencias que incluya:
            1. Resumen ejecutivo de las mejores oportunidades identificadas
            2. Ranking de productos según su potencial de mercado (con puntuaciones 1-100)
            3. Análisis de tendencias por producto con métricas clave
            4. Recomendaciones específicas para marketing digital en Meta
            5. Justificación de por qué ciertos productos tienen mejor potencial
            6. Calendario sugerido de campañas basado en estacionalidad
            
            El reporte debe ser claro, estructurado y orientado a la acción.
            """

            await self.send_progress("Compilando reporte final de tendencias")
            
            content_buffer = []
            async for chunk in self.primary_llm.astream([
                SystemMessage(content=system_instructions),
                HumanMessage(content=f"Datos de análisis:\n{analysis}\n\nDatos de tendencias:\n{trend_data}")
            ], max_tokens=12000):
                if hasattr(chunk, "content"):
                    content_buffer.append(chunk.content)
                    await self.send_progress("trend_report_chunk", {
                        "type": "trend_content",
                        "content": chunk.content,
                        "is_complete": False
                    })

            # Combinar todo el contenido del LLM
            llm_content = "".join(content_buffer)

            # Agregar la sección de referencias
            references_section = "\n\n## Fuentes de Datos\n"
            for idx, source in enumerate(sorted(self.sources), 1):
                references_section += f"[{idx}] {source}\n"

            # Combinar el contenido del LLM con las referencias
            final_content = llm_content + references_section

            # Enviar el reporte completo
            await self.send_progress("trend_report_complete", {
                "type": "trend_content",
                "content": final_content,
                "is_complete": True
            })

            # Extraer los productos con mejores oportunidades
            top_products = self.extract_product_opportunities(final_content)

            return {
                "trend_report": final_content,
                "top_products": top_products
            }

        except Exception as e:
            await self.send_progress("Error compiling trend report", {"error": str(e)})
            raise

    def extract_product_opportunities(self, report_content: str) -> dict:
        """Extrae los productos con mejores oportunidades del reporte."""
        try:
            # Implementación básica para extraer productos y puntuaciones
            # En una implementación real, esto sería más sofisticado
            products = {}
            # Buscar patrones como "Producto X: 85/100" o similar
            patterns = [
                r'(\w+):\s*(\d+)\/100',
                r'(\w+)\s*-\s*Puntuación:\s*(\d+)',
                r'(\w+).*?(\d+)\s*puntos'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, report_content)
                for match in matches:
                    product, score = match
                    products[product.strip()] = int(score)
            
            # Si no se encontraron productos, devolver un diccionario vacío
            return products
        except Exception as e:
            logger.error(f"Error extracting product opportunities: {str(e)}")
            return {} 