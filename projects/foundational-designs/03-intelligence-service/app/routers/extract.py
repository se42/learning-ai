"""
Extraction Router — Turn Unstructured Text into Structured Data

The "killer app" for a first integration. Your Rails app has text that
needs to become data. Send the text and describe what you want extracted;
get back validated JSON.

Example Rails usage:
    response = IntelligenceClient.extract(
      text: support_email.body,
      schema_hint: "contact info: name, email, phone, company"
    )
    contact = Contact.new(response["extracted"])
"""

from fastapi import APIRouter, HTTPException

from app.models import ExtractionRequest, ExtractionResponse
from app.services.extraction_service import extract_structured

router = APIRouter(prefix="/api/extract", tags=["extraction"])


@router.post("", response_model=ExtractionResponse)
async def extract(request: ExtractionRequest):
    """Extract structured data from unstructured text.

    Send any text (email, meeting notes, support ticket) plus a description
    of what you want extracted, and get back a JSON object with the fields
    populated from the text.

    The schema_hint is deliberately flexible — it's natural language, not a
    formal schema. This means non-technical stakeholders can define extraction
    templates without writing code.
    """
    try:
        result = await extract_structured(
            text=request.text,
            schema_hint=request.schema_hint,
            feature=request.feature,
        )
    except ValueError as e:
        # Unknown feature name
        raise HTTPException(status_code=400, detail=str(e))
    except ImportError as e:
        # Missing provider package
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        # LLM provider failures
        raise HTTPException(
            status_code=502,
            detail=f"LLM provider error during extraction: {e}. "
            "Check API keys and provider status.",
        )

    return ExtractionResponse(
        extracted=result["extracted"],
        model_used=result["model_used"],
    )
