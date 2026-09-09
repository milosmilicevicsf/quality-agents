"""Synthetic admissions example with an intentional deadline-boundary defect."""


def can_submit(now, deadline):
    """Both inputs must be timezone-aware datetime values."""
    if now.tzinfo is None or deadline.tzinfo is None:
        raise ValueError("Timezone-aware dates required")
    return now <= deadline
