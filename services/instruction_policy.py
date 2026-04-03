MAX_ORG_CUSTOM_INSTRUCTIONS = 1200
MAX_PROJECT_CUSTOM_INSTRUCTIONS = 1200

_DISALLOWED_PATTERNS = [
    "ignore previous instructions",
    "ignore all previous instructions",
    "system prompt",
    "developer message",
    "reveal chain of thought",
]


def validate_custom_instructions(value: str, *, max_length: int) -> str:
    normalized = (value or "").strip()
    if not normalized:
        return ""

    if len(normalized) > max_length:
        raise ValueError(f"Instructions exceed max length of {max_length} characters.")

    lowered = normalized.lower()
    for pattern in _DISALLOWED_PATTERNS:
        if pattern in lowered:
            raise ValueError("Instructions contain restricted prompt-injection wording.")

    return normalized


def build_merged_instructions(
    organization_instructions: str | None,
    project_instructions: str | None,
) -> str | None:
    org = (organization_instructions or "").strip()
    project = (project_instructions or "").strip()

    blocks: list[str] = []
    if org:
        blocks.append(f"[Organization Instructions]\n{org}")
    if project:
        blocks.append(f"[Project Instructions]\n{project}")

    if not blocks:
        return None
    return "\n\n".join(blocks)
