"""Pydantic-схемы запросов и ответов."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class TextAnalysisRequest(BaseModel):
    text: str = Field(..., min_length=10, description="Текст конкурента для анализа")


class ParseDemoRequest(BaseModel):
    url: str = Field(..., min_length=3, description="URL страницы конкурента")


class CompetitorAnalysis(BaseModel):
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    unique_offers: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    summary: str = ""
    conclusion: str = ""
    design_score: int = Field(0, ge=0, le=10)
    animation_potential: int = Field(0, ge=0, le=10)
    animation_notes: str = ""


class ImageAnalysis(BaseModel):
    description: str = ""
    marketing_insights: List[str] = Field(default_factory=list)
    visual_style_score: int = Field(0, ge=0, le=10)
    visual_style_analysis: str = ""
    recommendations: List[str] = Field(default_factory=list)
    design_score: int = Field(0, ge=0, le=10)
    animation_potential: int = Field(0, ge=0, le=10)
    animation_notes: str = ""


class ParsedContent(BaseModel):
    url: str
    title: Optional[str] = None
    h1: Optional[str] = None
    first_paragraph: Optional[str] = None
    screenshot: Optional[str] = None
    analysis: Optional[CompetitorAnalysis] = None
    error: Optional[str] = None


class TextAnalysisResponse(BaseModel):
    success: bool
    analysis: Optional[CompetitorAnalysis] = None
    error: Optional[str] = None


class ImageAnalysisResponse(BaseModel):
    success: bool
    analysis: Optional[ImageAnalysis] = None
    error: Optional[str] = None


class ParseDemoResponse(BaseModel):
    success: bool
    data: Optional[ParsedContent] = None
    error: Optional[str] = None


class HistoryItem(BaseModel):
    id: str
    timestamp: datetime
    request_type: str
    request_summary: str
    response_summary: str


class HistoryResponse(BaseModel):
    items: List[HistoryItem]
    total: int


class MonitorRunRequest(BaseModel):
    urls: Optional[List[str]] = None
    niche: Optional[str] = None


class MonitorChangeItem(BaseModel):
    field: str
    before: str = ""
    after: str = ""


class MonitorChange(BaseModel):
    id: str
    url: str
    changed_at: str
    items: List[MonitorChangeItem] = Field(default_factory=list)


class MonitorSite(BaseModel):
    url: str
    title: Optional[str] = None
    h1: Optional[str] = None
    analyzed_at: Optional[str] = None
    conclusion: str = ""
    design_score: Optional[int] = None
    animation_potential: Optional[int] = None
    animation_notes: str = ""
    summary: str = ""
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    unique_offers: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    error: Optional[str] = None


class MonitorStateResponse(BaseModel):
    niche: str
    urls: List[str] = Field(default_factory=list)
    defaults: List[str] = Field(default_factory=list)
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None
    sites: List[MonitorSite] = Field(default_factory=list)
    changes: List[MonitorChange] = Field(default_factory=list)
