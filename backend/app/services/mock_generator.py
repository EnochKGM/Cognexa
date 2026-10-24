"""Mock study-material generator (current, default).

Produces deterministic, realistic demo content with a radial mind-map layout.
Results are always flagged `is_demo=True` and labelled with `generator="mock"`,
so the UI can be honest that no AI model produced them.

Replaced later by `Gemma4StudyMaterialGenerator` (see `gemma4.py`) without any
change to the frontend contract.
"""

from __future__ import annotations

import asyncio
import hashlib
import math
import uuid
from typing import List

from ..config import get_settings
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
from .base import StudyMaterialGenerator
from .mock_content import TOPICS, TopicContent

TOPIC_RADIUS = 340.0
CONCEPT_RADIUS = 680.0


class MockStudyMaterialGenerator(StudyMaterialGenerator):
    """Deterministic mock generator — no AI, no external calls."""

    name = "mock"

    async def generate(self, source_image: SourceImage) -> StudyMaterial:
        settings = get_settings()
        if settings.mock_processing_delay > 0:
            # Simulated pipeline latency so the demo progress UI is meaningful.
            await asyncio.sleep(settings.mock_processing_delay)

        content = self._pick_content(source_image.upload_id)
        result_id = uuid.uuid4().hex
        nodes, edges = self._build_mind_map(content)
        subtopics = [Subtopic(id=f"{content.key}-sub-{i}", label=s["label"])
                     for i, s in enumerate(content.subtopics)]

        return StudyMaterial(
            result_id=result_id,
            is_demo=True,
            generator=self.name,
            main_topic=MainTopic(id=f"{content.key}-topic", label=content.label),
            subtopics=subtopics,
            nodes=nodes,
            edges=edges,
            summary=Summary(
                overview=content.summary_overview,
                sections=[SummarySection(**s) for s in content.summary_sections],
            ),
            key_terms=[KeyTerm(**t) for t in content.key_terms],
            questions=[
                Question(
                    id=f"q{i + 1}",
                    question=q.question,
                    type="multiple_choice",
                    options=q.options,
                    correct_answer=q.correct_answer,
                    explanation=q.explanation,
                )
                for i, q in enumerate(content.questions)
            ],
            source_image=source_image,
        )

    # ------------------------------------------------------------------
    def _pick_content(self, seed: str) -> TopicContent:
        """Pick a topic deterministically from the upload id (stable per image)."""
        digest = hashlib.sha256(seed.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % len(TOPICS)
        return TOPICS[index]

    def _build_mind_map(self, content: TopicContent) -> tuple[List[MindMapNode], List[MindMapEdge]]:
        nodes: List[MindMapNode] = []
        edges: List[MindMapEdge] = []

        topic_id = f"{content.key}-topic"
        nodes.append(
            MindMapNode(
                id=topic_id,
                label=content.label,
                node_type="topic",
                parent=None,
                position=Position(x=0.0, y=0.0),
            )
        )

        subtopic_count = max(len(content.subtopics), 1)
        # Start at the top and spread evenly around the circle.
        for i, sub in enumerate(content.subtopics):
            angle = -math.pi / 2 + (2 * math.pi * i / subtopic_count)
            sub_id = f"{content.key}-sub-{i}"
            sx = math.cos(angle) * TOPIC_RADIUS
            sy = math.sin(angle) * TOPIC_RADIUS

            nodes.append(
                MindMapNode(
                    id=sub_id,
                    label=sub["label"],
                    node_type="subtopic",
                    parent=topic_id,
                    position=Position(x=round(sx, 1), y=round(sy, 1)),
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

            concepts: List[str] = sub.get("concepts", [])
            concept_count = max(len(concepts), 1)
            for j, concept in enumerate(concepts):
                # Fan concept nodes outward around their subtopic's angle.
                spread = math.radians(30)
                c_angle = angle - spread / 2 + spread * (j / max(concept_count - 1, 1))
                if concept_count == 1:
                    c_angle = angle
                cx = math.cos(c_angle) * CONCEPT_RADIUS
                cy = math.sin(c_angle) * CONCEPT_RADIUS
                c_id = f"{content.key}-sub-{i}-c-{j}"

                nodes.append(
                    MindMapNode(
                        id=c_id,
                        label=concept,
                        node_type="concept",
                        parent=sub_id,
                        position=Position(x=round(cx, 1), y=round(cy, 1)),
                    )
                )
                edges.append(
                    MindMapEdge(
                        id=f"e-{sub_id}-{c_id}",
                        source=sub_id,
                        target=c_id,
                        label=None,
                    )
                )

        return nodes, edges
