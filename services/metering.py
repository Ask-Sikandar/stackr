from apps.accounts.models import Project, UsageEvent


def record_usage_event(
    *,
    event_type: str,
    organization_id: int | None = None,
    project_id: int | None = None,
    quantity: int = 1,
    metadata: dict | None = None,
) -> bool:
    """
    Best-effort metering hook.

    Returns True when a UsageEvent row is persisted.
    Returns False for validation errors or persistence failures.
    """
    event_type = (event_type or "").strip()
    if not event_type:
        return False

    if quantity == 0:
        return False

    if organization_id is None and project_id is not None:
        organization_id = (
            Project.objects.filter(id=project_id)
            .values_list("organization_id", flat=True)
            .first()
        )

    if organization_id is None:
        return False

    try:
        UsageEvent.objects.create(
            organization_id=organization_id,
            project_id=project_id,
            event_type=event_type,
            quantity=int(quantity),
            metadata=metadata or {},
        )
        return True
    except Exception:
        return False
