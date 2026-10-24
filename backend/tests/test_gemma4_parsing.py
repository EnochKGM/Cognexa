"""Unit tests for the Gemma 4 output parser/builder (no network calls).

These tests cover the validation layer that protects the app from malformed
model output. The live model itself is exercised separately via the API.
"""

import json

import pytest

from app.errors import AiGenerationError, ApiError
from app.schemas import SourceImage
from app.services.gemma4 import build_study_material, extract_json_object, normalize_plan


def make_plan_dict(**overrides):
    plan = {
        "main_topic": "Photosynthesis",
        "description": "Plants convert light energy into glucose using water and carbon dioxide.",
        "summary_sections": [
            {"title": "Light reactions", "content": "Water is split and ATP/NADPH are produced."},
            {"title": "Calvin cycle", "content": "RuBisCO fixes CO2 into G3P."},
        ],
        "key_terms": [
            {"term": "Chlorophyll", "definition": "Light-absorbing pigment."},
            {"term": "Stroma", "definition": "Site of the Calvin cycle."},
            {"term": "ATP", "definition": "Energy carrier."},
            {"term": "NADPH", "definition": "Electron carrier."},
        ],
        "subtopics": [
            {"label": "Light Reactions", "concepts": ["Photosystems", "Photolysis"]},
            {"label": "Calvin Cycle", "concepts": ["Carbon fixation", "G3P"]},
            {"label": "Inputs & Outputs", "concepts": ["Sunlight", "Glucose"]},
        ],
        "questions": [
            {
                "question": f"Question {i}?",
                "options": ["A", "B", "C", "D"],
                "correct_index": i % 4,
                "explanation": f"Explanation {i}.",
            }
            for i in range(5)
        ],
    }
    plan.update(overrides)
    return plan


def make_source() -> SourceImage:
    return SourceImage(
        upload_id="a" * 32,
        filename="page.png",
        content_type="image/png",
        size_bytes=100,
        width=100,
        height=100,
        url="/api/uploads/" + "a" * 32,
    )


def test_extract_json_handles_markdown_fences():
    payload = "```json\n" + json.dumps(make_plan_dict()) + "\n```"
    data = extract_json_object(payload)
    assert data["main_topic"] == "Photosynthesis"


def test_extract_json_rejects_non_json():
    with pytest.raises(AiGenerationError):
        extract_json_object("Here is your study plan: not json at all")
    with pytest.raises(AiGenerationError):
        extract_json_object("")


def test_normalize_and_build_matches_frontend_contract():
    plan = normalize_plan(make_plan_dict())
    result = build_study_material(plan, make_source(), result_id="r" * 32)

    assert result.is_demo is False
    assert result.generator == "gemma4"
    assert result.main_topic.label == "Photosynthesis"
    assert len(result.subtopics) == 3
    assert len(result.questions) == 5
    assert len(result.key_terms) == 4

    node_ids = {node.id for node in result.nodes}
    assert all(edge.source in node_ids and edge.target in node_ids for edge in result.edges)
    # Every non-topic node's parent link exists as an edge.
    edge_pairs = {(edge.source, edge.target) for edge in result.edges}
    for node in result.nodes:
        if node.parent is not None:
            assert node.parent in node_ids
            assert (node.parent, node.id) in edge_pairs

    for question in result.questions:
        assert len(question.options) == 4
        assert question.correct_answer in question.options
        assert question.explanation


def test_correct_index_maps_to_answer_string():
    plan = normalize_plan(make_plan_dict())
    assert plan.questions[0].correct_index == 0
    result = build_study_material(plan, make_source())
    assert result.questions[0].correct_answer == result.questions[0].options[0]


def test_correct_answer_fallback_by_text():
    data = make_plan_dict()
    data["questions"][0].pop("correct_index")
    data["questions"][0]["correct_answer"] = "c"
    plan = normalize_plan(data)
    assert plan.questions[0].correct_index == 2


def test_invalid_question_is_rejected():
    data = make_plan_dict()
    data["questions"] = data["questions"][:4]  # only 4 valid questions
    with pytest.raises(AiGenerationError):
        normalize_plan(data)

    bad_options = make_plan_dict()
    bad_options["questions"][0]["options"] = ["A", "B", "C"]  # needs exactly 4
    with pytest.raises(AiGenerationError):
        normalize_plan(bad_options)


def test_out_of_range_correct_index_is_rejected():
    data = make_plan_dict()
    data["questions"][0]["correct_index"] = 9
    with pytest.raises(AiGenerationError):
        normalize_plan(data)


def test_too_few_subtopics_is_rejected():
    data = make_plan_dict()
    data["subtopics"] = data["subtopics"][:2]
    with pytest.raises(AiGenerationError):
        normalize_plan(data)


def test_model_error_payload_becomes_readable_422():
    with pytest.raises(ApiError) as excinfo:
        normalize_plan({"error": "The image is too blurry to read."})
    assert excinfo.value.status_code == 422
    assert excinfo.value.code == "image_unreadable"
    assert "too blurry" in excinfo.value.message
