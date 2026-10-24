"""Generator factory.

Selects the active `StudyMaterialGenerator` based on `AI_PROVIDER`:

* "gemma4" -> Gemma4StudyMaterialGenerator (Gemma 4 via Google AI Studio)
* "mock"   -> MockStudyMaterialGenerator (offline demo data, zero AI calls)

The frontend never needs to know which generator ran — it always receives the
same `StudyMaterial` contract.
"""

from __future__ import annotations

from ..config import get_settings
from ..errors import ApiError
from .base import StudyMaterialGenerator
from .gemma4 import Gemma4StudyMaterialGenerator
from .mock_generator import MockStudyMaterialGenerator

__all__ = [
    "StudyMaterialGenerator",
    "MockStudyMaterialGenerator",
    "Gemma4StudyMaterialGenerator",
    "get_generator",
]


def get_generator() -> StudyMaterialGenerator:
    provider = get_settings().ai_provider.strip().lower()
    if provider == "mock":
        return MockStudyMaterialGenerator()
    if provider == "gemma4":
        return Gemma4StudyMaterialGenerator()
    raise ApiError(
        500,
        "invalid_ai_provider",
        f"Unknown AI_PROVIDER '{provider}'. Supported values: 'mock', 'gemma4'.",
    )
