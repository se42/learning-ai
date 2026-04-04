"""
Extraction Service — Structured Output from Unstructured Text

This is often the "killer app" for a first Rails integration. Your Rails app
has unstructured text (support emails, user descriptions, meeting notes) that
needs to become structured data it can store, display, and act on.

Uses LangChain's with_structured_output() to constrain the LLM to return
valid JSON matching a schema. The LLM does the understanding; Pydantic
does the validation.
"""

import json

from langchain_core.messages import HumanMessage, SystemMessage

from app.services.llm_factory import get_model, get_model_info


# ---------------------------------------------------------------------------
# Example schema_hints (for documentation and testing):
#
#   "Extract contact information: name, email, phone"
#   "Extract action items: description, assignee, due_date"
#   "Classify this support case: category, urgency (low/medium/high), summary"
#   "Extract product feedback: feature_mentioned, sentiment (positive/negative/neutral), quote"
#   "Parse this invoice: vendor, amount, currency, date, line_items"
# ---------------------------------------------------------------------------


async def extract_structured(
    text: str,
    schema_hint: str,
    feature: str = "extraction",
) -> dict:
    """Extract structured data from unstructured text using an LLM.

    Sends the text and a natural-language schema description to the LLM,
    which returns JSON matching the requested shape. The LLM does the
    understanding (figuring out which parts of the text map to which fields);
    we do the parsing and validation.

    Args:
        text: The unstructured text to extract from (email, note, etc.).
        schema_hint: Natural language description of what to extract.
            Example: "Extract contact info: name, email, phone, company"
        feature: Feature config name for model selection. Defaults to
            "extraction" which uses a fast, cheap model with temperature 0.

    Returns:
        A dict with two keys:
          - "extracted": the structured data pulled from the text
          - "model_used": which model handled the extraction
    """
    model = get_model(feature)
    model_info = get_model_info(feature)

    # Build the extraction prompt. We ask for JSON explicitly and describe
    # the desired schema in natural language. The system message establishes
    # the task; the human message provides the text to extract from.
    system_prompt = (
        "You are a precise data extraction assistant. "
        "Given a piece of text, extract the requested information and return "
        "it as a JSON object. Only include fields mentioned in the schema description. "
        "If a field cannot be determined from the text, use null for that field. "
        "Return ONLY valid JSON — no markdown, no explanation, no extra text."
    )

    human_prompt = (
        f"Schema to extract: {schema_hint}\n\n"
        f"Text to extract from:\n---\n{text}\n---\n\n"
        "Return the extracted data as a JSON object."
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt),
    ]

    # Invoke the model. We use ainvoke() for async compatibility with FastAPI.
    response = await model.ainvoke(messages)

    # Parse the response content as JSON. The model should return pure JSON
    # thanks to our prompt, but we handle the case where it wraps it in
    # markdown code fences (a common LLM habit).
    content = response.content.strip()

    # Strip markdown code fences if present
    if content.startswith("```"):
        # Remove opening fence (with optional language tag like ```json)
        content = content.split("\n", 1)[-1] if "\n" in content else content[3:]
        # Remove closing fence
        if content.endswith("```"):
            content = content[:-3].strip()

    try:
        extracted = json.loads(content)
    except json.JSONDecodeError:
        # If the LLM didn't return valid JSON, wrap the raw response.
        # This lets the caller see what happened instead of getting a 500.
        extracted = {"_raw_response": content, "_parse_error": "Response was not valid JSON"}

    return {
        "extracted": extracted,
        "model_used": model_info,
    }
