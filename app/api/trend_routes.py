from fastapi import APIRouter, BackgroundTasks
import logging
from typing import Dict, List, Optional
from pydantic import BaseModel

from app.graph.trend_graph import get_trend_graph

router = APIRouter()
logger = logging.getLogger(__name__)

# Almacén en memoria para resultados de análisis
trend_results = {}

class ProductRequest(BaseModel):
    """Modelo para solicitar análisis de tendencias para un producto"""
    product: str

class TrendResponse(BaseModel):
    """Modelo de respuesta para análisis de tendencias"""
    product: str
    status: str
    message: str

async def analyze_product_background(product: str):
    """Ejecuta el análisis de tendencias en segundo plano"""
    try:
        logger.info(f"Iniciando análisis en segundo plano para: {product}")
        
        # Crear estado inicial para análisis de tendencias
        state = {
            "product": product,
            "product_research": [],
            "trend_data": None,
            "opportunity_analysis": None,
            "trend_report": None,
            "top_products": None
        }
        
        # Obtener y ejecutar el grafo
        graph = get_trend_graph()
        chain = graph.compile()
        result = await chain.ainvoke(state)
        
        # Almacenar resultado
        trend_results[product] = {
            "product": product,
            "trend_report": result.get("trend_report", ""),
            "top_products": result.get("top_products", {}),
            "status": "completed"
        }
        
        logger.info(f"Análisis completado para: {product}")
    except Exception as e:
        logger.error(f"Error en análisis: {str(e)}", exc_info=True)
        trend_results[product] = {
            "product": product,
            "status": "error",
            "error": str(e)
        }

@router.post("/analyze", response_model=TrendResponse)
async def analyze_trend(request: ProductRequest, background_tasks: BackgroundTasks):
    """Endpoint para solicitar análisis de tendencias de forma asíncrona"""
    product = request.product
    
    # Iniciar análisis en segundo plano
    background_tasks.add_task(analyze_product_background, product)
    
    return {
        "product": product,
        "status": "processing",
        "message": f"Análisis de tendencias iniciado para: {product}"
    }

@router.get("/result/{product}")
async def get_trend_result(product: str):
    """Obtiene el resultado del análisis de tendencias para un producto"""
    if product not in trend_results:
        return {
            "product": product,
            "status": "not_found",
            "message": "No se ha encontrado el análisis para este producto"
        }
    
    return trend_results[product]

@router.get("/results")
async def get_all_trend_results():
    """Obtiene todos los resultados de análisis de tendencias"""
    return trend_results 