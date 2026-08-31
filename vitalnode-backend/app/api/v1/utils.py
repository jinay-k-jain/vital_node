"""
Shared API utility helpers.
"""


def ev(v) -> str:
    """
    Safe enum-to-string helper.
    SQLAlchemy sometimes returns plain strings instead of enum instances
    depending on how the object was loaded. This handles both cases.
    """
    if v is None:
        return None
    return v.value if hasattr(v, "value") else str(v)
