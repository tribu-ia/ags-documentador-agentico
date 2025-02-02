import uvicorn
import logging

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8098,
        reload=True,
        ws_ping_interval=20,
        ws_ping_timeout=20,
        log_level="debug",
        workers=1  # Importante: usa solo 1 worker para WebSockets
    ) 