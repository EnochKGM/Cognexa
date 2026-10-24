"""Pydantic schemas for the Cognexa API.

These models are the STABLE contract between backend and frontend.  The mock
generator produces exactly this shape, so the future `Gemma4StudyMaterialGenerator`
can replace it without any frontend or results-UI changes.
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------
# Upload
# --------------------------------------------------------------------------
class UploadResponse(BaseModel):
    upload_id: str = Field(..., description="Server-generated id for the stored upload.")
    filename: str = Field(..., description="Original filename, display only.")
    content_type: str
    size_bytes: int
    width: int
    height: int
    stored_format: str = Field(..., description="Actual decoded format, e.g. PNG or JPEG.")


# --------------------------------------------------------------------------
# Mind map
# --------------------------------------------------------------------------
class Position(BaseModel):
    x: float
    y: float


class MindMapNode(BaseModel):
    id: str = Field(..., description="Stable node id, unique within a result.")
    label: str
    node_type: Literal["topic", "subtopic", "concept"]
    parent: Optional[str] = Field(None, description="Parent node id, None for the central topic.")
    position: Position = Field(..., description="Initial canvas position; users may rearrange.")


class MindMapEdge(BaseModel):
    id: str
    source: str = Field(..., description="Source node id.")
    target: str = Field(..., description="Target node id.")
    label: Optional[str] = None


# --------------------------------------------------------------------------
# Study material
# --------------------------------------------------------------------------
class MainTopic(BaseModel):
    id: str
    label: str


class Subtopic(BaseModel):
    id: str
    label: str


class SummarySection(BaseModel):
    title: str
    content: str


class Summary(BaseModel):
    overview: str
    sections: List[SummarySection]


class KeyTerm(BaseModel):
    term: str
    definition: str


class Question(BaseModel):
    id: str
    question: str
    type: Literal["multiple_choice"] = "multiple_choice"
    options: List[str]
    correct_answer: str = Field(..., description="Must exactly match one of `options`.")
    explanation: str


class SourceImage(BaseModel):
    upload_id: str
    filename: str
    content_type: str
    size_bytes: int
    width: int
    height: int
    url: str = Field(..., description="API URL from which the image can be reviewed.")


class StudyMaterial(BaseModel):
    result_id: str = Field(..., description="Server-generated id for this result.")
    is_demo: bool = Field(True, description="True while mock generation is in use.")
    generator: str = Field(..., description="Which service produced this result, e.g. 'mock'.")
    main_topic: MainTopic
    subtopics: List[Subtopic]
    nodes: List[MindMapNode]
    edges: List[MindMapEdge]
    summary: Summary
    key_terms: List[KeyTerm]
    questions: List[Question]
    source_image: SourceImage


# --------------------------------------------------------------------------
# Requests / misc
# --------------------------------------------------------------------------
class GenerateRequest(BaseModel):
    upload_id: str = Field(..., description="upload_id returned by POST /api/upload.")


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str = "cognexa-backend"
    demo_mode: bool = True
    ai_provider: str
    ai_configured: bool = Field(
        False, description="True when AI_PROVIDER=gemma4 and GOOGLE_API_KEY is configured."
    )
    reserved_gemma_model: str = Field(
        "gemma-4-31b-it",
        description="Gemma 4 model id used for generation (Google AI Studio).",
    )
    max_upload_mb: int
