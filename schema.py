"""파이프라인 단계 간 주고받는 데이터 구조(pydantic).

흐름: Candidate(수집) → NewsItem(요약·해석) → FactCheck(검증) → Issue(발행)
"""
from __future__ import annotations
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class Candidate(BaseModel):
    """취재 기자(collect)가 발굴한 후보 뉴스 1건."""
    region: str
    category: str = Field(description="config.CATEGORIES 의 키 중 하나")
    headline: str
    summary: str
    effective_date: str = Field(default="", description="시행/개정일 등 핵심 날짜")
    source_name: str = Field(default="", description="출처 기관/매체 짧은 이름")
    source_urls: List[str] = Field(default_factory=list)


class CandidateList(BaseModel):
    items: List[Candidate]


class Draft(BaseModel):
    """법률 해설가(draft)가 쓴 요약 + 쉬운 해석."""
    head: str = Field(description="카드 제목")
    desc: str = Field(description="2~3문장 요약")
    interp: str = Field(description="'쉬운 해석' — 핵심어는 <b>…</b>로 강조")
    read_min: int = 3


class FactVerdict(BaseModel):
    """팩트체커 1인의 판정."""
    verdict: Literal["PASS", "HOLD"]
    confidence: float = Field(ge=0.0, le=1.0)
    sources_count: int = 0
    issues: List[str] = Field(default_factory=list, description="불일치/의심 항목")


class NewsItem(BaseModel):
    """렌더링·발행에 쓰이는 최종 뉴스 카드."""
    region: str
    category: str
    head: str
    desc: str
    interp: str
    source: str = ""
    read: int = 3
    url: str = "#"
    source_urls: List[str] = Field(default_factory=list)
    hot: bool = False
    hotflag: Optional[str] = None
    # 어려운 용어 풀이 — desc 안 단어에 점선 밑줄 → 탭하면 설명. [{"term","explain"}, ...]
    terms: List[dict] = Field(default_factory=list)
    # 검증 결과(감사 로그)
    verdict: Literal["PASS", "HOLD", "PENDING"] = "PENDING"
    check_a: Optional[FactVerdict] = None
    check_b: Optional[FactVerdict] = None
    check_notes: List[str] = Field(default_factory=list)


class Issue(BaseModel):
    """하루치 브리핑 = 한 '호'."""
    number: int
    date: str                 # YYYY-MM-DD
    published: List[NewsItem] = Field(default_factory=list)
    held: List[NewsItem] = Field(default_factory=list)  # 사람 검토 대기

    def region_counts(self) -> dict:
        c: dict = {}
        for it in self.published:
            c[it.region] = c.get(it.region, 0) + 1
        return c
