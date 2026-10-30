"""Gemini integration with a fake Gemini server: caching, quota handling, validation and fallbacks."""

import base64
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.core import gemini
from backend.main import app

client = TestClient(app)
IMAGE = base64.b64encode(b"\xff\xd8" + b"0" * 200).decode()


@pytest.fixture
def offline_coach(monkeypatch):
    """The coach searches the catalogue fixture, like the catalogue routes do in tests."""
    from backend.tests import catalogue_fixture as fx

    monkeypatch.setattr("backend.core.off_catalogue.browse_catalogue", fx.fake_browse)


@pytest.fixture
def fake_gemini(monkeypatch):
    """Points Gemini at a fake server; returns the list of request bodies and a setter for the reply."""
    calls = []
    state = {"status": 200, "reply": {}}

    def handler(request):
        calls.append(json.loads(request.content))
        if state["status"] != 200:
            return httpx.Response(state["status"], json={})
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": json.dumps(state["reply"])}]}}]})

    real_client = httpx.Client
    monkeypatch.setattr(gemini, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(gemini.httpx, "Client", lambda **kw: real_client(transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(gemini, "_cache", {})
    monkeypatch.setattr(gemini, "_budget", {"day": "", "used": 0})
    monkeypatch.setattr(gemini, "_paused_until", 0.0)
    return calls, state


def test_without_a_key_everything_falls_back(monkeypatch):
    monkeypatch.setattr(gemini, "GEMINI_API_KEY", "")
    assert gemini.generate_json("x", {"type": "OBJECT"}) is None
    status = client.get("/api/ai/status").json()
    assert status["available"] is False
    assert status["models"] == {"category": False, "quality": False, "recommender": False}  # none trained yet
    res = client.post("/api/ai/read-claims", json={"image": IMAGE})
    assert res.status_code == 503 and res.json()["detail"]["error_code"] == "AI_UNAVAILABLE"


def test_the_same_request_is_answered_from_the_cache(fake_gemini):
    calls, state = fake_gemini
    state["reply"] = {"claims": ["High protein"]}
    first = client.post("/api/ai/read-claims", json={"image": IMAGE}).json()
    second = client.post("/api/ai/read-claims", json={"image": IMAGE}).json()
    assert first == second == {"claims": ["High protein"]}
    assert len(calls) == 1
    assert calls[0]["generationConfig"]["thinkingConfig"] == {"thinkingBudget": 0}


def test_a_rate_limit_reply_pauses_gemini(fake_gemini):
    calls, state = fake_gemini
    state["status"] = 429
    assert gemini.generate_json("a", {"type": "OBJECT"}) is None
    assert gemini.is_available() is False
    assert gemini.generate_json("b", {"type": "OBJECT"}) is None
    assert len(calls) == 1  # no second call while paused


def test_the_daily_budget_caps_calls(fake_gemini, monkeypatch):
    calls, state = fake_gemini
    monkeypatch.setattr(gemini, "GEMINI_DAILY_LIMIT", 2)
    state["reply"] = {"ok": True}
    for prompt in ("a", "b", "c"):
        gemini.generate_json(prompt, {"type": "OBJECT"})
    assert len(calls) == 2


def test_label_values_are_range_checked(fake_gemini):
    _, state = fake_gemini
    state["reply"] = {"basis": "per 100g", "energy_kcal": 480, "sugars_g": 22.5, "sodium_mg": -5, "protein_g": 99999,
                      "product_name": "Test Biscuit"}
    data = client.post("/api/ai/read-label", json={"image": IMAGE}).json()
    assert data["values"]["energy_kcal"] == 480 and data["values"]["sugars_g"] == 22.5
    assert data["values"]["sodium_mg"] is None and data["values"]["protein_g"] is None
    assert data["measurement_basis"] == "per 100g" and data["product_name"] == "Test Biscuit"


def test_questions_the_built_in_answers_cover_never_call_gemini(fake_gemini):
    calls, _ = fake_gemini
    res = client.post("/api/assistant/ask", json={"product_id": "OFF_2000000000015", "question": "How much sugar does it have?"})
    assert res.status_code == 200 and res.json()["understood"] is True
    assert calls == []


def test_other_questions_are_answered_from_the_product_facts(fake_gemini):
    calls, state = fake_gemini
    state["reply"] = {"answer": "It works as an evening snack in small portions.", "details": ["Sodium is above the limit."]}
    res = client.post("/api/assistant/ask", json={"product_id": "OFF_2000000000015", "question": "Can I eat this in the evening?"})
    data = res.json()
    assert data["conclusion"] == [{"text": "It works as an evening snack in small portions."}]
    assert data["details"] == [[{"text": "Sodium is above the limit."}]]
    prompt = calls[0]["contents"][0]["parts"][0]["text"]
    assert "Nutrition grade (same for everyone)" in prompt and "can i eat this in the evening" in prompt


def test_a_failed_gemini_answer_falls_back_to_the_built_in_one(fake_gemini):
    _, state = fake_gemini
    state["status"] = 500
    res = client.post("/api/assistant/ask", json={"product_id": "OFF_2000000000015", "question": "Can I eat this in the evening?"})
    assert res.status_code == 200 and res.json()["understood"] is False


def test_a_model_that_rejects_the_thinking_setting_is_retried_without_it(monkeypatch):
    calls = []

    def handler(request):
        body = json.loads(request.content)
        calls.append(body)
        if "thinkingConfig" in body["generationConfig"]:
            return httpx.Response(400, json={})
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": '{"ok": true}'}]}}]})

    real_client = httpx.Client
    monkeypatch.setattr(gemini, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(gemini.httpx, "Client", lambda **kw: real_client(transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(gemini, "_cache", {})
    monkeypatch.setattr(gemini, "_budget", {"day": "", "used": 0})
    monkeypatch.setattr(gemini, "_paused_until", 0.0)
    monkeypatch.setattr(gemini, "_no_thinking_config", set())
    assert gemini.generate_json("a", {"type": "OBJECT"}, text_only=True) == {"ok": True}
    assert gemini.generate_json("b", {"type": "OBJECT"}, text_only=True) == {"ok": True}
    assert len(calls) == 3  # one rejected attempt, then the setting is left out from then on


def test_an_everyday_words_search_with_no_results_is_retried_with_product_keywords(fake_gemini):
    calls, state = fake_gemini
    state["reply"] = {"keywords": "masala bhujia"}
    data = client.get("/api/products", params={"query": "spicy crunchy thing for tea time"}).json()
    assert data["rewritten_query"] == "masala bhujia"
    assert any("Bhujia" in p["product_name"] for p in data["products"])
    assert len(calls) == 1

    short = client.get("/api/products", params={"query": "zzqx"}).json()
    assert short["rewritten_query"] is None and len(calls) == 1  # short searches never call it


def test_claims_the_rules_dont_recognise_are_checked_in_one_request(fake_gemini):
    calls, state = fake_gemini
    state["reply"] = {"results": [
        {"claim": "no oil", "claim_type": "Ingredient & Composition Claim", "status": "Potentially inconsistent with the checked criteria",
         "evidence": "Ingredients list palm oil.", "explanation": "Oil is an ingredient."},
        {"claim": "baked not fried", "claim_type": "Processing Claim", "status": "Insufficient evidence to assess compliance",
         "evidence": "The label doesn't say how it was cooked.", "explanation": "Can't tell from the label."},
    ]}
    product = {"product_name": "Chips", "category": "Snacks", "protein_g": 12, "ingredients": "rice meal, palm oil, salt"}
    res = client.post("/api/claims/check", json={"claims": "no oil\nbaked not fried\nhigh protein", "product": product}).json()
    by_claim = {c["claim"]: c for c in res["claims"]}
    assert by_claim["no oil"]["compliance_status"].startswith("Potentially inconsistent")
    assert by_claim["no oil"]["evidence_available"] == "Ingredients list palm oil."
    assert by_claim["baked not fried"]["primary_claim_type"] == "Processing Claim"
    assert by_claim["high protein"]["compliance_status"].startswith("Consistent")  # built-in rule, unchanged
    assert len(calls) == 1
    assert "- no oil" in calls[0]["contents"][0]["parts"][0]["text"] and "high protein" not in calls[0]["contents"][0]["parts"][0]["text"].split("Claims:")[1]


def test_ingredient_explanations_keep_only_items_on_the_list(fake_gemini):
    _, state = fake_gemini
    state["reply"] = {"items": [
        {"as_listed": "palm oil", "what_it_is": "A vegetable oil.", "why_used": "For frying.", "note": "High in saturated fat"},
        {"as_listed": "aspartame", "what_it_is": "A sweetener.", "why_used": "Sweetness.", "note": ""},  # not on the list
    ]}
    res = client.post("/api/ai/explain-ingredients", json={"ingredients": "Rice meal, palm oil, salt"}).json()
    assert [i["as_listed"] for i in res["items"]] == ["palm oil"]


def test_comparison_patterns_always_come_back_and_the_explanation_when_available(fake_gemini, monkeypatch):
    calls, state = fake_gemini
    state["reply"] = {"explanation": "Bhujia has more sodium."}
    ids = ["OFF_2000000000015", "OFF_2000000000022"]
    data = client.post("/api/compare/explain", json={"product_ids": ids, "priority": {ids[0]: 2, ids[1]: 1}}).json()
    assert data["explanation"] == "Bhujia has more sodium."
    assert isinstance(data["patterns"], list)
    monkeypatch.setattr(gemini, "GEMINI_API_KEY", "")
    data = client.post("/api/compare/explain", json={"product_ids": ids}).json()
    assert data["explanation"] is None and isinstance(data["patterns"], list)


def test_the_coach_only_suggests_catalogue_products_it_found(fake_gemini, offline_coach):
    calls, state = fake_gemini
    # One reply serves both requests: the search plan uses keywords/category/avoid, the answer uses answer/product_ids.
    state["reply"] = {"keywords": "bhujia", "category": "All", "avoid": [], "answer": "Try the bhujia.",
                      "product_ids": ["OFF_2000000000015", "OFF_9999999999999"]}
    data = client.post("/api/ai/coach/ask", json={"question": "something spicy for tea time"}).json()
    assert data["answer"] == "Try the bhujia."
    assert [p["product_id"] for p in data["products"]] == ["OFF_2000000000015"]  # the invented id is dropped


def test_the_coach_respects_allergens_in_the_question(fake_gemini, offline_coach):
    _, state = fake_gemini
    state["reply"] = {"keywords": "bhujia", "category": "All", "avoid": ["Peanuts", "Gluten", "Milk", "Soy", "Tree Nuts", "Sesame"],
                      "answer": "Here you go.", "product_ids": ["OFF_2000000000015"]}
    data = client.post("/api/ai/coach/ask", json={"question": "bhujia without any common allergens"}).json()
    from backend.core.nutrition_scoring import assess_personalized_suitability
    from backend.products import resolve_product
    profile = {"goal": "Balanced Choices", "allergens_to_avoid": "Peanuts, Gluten, Milk, Soy, Tree Nuts, Sesame"}
    for p in data["products"]:
        assert not assess_personalized_suitability(resolve_product(p["product_id"]), profile)["has_critical_allergen_conflict"]


def test_without_gemini_the_coach_still_finds_products(monkeypatch, offline_coach):
    monkeypatch.setattr(gemini, "GEMINI_API_KEY", "")
    data = client.post("/api/ai/coach/ask", json={"question": "bhujia"}).json()
    assert data["answer"] is None
    assert any("Bhujia" in p["product_name"] for p in data["products"])
    insights = client.post("/api/ai/coach/insights", json={"product_ids": ["OFF_2000000000015", "OFF_2000000000022"]}).json()
    assert insights["count"] == 2 and insights["patterns"]


def test_a_slow_model_rests_and_the_backup_answers(monkeypatch):
    calls = []

    def handler(request):
        model = request.url.path.split("/models/")[1].split(":")[0]
        calls.append(model)
        if model == "slow-model":
            raise httpx.ReadTimeout("slow", request=request)
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": '{"ok": true}'}]}}]})

    real_client = httpx.Client
    monkeypatch.setattr(gemini, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(gemini, "GEMINI_TEXT_MODEL", "slow-model")
    monkeypatch.setattr(gemini, "GEMINI_FALLBACK_MODEL", "backup-model")
    monkeypatch.setattr(gemini.httpx, "Client", lambda **kw: real_client(transport=httpx.MockTransport(handler)))
    for name, value in (("_cache", {}), ("_budget", {"day": "", "used": 0}), ("_paused_until", 0.0),
                        ("_model_rest_until", {}), ("_no_thinking_config", set())):
        monkeypatch.setattr(gemini, name, value)
    assert gemini.generate_json("a", {"type": "OBJECT"}, text_only=True) == {"ok": True}
    assert gemini.generate_json("b", {"type": "OBJECT"}, text_only=True) == {"ok": True}
    assert calls == ["slow-model", "backup-model", "backup-model"]  # the slow model isn't tried again while resting


def test_requests_are_read_without_gemini_too():
    from backend.core.coach import _local_plan

    assert _local_plan("Low sugar breakfast cereal for kids") == {
        "category": "Breakfast Cereals", "avoid": [], "max_sugars": 5.0, "keywords": "breakfast cereal"}
    plan = _local_plan("high protein snack without peanuts")
    assert (plan["category"], plan["avoid"], plan["min_protein"]) == ("Snacks", ["Peanuts"], 10.0)
    assert _local_plan("dairy-free chocolate")["avoid"] == ["Milk"]
