from fastapi import FastAPI

app = FastAPI(
    title="Buckteeth",
    description="AI-powered dental insurance coding agent",
    version="0.1.0",
)


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "0.1.0"}
