from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.graph.report_graph import report_graph
from app.utils.state import ReportState

app = FastAPI()



class ReportRequest(BaseModel):
    topic: str


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "version": "1.0.0",
        "langsmith_enabled": True
    }


@app.post("/generate_report")
async def generate_report(request: dict):
    topic = request.get("topic", "")
    if not topic:
        raise HTTPException(status_code=400, detail="The 'topic' field is required.")

    state = ReportState(topic=topic)
    build = report_graph.compile()
    result = await build.ainvoke(state)  # Cambiar a invoke si el grafo no es asíncrono
    return {"report": result}


if __name__ == "__main__":
    import uvicorn

    # Ejecuta la aplicación
    uvicorn.run(app, host="0.0.0.0", port=8098, workers=2)
