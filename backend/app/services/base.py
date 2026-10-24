"""Generator service interface.

The frontend contract is defined by `schemas.StudyMaterial`.  Any generator
that returns that shape can replace the mock implementation without touching
the frontend or the results UI.

Current implementation: `Gemma4StudyMaterialGenerator` in `gemma4.py`, using
Gemma 4 (`gemma-4-31b-it`) through Google AI Studio. Provider errors are
surfaced honestly (429/502/503/504) and it never silently switches models.
"""

from __future__ import annotations

import abc
from typing import Optional

from ..schemas import SourceImage, StudyMaterial


class StudyMaterialGenerator(abc.ABC):
    """Abstract interface for study-material generation."""

    #: short identifier stored on results, e.g. "mock" or "gemma4"
    name: str = "base"

    @abc.abstractmethod
    async def generate(self, source_image: SourceImage) -> StudyMaterial:
        """Turn an uploaded textbook image into structured study material.

        Implementations must return a complete `StudyMaterial` (mind map
        nodes/edges, summary, key terms, quiz questions) and must set
        `is_demo` honestly.
        """
        raise NotImplementedError
