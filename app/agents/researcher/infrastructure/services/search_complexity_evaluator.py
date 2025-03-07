import logging

logger = logging.getLogger(__name__)

class SearchComplexityEvaluator:
    def __init__(self, language_model):
        self.language_model = language_model

    async def evaluate(self, query: str, context: str = "General context for search queries") -> float:
        """Evalúa la complejidad de la búsqueda basada en el query y contexto"""
        try:
            evaluation_prompt = f"""
            Evalúa la complejidad y necesidad de información actualizada para esta búsqueda:
            Query: {query}
            Contexto: {context}

            Responde con un número entre 0 y 1, donde:
            - 0-0.5: Consulta simple o información general
            - 0.6-1.0: Consulta compleja o necesita información actualizada
            """

            response = await self.language_model.generate_content(
                evaluation_prompt,
                {'temperature': 0.1}  # Baja temperatura para respuestas más consistentes
            )

            logger.debug(f"Response for query '{query}': {response}")

            try:
                score = float(response.strip())
                score = min(max(score, 0.0), 1.0)  # Asegurar que esté entre 0 y 1

                if score <= 0.5:
                    logger.info(f"Query '{query}' evaluated as simple with score {score}.")
                else:
                    logger.info(f"Query '{query}' evaluated as complex with score {score}.")

                return score

            except ValueError:
                logger.warning(f"Failed to convert response to float for query '{query}'. Using default score 0.5.")
                return 0.5  # Valor por defecto si no se puede convertir

        except Exception as e:
            logger.error(f"Error evaluating search complexity for query '{query}': {str(e)}")
            return 0.5  # Valor por defecto en caso de error 