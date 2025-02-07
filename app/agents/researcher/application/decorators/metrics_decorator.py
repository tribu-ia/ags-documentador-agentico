import time
import logging
from functools import wraps

logger = logging.getLogger(__name__)

def track_metrics(func):
    """Decorator to track function metrics"""
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        start_time = time.time()
        try:
            result = await func(self, *args, **kwargs)
            end_time = time.time()
            
            logger.debug(
                f"Function {func.__name__} completed in {end_time - start_time:.2f} seconds"
            )
            
            return result
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            raise
    return wrapper 