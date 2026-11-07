import runpy
from pathlib import Path

import pytest

from backend import db
from backend.main import INSTRUCTIONS, app

PERSONAL = ("email", "phone", "address", "date_of_birth")


def test_seed_queues_every_claim_as_waiting(client):
    claims = client.get("/api/claims").json()
    assert len(claims) == 25
    assert {claim["status"] for claim in claims} == {"waiting"}
    assert claims[0] == {
        "claim_id": "CLM-1001",
        "claim_type": "trip_delay",
        "customer_name": "Maya Patel",
        "amount_claimed": 420.0,
        "submitted_on": "2026-06-24",
        "summary": "Flight home canceled by the airline, rebooked the next morning",
        "status": "waiting",
    }


def test_get_claim(client):
    claim = client.get("/api/claims/CLM-1001").json()
    assert claim["amount_claimed"] == 420.0
    assert claim["story"].startswith("My flight home from Rome")
    assert [item["amount"] for item in claim["items"]] == [245.0, 95.0, 80.0]
    assert len(claim["documents"]) == 4
    assert claim["thread_id"] is None


def test_get_policy(client):
    policy = client.get("/api/policies/POL-2001").json()
    assert policy["plan"] == "premium"
    assert policy["trip"]["destination"] == "Rome, Italy"
    assert policy["travelers"] == ["Maya Patel"]


def test_get_plan(client):
    plan = client.get("/api/plans/premium").json()
    assert plan["deductible"] == 50.0
    assert plan["trip_delay_waiting_hours"] == 6
    assert plan["deductible_applies_to"] == ["baggage", "emergency_medical"]


def test_claim_history_leaves_out_personal_data(client):
    response = client.get("/api/customers/CUS-3001/claims")
    history = response.json()
    assert [c["claim_id"] for c in history["previous_claims"]] == ["CLM-0412"]
    assert not any(field in response.text for field in PERSONAL)


def test_policy_wording(client):
    wording = client.get("/api/policy-wording").json()["policy_wording"]
    assert wording == (db.DATA_DIR / "policy_wording.md").read_text(encoding="utf-8")


def test_instructions(client):
    instructions = client.get("/api/instructions").json()["instructions"]
    assert instructions == INSTRUCTIONS.read_text(encoding="utf-8")


def test_list_handlers(client):
    names = [h["name"] for h in client.get("/api/handlers").json()]
    assert names == ["Dana Whitfield", "Marcus Oyelaran", "Priya Raman"]


@pytest.mark.parametrize(
    "path",
    [
        "/api/claims/CLM-9999",
        "/api/policies/POL-9999",
        "/api/plans/platinum",
        "/api/customers/CUS-9999/claims",
    ],
)
def test_unknown_records_are_not_found(client, path):
    assert client.get(path).status_code == 404


def test_seed_never_opens_the_answer_key(monkeypatch):
    opened: list[Path] = []
    original = Path.open

    def spy(self, *args, **kwargs):
        opened.append(self.resolve())
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", spy)
    db.seed()
    data = db.DATA_DIR.resolve()
    assert data / "claims.json" in opened
    assert not [p for p in opened if p.is_relative_to(data / "evals")]
    assert not [p for p in opened if p.is_relative_to(data / "security")]


def test_lifespan_seeds_a_missing_database(client, tmp_path, monkeypatch):
    monkeypatch.setenv("UNDERCOVER_DB", str(tmp_path / "fresh.db"))
    with type(client)(app) as fresh:
        assert len(fresh.get("/api/claims").json()) == 25


def resolve(schema: dict, components: dict) -> dict:
    if "$ref" in schema:
        return components[schema["$ref"].split("/")[-1]]
    return schema


def test_every_operation_follows_the_api_rules():
    spec = app.openapi()
    components = spec["components"]["schemas"]
    for path, methods in spec["paths"].items():
        for method, operation in methods.items():
            where = f"{method.upper()} {path}"
            assert operation["operationId"], where
            assert operation["summary"], where
            assert "\n" not in operation.get("description", ""), where
            assert all(p["required"] for p in operation.get("parameters", [])), where
            if "requestBody" in operation:
                body = operation["requestBody"]
                schema = resolve(
                    body["content"]["application/json"]["schema"], components
                )
                assert body["required"], where
                assert set(schema["properties"]) == set(schema["required"]), where


def test_seed_command(capsys):
    runpy.run_module("backend.seed", run_name="__main__")
    assert "Seeded" in capsys.readouterr().out
