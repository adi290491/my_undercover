from fastapi.routing import APIRoute

from backend.main import app

SCHEMA = app.openapi()


def operations():
    for operations in SCHEMA["paths"].values():
        yield from operations.values()


def body_fields(operation):
    ref = operation["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    model = SCHEMA["components"]["schemas"][ref.rsplit("/", 1)[-1]]
    return set(model["properties"]), set(model.get("required", []))


def test_every_route_has_an_operation_id_and_a_one_line_docstring():
    routes = [r for r in app.routes if isinstance(r, APIRoute)]
    ids = [r.operation_id for r in routes]
    assert all(ids)
    assert len(set(ids)) == len(ids)
    for route in routes:
        doc = (route.endpoint.__doc__ or "").strip()
        assert doc, route.path
        assert "\n" not in doc, route.path


def test_no_route_has_an_optional_input():
    for operation in operations():
        assert all(p["required"] for p in operation.get("parameters", []))
        if "requestBody" in operation:
            assert operation["requestBody"]["required"]
            fields, required = body_fields(operation)
            assert fields == required, operation["operationId"]
