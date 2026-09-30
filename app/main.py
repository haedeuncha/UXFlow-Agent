from fastapi import FastAPI

from app.routers.designs import router as designs_router

app = FastAPI(title="UXFlow Agent", version="0.1.0")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "UXFlow Agent"}


app.include_router(designs_router)
