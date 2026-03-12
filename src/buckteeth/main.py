from fastapi import FastAPI

from buckteeth.api.patients import router as patients_router
from buckteeth.api.encounters import router as encounters_router
from buckteeth.api.claims import router as claims_router
from buckteeth.api.coding import router as coding_router
from buckteeth.api.submissions import router as submissions_router

app = FastAPI(
    title="Buckteeth",
    description="AI-powered dental insurance coding agent",
    version="0.1.0",
)

app.include_router(patients_router)
app.include_router(encounters_router)
app.include_router(coding_router)
app.include_router(claims_router)
app.include_router(submissions_router)


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "0.1.0"}
