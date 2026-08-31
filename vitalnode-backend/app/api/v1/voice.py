"""
Voice Transcription API - /api/v1/voice/*

The frontend uploads audio here. The backend calls the configured
speech-to-text provider. API keys are NEVER exposed to the frontend.

POST /api/v1/voice/transcribe - transcribe audio file
POST /api/v1/voice/extract-symptoms - extract symptoms from complaint text
"""
import re
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, status
from pydantic import BaseModel

from app.api.v1.deps import DbDep, CurrentUser, NurseOrClinician
from app.core.config import get_settings
from app.core.logging import get_logger

router = APIRouter(prefix="/voice", tags=["Voice & NLP"])
logger = get_logger(__name__)
settings = get_settings()


class TranscriptResponse(BaseModel):
    transcript: str
    language: str
    confidence: Optional[float]
    provider: str
    timestamp: str


class ExtractSymptomsRequest(BaseModel):
    complaint_text: str


class SymptomExtraction(BaseModel):
    name: str
    source: str
    confidence: float


class ExtractSymptomsResponse(BaseModel):
    symptoms: list[SymptomExtraction]
    raw_text: str
    provider: str


@router.post(
    "/transcribe",
    response_model=TranscriptResponse,
    summary="Transcribe voice audio to text",
    description=(
        "Upload an audio file. Backend calls the configured speech provider. "
        "API keys are never exposed to the frontend."
    ),
)
async def transcribe(
    db: DbDep,
    current_user: NurseOrClinician,
    audio: UploadFile = File(..., description="Audio file (wav, mp3, webm, m4a)"),
):
    provider = settings.speech_provider

    if provider == "mock":
        # Mock mode — return a realistic demo transcript
        transcript = _mock_transcript()
        return TranscriptResponse(
            transcript=transcript,
            language="en",
            confidence=0.92,
            provider="mock",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    if not settings.speech_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "VOICE_NOT_CONFIGURED",
                "message": (
                    f"Speech provider '{provider}' is configured but SPEECH_API_KEY is missing. "
                    "Set SPEECH_PROVIDER=mock for development."
                ),
            },
        )

    if provider == "openai_whisper":
        transcript_text = await _transcribe_openai(audio)
    elif provider == "assemblyai":
        transcript_text = await _transcribe_assemblyai(audio)
    else:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail={
                "code": "PROVIDER_NOT_IMPLEMENTED",
                "message": f"Speech provider '{provider}' is not yet implemented. Use SPEECH_PROVIDER=mock.",
            },
        )

    return TranscriptResponse(
        transcript=transcript_text,
        language="en",
        confidence=None,
        provider=provider,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.post(
    "/extract-symptoms",
    response_model=ExtractSymptomsResponse,
    summary="Extract symptoms from complaint text",
    description=(
        "Runs keyword/NLP extraction on the complaint text. "
        "Results are SUGGESTIONS — the nurse must confirm before they are stored."
    ),
)
async def extract_symptoms(
    payload: ExtractSymptomsRequest,
    current_user: NurseOrClinician,
    db: DbDep,
):
    symptoms = _keyword_extract(payload.complaint_text)
    return ExtractSymptomsResponse(
        symptoms=symptoms,
        raw_text=payload.complaint_text,
        provider="keyword-v1",
    )


# ── Internal helpers ───────────────────────────────────────────────────────

def _mock_transcript() -> str:
    return (
        "I have been having chest pain and difficulty breathing since this morning. "
        "I also feel dizzy and my left arm feels weak."
    )


async def _transcribe_assemblyai(audio: UploadFile) -> str:
    """
    AssemblyAI transcription.
    Free tier: 5 hours/month. No credit card required.
    Docs: https://www.assemblyai.com/docs
    """
    import httpx

    api_key = settings.speech_api_key
    audio_bytes = await audio.read()

    async with httpx.AsyncClient() as client:
        # Step 1: Upload audio to AssemblyAI
        upload_resp = await client.post(
            "https://api.assemblyai.com/v2/upload",
            headers={"authorization": api_key},
            content=audio_bytes,
            timeout=30.0,
        )
        if upload_resp.status_code != 200:
            raise HTTPException(
                status_code=503,
                detail={"code": "ASSEMBLYAI_UPLOAD_FAILED", "message": "Failed to upload audio to AssemblyAI"},
            )
        upload_url = upload_resp.json()["upload_url"]

        # Step 2: Request transcription
        transcript_resp = await client.post(
            "https://api.assemblyai.com/v2/transcript",
            headers={"authorization": api_key, "content-type": "application/json"},
            json={"audio_url": upload_url, "language_code": "en"},
            timeout=30.0,
        )
        transcript_id = transcript_resp.json()["id"]

        # Step 3: Poll until complete
        import asyncio
        for _ in range(30):  # max 30 seconds polling
            await asyncio.sleep(1)
            poll_resp = await client.get(
                f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
                headers={"authorization": api_key},
                timeout=10.0,
            )
            result = poll_resp.json()
            if result["status"] == "completed":
                return result.get("text", "")
            elif result["status"] == "error":
                raise HTTPException(
                    status_code=503,
                    detail={"code": "ASSEMBLYAI_ERROR", "message": result.get("error", "Transcription failed")},
                )

    raise HTTPException(
        status_code=503,
        detail={"code": "ASSEMBLYAI_TIMEOUT", "message": "Transcription timed out. Use manual entry."},
    )


async def _transcribe_openai(audio: UploadFile) -> str:
    """
    OpenAI Whisper API transcription.
    Requires: pip install openai
    """
    try:
        import openai  # type: ignore
        client = openai.AsyncOpenAI(api_key=settings.speech_api_key)
        audio_bytes = await audio.read()
        # Whisper expects a file-like tuple: (filename, bytes, content_type)
        response = await client.audio.transcriptions.create(
            model="whisper-1",
            file=(audio.filename or "audio.wav", audio_bytes, audio.content_type or "audio/wav"),
            response_format="text",
        )
        return str(response)
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail={"code": "OPENAI_NOT_INSTALLED", "message": "pip install openai"},
        )
    except Exception as exc:
        logger.error("openai_whisper_failed", error=str(exc))
        raise HTTPException(
            status_code=503,
            detail={"code": "TRANSCRIPTION_FAILED", "message": "Voice transcription failed. Use manual entry."},
        )


# Simple deterministic keyword extraction
# Replace with a lightweight NLP model (spaCy, etc.) if needed
SYMPTOM_PATTERNS = [
    (r"\bchest pain\b", "Chest pain", 0.95),
    (r"\bbreath(ing)?\b|\bshortness of breath\b|\bdyspn", "Dyspnea", 0.90),
    (r"\bdizz(y|iness)\b", "Dizziness", 0.92),
    (r"\bweak(ness)?\b", "Weakness", 0.85),
    (r"\bnausea\b|\bvomit", "Nausea", 0.88),
    (r"\bheadache\b|\bhead pain\b", "Headache", 0.90),
    (r"\bfever\b|\bhigh temperature\b", "Fever", 0.92),
    (r"\bpalpitation\b|\bheart racing\b|\bfast heart\b", "Palpitations", 0.88),
    (r"\bswelling\b|\bedema\b", "Swelling", 0.82),
    (r"\bpain\b", "Pain", 0.70),
    (r"\bfaint(ing)?\b|\bsynco", "Syncope", 0.85),
    (r"\bcough\b", "Cough", 0.90),
    (r"\barm (pain|weak|numb)", "Arm pain/weakness", 0.88),
    (r"\back pain\b|\bback ache\b", "Back pain", 0.85),
    (r"\babdom(en|inal)\b|\bstomach pain\b", "Abdominal pain", 0.90),
]


def _keyword_extract(text: str) -> list[SymptomExtraction]:
    text_lower = text.lower()
    results = []
    seen = set()
    for pattern, name, confidence in SYMPTOM_PATTERNS:
        if re.search(pattern, text_lower) and name not in seen:
            results.append(SymptomExtraction(name=name, source="keyword", confidence=confidence))
            seen.add(name)
    return results
