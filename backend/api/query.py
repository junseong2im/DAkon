"""
자연어 질의 파싱 API
─────────────────────
프론트의 프롬프트 입력 → agi_core NL Parser → 구조화된 JSON 반환
LLM Key 있으면 GPT 파싱, 없으면 로컬 폴백 (200+ 종목 매핑)
"""
from fastapi import APIRouter, Header
from pydantic import BaseModel
from typing import Optional
import asyncio

from agi_core.parser.nl_parser import parse_query_safe, parse_query_fallback

router = APIRouter()


class QueryRequest(BaseModel):
    prompt: str


@router.post("/query")
async def query(
    req: QueryRequest,
    x_llm_key: Optional[str] = Header(None),
):
    """
    자연어 질의를 파싱하여 종목/기간/차트/지표 정보를 반환합니다.

    - X-LLM-Key 헤더가 있으면: LLM(GPT-4o)으로 파싱 (무제한 종목)
    - 없으면: 로컬 규칙 기반 폴백 (200+ 매핑 + 동적 추출)
    """
    result = await parse_query_safe(
        user_input=req.prompt,
        api_key=x_llm_key,
    )

    return {
        "status": "success",
        "data": result.to_dict(),
    }