"""Mock generation + result retrieval tests."""

REQUIRED_STUDY_KEYS = {
    "result_id",
    "is_demo",
    "generator",
    "main_topic",
    "subtopics",
    "nodes",
    "edges",
    "summary",
    "key_terms",
    "questions",
    "source_image",
}


def generate(client, upload_id):
    response = client.post("/api/generate", json={"upload_id": upload_id})
    assert response.status_code == 200, response.text
    return response.json()


def test_generate_returns_stable_contract(client, uploaded_png):
    body = generate(client, uploaded_png["upload_id"])

    assert REQUIRED_STUDY_KEYS.issubset(body.keys())
    assert body["is_demo"] is True
    assert body["generator"] == "mock"
    assert len(body["result_id"]) == 32

    # Mind map: central topic + several subtopics + concepts, all with stable ids.
    node_types = {n["node_type"] for n in body["nodes"]}
    assert node_types == {"topic", "subtopic", "concept"}
    topic_nodes = [n for n in body["nodes"] if n["node_type"] == "topic"]
    assert len(topic_nodes) == 1
    assert topic_nodes[0]["parent"] is None
    assert body["main_topic"]["id"] == topic_nodes[0]["id"]
    assert len(body["subtopics"]) >= 3
    assert len(body["nodes"]) >= 10

    node_ids = [n["id"] for n in body["nodes"]]
    assert len(node_ids) == len(set(node_ids)), "node ids must be unique"

    # Every node has a label and an initial position; parents must exist.
    for node in body["nodes"]:
        assert node["label"]
        assert "x" in node["position"] and "y" in node["position"]
        if node["parent"] is not None:
            assert node["parent"] in node_ids

    # Edges reference real nodes; parent relationships match the topology.
    for edge in body["edges"]:
        assert edge["source"] in node_ids
        assert edge["target"] in node_ids
        assert edge["id"]
    parent_edges = {(e["source"], e["target"]) for e in body["edges"]}
    for node in body["nodes"]:
        if node["parent"] is not None:
            assert (node["parent"], node["id"]) in parent_edges

    # Summary + key terms.
    assert body["summary"]["overview"]
    assert len(body["summary"]["sections"]) >= 2
    for section in body["summary"]["sections"]:
        assert section["title"] and section["content"]
    assert len(body["key_terms"]) >= 4
    for term in body["key_terms"]:
        assert term["term"] and term["definition"]

    # Quiz: 3-5 questions, scorable, with explanations.
    assert 3 <= len(body["questions"]) <= 5
    for question in body["questions"]:
        assert question["type"] == "multiple_choice"
        assert question["question"]
        assert len(question["options"]) >= 2
        assert question["correct_answer"] in question["options"]
        assert question["explanation"]

    # Source image metadata mirrors the upload.
    assert body["source_image"]["upload_id"] == uploaded_png["upload_id"]
    assert body["source_image"]["url"] == f"/api/uploads/{uploaded_png['upload_id']}"


def test_generate_is_deterministic_per_image_but_ids_are_unique(client, uploaded_png):
    first = generate(client, uploaded_png["upload_id"])
    second = generate(client, uploaded_png["upload_id"])

    # Same image -> same demo topic content, but each request gets its own result id.
    assert first["main_topic"]["label"] == second["main_topic"]["label"]
    assert first["result_id"] != second["result_id"]


def test_generated_result_is_retrievable(client, uploaded_png):
    body = generate(client, uploaded_png["upload_id"])

    response = client.get(f"/api/results/{body['result_id']}")
    assert response.status_code == 200
    assert response.json() == body


def test_generate_rejects_unknown_upload_id(client):
    response = client.post("/api/generate", json={"upload_id": "0" * 32})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_generate_rejects_malformed_upload_id(client):
    response = client.post("/api/generate", json={"upload_id": "not-a-real-id"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_upload_id"


def test_generate_rejects_missing_field(client):
    response = client.post("/api/generate", json={})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_unknown_result_id_returns_structured_404(client):
    response = client.get("/api/results/" + "f" * 32)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
