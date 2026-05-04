from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import market, query, websocket, analysis

app = FastAPI(
    title="DeepSR Backend API",
    description="투자 데이터 분석 + AGI 엔진 API",
    version="1.0.0",
)

# CORS — 프론트엔드 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(market.router, prefix="/api/v1")
app.include_router(query.router, prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")
app.include_router(websocket.router)


@app.get("/")
def root():
    return {"service": "DeepSR Backend", "version": "1.0.0", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "healthy"}
