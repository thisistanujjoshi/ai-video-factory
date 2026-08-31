import json
import logging
import time
from pathlib import Path

from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.models import AgentRun
from app.providers.llm import LLMProvider

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parents[3] / "prompts"


class GenerationFailedError(Exception):
    pass


async def generate_structured[T: BaseModel](
    db: Session,
    llm: LLMProvider,
    prompt: str,
    response_model: type[T],
    *,
    agent: str,
    prompt_version: str,
    input_payload: dict,
    retries: int = 1,
    **llm_kwargs,
) -> T:
    """Call the LLM, validate its output against `response_model`, retry once
    on malformed JSON (never silently accept it), and record an AgentRun row
    either way — see spec sections 15 and 38."""

    start = time.monotonic()
    last_error: Exception | None = None
    parsed: T | None = None

    for attempt in range(retries + 1):
        raw = await llm.generate(prompt, **llm_kwargs)
        try:
            parsed = response_model.model_validate_json(raw)
            break
        except (ValidationError, json.JSONDecodeError) as exc:
            last_error = exc
            logger.warning(
                "structured generation failed (attempt %s/%s) for %s: %s",
                attempt + 1,
                retries + 1,
                response_model.__name__,
                exc,
            )

    duration_ms = int((time.monotonic() - start) * 1000)
    db.add(
        AgentRun(
            agent=agent,
            provider=type(llm).__name__,
            model=llm.model_name,
            prompt_version=prompt_version,
            input=input_payload,
            output=parsed.model_dump(mode="json") if parsed else {},
            status="success" if parsed else "failed",
            error=None if parsed else str(last_error),
            duration_ms=duration_ms,
        )
    )

    if parsed is None:
        raise GenerationFailedError(
            f"could not parse {response_model.__name__} after {retries + 1} attempt(s)"
        ) from last_error

    return parsed
