"""
AGI 금융 대시보드 - FastAPI 백엔드 엔트리포인트
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import query, market, ws

app = FastAPI(
    title="AGI Finance Dashboard API",
    description="실시간 금융 데이터 및 AGI 분석 API",
    version="1.0.0",
)

# CORS 설정 - 프론트엔드 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(query.router, prefix="/api/v1", tags=["query"])
app.include_router(market.router, prefix="/api/v1", tags=["market"])
app.include_router(ws.router, tags=["websocket"])


@app.get("/")
async def root():
    return {
        "service": "AGI Finance Dashboard API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
