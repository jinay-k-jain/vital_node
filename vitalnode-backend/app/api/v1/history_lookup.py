"""
Patient History Lookup API - /api/v1/history/lookup

GET /api/v1/history/lookup?name=Rajesh%20Kumar&age=58

Searches pre-loaded patient history records by name and age.
Returns history if found, or null if no match.
This replaces manual history entry in the New Assessment form.
"""
from fastapi import APIRouter, Query
from typing import Optional

from app.api.v1.deps import CurrentUser
from app.data.patient_history_records import lookup_patient_history

router = APIRouter(prefix="/history", tags=["Patient History"])


@router.get("/lookup", summary="Look up pre-loaded patient history by name and age")
async def lookup_history(
    current_user: CurrentUser,
    name: Optional[str] = Query(None, description="Patient full name (exact match, case-insensitive)"),
    age: Optional[int] = Query(None, description="Patient age"),
):
    """
    Search the pre-loaded patient history database.
    Returns matched history or null if no record found.
    Frontend uses this to auto-populate history context for the ML model.
    """
    if not name and not age:
        return {"found": False, "record": None}

    record = lookup_patient_history(name or "", age or 0)

    if not record:
        return {"found": False, "record": None}

    return {
        "found": True,
        "record": {
            "name": record["name"],
            "history_text": record["history_text"],
            "conditions": record["conditions"],
            "medications": record["medications"],
            "allergies": record["allergies"],
        },
    }
