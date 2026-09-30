from fastapi import FastAPI

from app.routers.designs import router as designs_router

app = FastAPI(
    title="UXFlow Agent API",
    description="한국어로 서비스 화면 계획, UI 추천, UX 검수를 확인하는 멀티 에이전트 API입니다.",
    version="0.1.0",
    openapi_tags=[
        {
            "name": "UXFlow Agent API",
            "description": "화면 계획부터 UX 검수와 실행 기록 조회까지 제공합니다.",
        }
    ],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "UXFlow Agent"}


app.include_router(designs_router)
