"""Small, explicit JSON Schema subset used by both the API and local validator."""

from .utils import QAError


def obj(**properties):
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


def arr(items):
    return {"type": "array", "items": items}


def enum(*values):
    return {"type": "string", "enum": list(values)}


TEXT = {"type": "string"}
INT = {"type": "integer"}
REF = obj(path=TEXT, start_line=INT, end_line=INT, reason=TEXT)
SCENARIO = obj(id=TEXT, behavior=TEXT, risk=enum("low", "medium", "high", "critical"),
               layer=enum("unit", "component", "api", "integration", "e2e", "manual", "eval"),
               rationale=TEXT, oracle=TEXT,
               coverage=enum("covered", "partial", "missing", "unknown"),
               references=arr(REF), gaps=arr(TEXT))
SCHEMAS = {
    "risk": obj(summary=TEXT, scenarios=arr(SCENARIO), questions=arr(TEXT), limitations=arr(TEXT)),
    "builder": obj(summary=TEXT, files=arr(obj(path=TEXT, content=TEXT, scenario_ids=arr(TEXT),
                                             rationale=TEXT)),
                   suggested_checks=arr(TEXT), limitations=arr(TEXT)),
    "failure": obj(summary=TEXT, findings=arr(obj(
        classification=enum("product", "test", "environment", "data", "suspected_flaky", "unknown"),
        confidence=enum("low", "medium", "high"), hypothesis=TEXT,
        references=arr(REF), alternative_causes=arr(TEXT), next_action=TEXT,
        suggested_owner=TEXT)), limitations=arr(TEXT)),
}


def validate(value, schema, path="$"):
    """Validate only the schema keywords emitted above; reject unknown fields."""
    kind = schema["type"]
    types = {"string": str, "array": list, "object": dict, "integer": int}
    if type(value) is not types[kind]:
        raise QAError(f"{path}: expected {kind}")
    if "enum" in schema and value not in schema["enum"]:
        raise QAError(f"{path}: unsupported value {value!r}")
    if kind == "object":
        if set(value) != set(schema["properties"]):
            raise QAError(f"{path}: fields must be {list(schema['properties'])}")
        for key, child in schema["properties"].items():
            validate(value[key], child, f"{path}.{key}")
    if kind == "array":
        if len(value) > 100:
            raise QAError(f"{path}: too many items (maximum 100)")
        for index, item in enumerate(value):
            validate(item, schema["items"], f"{path}[{index}]")
