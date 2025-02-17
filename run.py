import uvicorn
import logging
import sys

if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Ejecutar servidor
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8099,
        reload=True,
        ws_ping_interval=20,
        ws_ping_timeout=20,
        log_level="debug",
        workers=1,  # Importante: usa solo 1 worker para WebSockets
        reload_delay=1.0  # Añadir delay para evitar recargas muy rápidas
    ) 