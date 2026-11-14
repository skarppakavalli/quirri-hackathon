import json

with open("openapi.json", encoding="utf-8") as f:
    spec = json.load(f)

for path, methods in spec["paths"].items():
    for method, details in methods.items():
        if method.lower() not in [
            "get", "post", "put", "patch", "delete"
        ]:
            continue

        print("\n", method.upper(), path)
        print("Summary:", details.get("summary"))

        # Request body schema
        body = details.get("requestBody", {})
        if body:
            print("Request body:")
            print(json.dumps(body, indent=2))

        # Query/path parameters
        params = details.get("parameters", [])
        if params:
            print("Parameters:")
            print(json.dumps(params, indent=2))

        # Responses
        print("Responses:")
        print(json.dumps(
            details.get("responses", {}),
            indent=2
        ))


# Extract the actual schemas referenced by our must-have endpoints

required_schemas = [
    "LoginRequest",
    "LoginResponse",
    "UserSummary",
    "RequestCreate",
    "RequestResponse",
    "ApproveRequestPayload",
    "RejectRequestPayload",
    "AttendanceSummaryResponse",
    "TimetableSlotResponse",
    "CalendarEventResponse",
]

schemas = spec.get("components", {}).get("schemas", {})

for name in required_schemas:
    print(f"\n{'=' * 60}")
    print(f"SCHEMA: {name}")
    print("=" * 60)

    schema = schemas.get(name)

    if schema:
        print(json.dumps(schema, indent=2))
    else:
        print("Schema not found")
