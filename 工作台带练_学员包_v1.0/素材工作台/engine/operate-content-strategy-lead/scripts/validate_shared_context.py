from __future__ import annotations


def validate(value: dict) -> list[str]:
    errors = []
    required = ("context_id", "company", "version", "created_at", "created_by", "people", "offerings", "scenes", "knowledge", "boundaries", "sources")
    if value.get("schema_version") != "shared_enterprise_context/v1": errors.append("schema_version:unsupported")
    for key in required:
        if key not in value or value[key] in (None, ""): errors.append(f"{key}:missing")
    source_ids = {row.get("source_id") for row in value.get("sources") or []}
    for group in ("knowledge", "boundaries"):
        for index, item in enumerate(value.get(group) or []):
            if item.get("kind") in {"fact", "boundary"} and not item.get("source_refs"):
                errors.append(f"{group}[{index}].source_refs:required")
            for ref in item.get("source_refs") or []:
                if ref not in source_ids: errors.append(f"{group}[{index}].source_refs:dangling:{ref}")
    def check_refs(node, path):
        if isinstance(node, dict):
            for ref in node.get("source_refs") or []:
                if ref not in source_ids: errors.append(f"{path}.source_refs:dangling:{ref}")
            for key, child in node.items(): check_refs(child, f"{path}.{key}")
        elif isinstance(node, list):
            for index, child in enumerate(node): check_refs(child, f"{path}[{index}]")
    check_refs(value.get("strategy_foundation") or {}, "strategy_foundation")
    return sorted(set(errors))
