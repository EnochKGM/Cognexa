"""Gemma 4 study-material generator — Google AI Studio (google-genai).

Replaces the previous mock-only placeholder. The model is **always**
`gemma-4-31b-it`; no other model or provider is used, and failures are surfaced
honestly instead of silently falling back.

Flow:
    stored upload -> validated image bytes -> google-genai generate_content
    -> JSON plan -> strict normalisation -> the existing StudyMaterial contract

The API key is read from `GOOGLE_API_KEY` on the backend only. It is never
logged, returned, or sent to the frontend.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import re
import time
import uuid
from typing import Any, List, Optional

from pydantic import BaseModel, ValidationError

from ..config import get_settings
from ..errors import AiGenerationError, ApiError, FileNotFoundError_, ProviderNotAvailableError
from ..schemas import (
    KeyTerm,
    MainTopic,
    MindMapEdge,
    MindMapNode,
    Position,
    Question,
    SourceImage,
    StudyMaterial,
    Subtopic,
    Summary,
    SummarySection,
)
from ..storage import state
from .base import StudyMaterialGenerator

logger = logging.getLogger("mindmap_ai.gemma")

TOPIC_RADIUS = 340.0
CONCEPT_RADIUS = 680.0
MAX_MODEL_TEXT_CHARS = 20_000

PROMPT = """You are an expert study assistant. Analyse the attached textbook page image and
build revision material for a student.

Return ONLY a single JSON object — no markdown fences, no commentary — with exactly this shape:
{
  "main_topic": "short title of the page's main topic",
  "description": "2-4 sentence overview of the topic, based only on the page",
  "summary_sections": [{"title": "short heading", "content": "2-4 sentences"}],
  "key_terms": [{"term": "term", "definition": "one-sentence definition"}],
  "subtopics": [{"label": "subtopic name", "concepts": ["concept 1", "concept 2"]}],
  "questions": [
    {
      "question": "...",
      "options": ["option A", "option B", "option C", "option D"],
      "correct_index": 0,
      "explanation": "why this answer is correct"
    }
  ]
}

Rules:
- Base everything strictly on the page. Do not invent facts that are not supported by it.
- Provide 4-6 subtopics, each with 2-4 short concept labels.
- Provide 4-6 summary sections, 6-10 key terms, and exactly 5 multiple-choice questions.
- Every question must have exactly 4 distinct options, exactly one correct answer, and
  "correct_index" must be the 0-based index of the correct option.
- Keep all text concise and classroom-appropriate.
- If the image is unreadable or is not a textbook/study page, return exactly:
  {"error": "brief reason describing why the page cannot be processed"}
"""


# ---------------------------------------------------------------------------
# Model-output models (internal; normalized into schemas.StudyMaterial)
# ---------------------------------------------------------------------------
class AISection(BaseModel):
    title: str
    content: str


class AITerm(BaseModel):
    term: str
    definition: str


class AISubtopic(BaseModel):
    label: str
    concepts: List[str] = []


class AIQuestion(BaseModel):
    question: str
    options: List[str]
    correct_index: Optional[int] = None
    correct_answer: Optional[str] = None
    explanation: str


class AIPlan(BaseModel):
    main_topic: str
    description: str = ""
    summary_sections: List[AISection] = []
    key_terms: List[AITerm] = []
    subtopics: List[AISubtopic] = []
    questions: List[AIQuestion] = []


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def extract_json_object(text: Optional[str]) -> dict:
    """Extract a JSON object from the model output (tolerates code fences)."""
    if not text or not text.strip():
        raise AiGenerationError("Gemma 4 returned an empty response. Please try again.")

    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise AiGenerationError(
            "Gemma 4 did not return a JSON study plan. Please retry the generation."
        )

    try:
        data = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError:
        raise AiGenerationError(
            "Gemma 4 returned malformed JSON, so no result was produced. Please retry."
        )

    if not isinstance(data, dict):
        raise AiGenerationError("Gemma 4 returned an unexpected response shape. Please retry.")
    return data


def normalize_plan(data: dict) -> AIPlan:
    """Validate and normalize the model's JSON into a strict AIPlan.

    Raises AiGenerationError with a clear message when the model output cannot
    satisfy the application contract. Never fabricates missing content.
    """
    if data.get("error"):
        raise ApiError(
            422,
            "image_unreadable",
            f"Gemma 4 could not read this page: {_clean(str(data['error']))[:300]}",
        )

    try:
        plan = AIPlan.model_validate(data)
    except ValidationError:
        raise AiGenerationError(
            "Gemma 4 returned a study plan with missing or invalid fields. Please retry."
        )

    plan.main_topic = _clean(plan.main_topic)
    plan.description = _clean(plan.description)
    if not plan.main_topic:
        raise AiGenerationError("Gemma 4 did not identify a main topic for this page.")

    if not plan.description:
        raise AiGenerationError("Gemma 4 did not provide a summary for this page.")

    # Summary sections
    sections = [s for s in plan.summary_sections if _clean(s.title) and _clean(s.content)]
    if not sections:
        raise AiGenerationError("Gemma 4 did not return any summary sections.")
    plan.summary_sections = sections[:8]

    # Key terms
    terms = [t for t in plan.key_terms if _clean(t.term) and _clean(t.definition)]
    if len(terms) < 4:
        raise AiGenerationError("Gemma 4 returned too few key terms to build the glossary.")
    plan.key_terms = terms[:12]

    # Subtopics + concepts
    subtopics: List[AISubtopic] = []
    for sub in plan.subtopics:
        label = _clean(sub.label)
        concepts = [_clean(c) for c in sub.concepts if _clean(c)]
        if label and concepts:
            subtopics.append(AISubtopic(label=label, concepts=concepts[:5]))
    if len(subtopics) < 3:
        raise AiGenerationError(
            "Gemma 4 returned too few subtopics to build a mind map. Please retry."
        )
    plan.subtopics = subtopics[:8]

    # Questions: exactly 5, four distinct options, resolvable correct answer.
    questions: List[AIQuestion] = []
    for q in plan.questions:
        options = [_clean(o) for o in q.options if _clean(o)]
        if len(options) != 4 or len(set(options)) != 4:
            continue
        explanation = _clean(q.explanation)
        question_text = _clean(q.question)
        if not question_text or not explanation:
            continue

        correct_index: Optional[int] = None
        if isinstance(q.correct_index, int) and 0 <= q.correct_index < len(options):
            correct_index = q.correct_index
        elif q.correct_answer:
            answer = _clean(q.correct_answer)
            for index, option in enumerate(options):
                if option.casefold() == answer.casefold():
                    correct_index = index
                    break
        if correct_index is None:
            continue

        questions.append(
            AIQuestion(
                question=question_text,
                options=options,
                correct_index=correct_index,
                explanation=explanation,
            )
        )

    if len(questions) < 5:
        raise AiGenerationError(
            "Gemma 4 returned fewer than five valid multiple-choice questions. Please retry."
        )
    plan.questions = questions[:5]

    return plan


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:40] or "topic"


def build_study_material(
    plan: AIPlan,
    source_image: SourceImage,
    result_id: Optional[str] = None,
    generator: str = "gemma4",
) -> StudyMaterial:
    """Build the exact StudyMaterial contract the frontend already expects."""
    slug = _slugify(plan.main_topic)
    topic_id = f"{slug}-topic"

    nodes: List[MindMapNode] = [
        MindMapNode(
            id=topic_id,
            label=plan.main_topic,
            node_type="topic",
            parent=None,
            position=Position(x=0.0, y=0.0),
        )
    ]
    edges: List[MindMapEdge] = []
    subtopics: List[Subtopic] = []

    subtopic_count = max(len(plan.subtopics), 1)
    for i, sub in enumerate(plan.subtopics):
        angle = -math.pi / 2 + (2 * math.pi * i / subtopic_count)
        sub_id = f"{slug}-sub-{i}"
        subtopics.append(Subtopic(id=sub_id, label=sub.label))
        nodes.append(
            MindMapNode(
                id=sub_id,
                label=sub.label,
                node_type="subtopic",
                parent=topic_id,
                position=Position(
                    x=round(math.cos(angle) * TOPIC_RADIUS, 1),
                    y=round(math.sin(angle) * TOPIC_RADIUS, 1),
                ),
            )
        )
        edges.append(
            MindMapEdge(
                id=f"e-{topic_id}-{sub_id}",
                source=topic_id,
                target=sub_id,
                label="includes",
            )
        )

        concept_count = max(len(sub.concepts), 1)
        spread = math.radians(30)
        for j, concept in enumerate(sub.concepts):
            c_angle = angle if concept_count == 1 else angle - spread / 2 + spread * (j / (concept_count - 1))
            c_id = f"{slug}-sub-{i}-c-{j}"
            nodes.append(
                MindMapNode(
                    id=c_id,
                    label=concept,
                    node_type="concept",
                    parent=sub_id,
                    position=Position(
                        x=round(math.cos(c_angle) * CONCEPT_RADIUS, 1),
                        y=round(math.sin(c_angle) * CONCEPT_RADIUS, 1),
                    ),
                )
            )
            edges.append(
                MindMapEdge(id=f"e-{sub_id}-{c_id}", source=sub_id, target=c_id, label=None)
            )

    return StudyMaterial(
        result_id=result_id or uuid.uuid4().hex,
        is_demo=False,
        generator=generator,
        main_topic=MainTopic(id=topic_id, label=plan.main_topic),
        subtopics=subtopics,
        nodes=nodes,
        edges=edges,
        summary=Summary(
            overview=plan.description,
            sections=[SummarySection(title=s.title, content=s.content) for s in plan.summary_sections],
        ),
        key_terms=[KeyTerm(term=t.term, definition=t.definition) for t in plan.key_terms],
        questions=[
            Question(
                id=f"q{index + 1}",
                question=q.question,
                type="multiple_choice",
                options=q.options,
                correct_answer=q.options[q.correct_index or 0],
                explanation=q.explanation,
            )
            for index, q in enumerate(plan.questions)
        ],
        source_image=source_image,
    )


class Gemma4StudyMaterialGenerator(StudyMaterialGenerator):
    """Gemma 4 generator backed by Google AI Studio (model: gemma-4-31b-it)."""

    name = "gemma4"

    async def generate(self, source_image: SourceImage) -> StudyMaterial:
        settings = get_settings()

        if not settings.google_api_key:
            raise ProviderNotAvailableError(
                "Gemma 4 generation is not configured: GOOGLE_API_KEY is missing on the backend.",
                detail={"ai_provider": settings.ai_provider, "model": settings.gemma_model},
            )

        record = state.get_upload(source_image.upload_id)
        if record is None or not record.stored_path.exists():
            raise FileNotFoundError_(
                "The uploaded image is no longer available. Please upload the page again."
            )

        try:
            image_bytes = record.stored_path.read_bytes()
        except OSError:
            raise ApiError(500, "storage_error", "The stored image could not be read. Please upload it again.")

        mime_type = record.content_type if record.content_type in ("image/png", "image/jpeg") else "image/png"

        started = time.monotonic()
        text = await self._call_model(image_bytes, mime_type)
        elapsed = time.monotonic() - started
        logger.info("Gemma 4 generation completed in %.1fs (model=%s)", elapsed, settings.gemma_model)

        data = extract_json_object(text)
        plan = normalize_plan(data)
        return build_study_material(plan, source_image, generator=self.name)

    # ------------------------------------------------------------------
    async def _call_model(self, image_bytes: bytes, mime_type: str) -> str:
        settings = get_settings()

        # Imported lazily so the app still boots if the SDK is missing, and the
        # mock provider works without google-genai installed.
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            raise ProviderNotAvailableError(
                "The google-genai SDK is not installed on the backend. "
                "Install it with `pip install google-genai`."
            )

        client = genai.Client(
            api_key=settings.google_api_key,
            http_options=types.HttpOptions(timeout=int(settings.ai_timeout_seconds * 1000)),
        )

        try:
            response = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=settings.gemma_model,
                    contents=[
                        types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                        PROMPT,
                    ],
                ),
                timeout=settings.ai_timeout_seconds,
            )
        except asyncio.TimeoutError:
            raise ApiError(
                504,
                "ai_timeout",
                f"Gemma 4 did not respond within {int(settings.ai_timeout_seconds)} seconds. "
                "Please try again.",
                detail={"model": settings.gemma_model},
            )
        except Exception as exc:  # mapped below; the key is never included
            raise self._map_error(exc)

        try:
            text = response.text
        except Exception:
            text = None
        if not text or not text.strip():
            raise AiGenerationError(
                "Gemma 4 returned no text for this page. It may have been blocked or the image "
                "may be unreadable — try a clearer photo.",
                detail={"model": settings.gemma_model},
            )
        return text[:MAX_MODEL_TEXT_CHARS]

    # ------------------------------------------------------------------
    @staticmethod
    def _map_error(exc: Exception) -> ApiError:
        """Translate provider failures into clear API errors. No retries, no model switching."""
        raw_code = getattr(exc, "code", None)
        code: Optional[int] = None
        if isinstance(raw_code, int):
            code = raw_code
        elif isinstance(raw_code, str) and raw_code.isdigit():
            code = int(raw_code)

        status = str(getattr(exc, "status", "") or "")
        message = str(getattr(exc, "message", "") or exc)
        lowered = f"{status} {message}".lower()
        settings = get_settings()
        model = settings.gemma_model

        if code == 429 or "quota" in lowered or "resource_exhausted" in lowered or "rate limit" in lowered:
            return ApiError(
                429,
                "ai_rate_limited",
                "Gemma 4 is rate-limited or the quota is exhausted. Please wait a moment and try again.",
                detail={"model": model, "provider": "Google AI Studio"},
            )
        if code in (401, 403) or "api key" in lowered or "unauthenticated" in lowered or "permission_denied" in lowered:
            return ApiError(
                503,
                "ai_auth_failed",
                "Google AI Studio rejected the backend credentials. Check GOOGLE_API_KEY on the server.",
                detail={"model": model, "provider": "Google AI Studio"},
            )
        if code == 404 or "not found" in lowered and "model" in lowered:
            return ApiError(
                502,
                "ai_model_unavailable",
                f"The model '{model}' is not available to this API key. No other model was used.",
                detail={"model": model},
            )
        if code in (400, 422) or "invalid_argument" in lowered:
            return ApiError(
                422,
                "ai_invalid_input",
                "Google AI Studio rejected the request (the image may be unsupported or malformed). "
                "Try a different page image.",
                detail={"model": model},
            )
        if code in (500, 502, 503, 504) or "unavailable" in lowered or "internal" in lowered:
            return ApiError(
                503,
                "ai_provider_unavailable",
                "Gemma 4 is temporarily unavailable or under high demand. Please retry in a moment.",
                detail={"model": model, "provider": "Google AI Studio"},
            )
        if isinstance(exc, (asyncio.TimeoutError, TimeoutError)) or "timed out" in lowered or "timeout" in lowered:
            return ApiError(
                504,
                "ai_timeout",
                "The request to Gemma 4 timed out. Please try again.",
                detail={"model": model},
            )

        logger.warning("Gemma 4 provider error: %s", type(exc).__name__)
        return ApiError(
            502,
            "ai_generation_failed",
            "Gemma 4 could not generate study material for this page. Please try again.",
            detail={"model": model},
        )
