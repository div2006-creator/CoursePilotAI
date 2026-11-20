"""Local LLM client integrating with Ollama."""
from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class LLMError(RuntimeError):
    """Base exception for LLM operations."""


class OllamaConnectionError(LLMError):
    """Raised when the Ollama server is unreachable or refused connection."""


class OllamaModelNotFoundError(LLMError):
    """Raised when the configured model is not installed/pulled in Ollama."""


class OllamaTimeoutError(LLMError):
    """Raised when Ollama generation times out."""


class OllamaGenerationError(LLMError):
    """Raised when Ollama returns an error during generation."""


def get_ollama_base_url() -> str:
    """Normalize and return the configured Ollama base URL without trailing slash."""
    return settings.OLLAMA_BASE_URL.rstrip("/")


def check_ollama_status(
    base_url: Optional[str] = None,
    timeout: float = 3.0,
) -> tuple[bool, str, list[str]]:
    """Check whether the Ollama server is running and list installed models.

    Returns:
        (is_running, message, installed_models_list)
    """
    url = (base_url or get_ollama_base_url()) + "/api/tags"
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                return True, "Ollama is running", models
            return (
                False,
                f"Ollama returned unexpected status code {resp.status_code}",
                [],
            )
    except httpx.ConnectError:
        return (
            False,
            f"Ollama server not reachable at {url}. Run 'ollama serve' to start it.",
            [],
        )
    except Exception as exc:
        return False, f"Error connecting to Ollama: {exc}", []


def generate_completion(
    prompt: str,
    system: Optional[str] = None,
    response_format: Optional[str] = "json",
    temperature: float = 0.1,
    model: Optional[str] = None,
    timeout: Optional[float] = None,
) -> str:
    """Generate completion from local Ollama model.

    Args:
        prompt: User / task prompt.
        system: Optional system prompt instructions.
        response_format: Output format, e.g. "json".
        temperature: Sampling temperature (default 0.1 for deterministic academic extraction).
        model: Optional model override; defaults to settings.OLLAMA_MODEL.
        timeout: Request timeout in seconds; defaults to settings.OLLAMA_TIMEOUT_SECONDS.

    Returns:
        Generated text string (guaranteed valid JSON if response_format="json" is respected).

    Raises:
        OllamaConnectionError: If Ollama server is offline.
        OllamaModelNotFoundError: If the target model has not been pulled.
        OllamaTimeoutError: If inference exceeds timeout limit.
        OllamaGenerationError: If generation fails.
    """
    base_url = get_ollama_base_url()
    target_model = model or settings.OLLAMA_MODEL
    req_timeout = timeout if timeout is not None else float(settings.OLLAMA_TIMEOUT_SECONDS)

    payload: dict[str, Any] = {
        "model": target_model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
        },
    }
    if system:
        payload["system"] = system
    if response_format:
        payload["format"] = response_format

    endpoint = f"{base_url}/api/generate"

    try:
        with httpx.Client(timeout=req_timeout) as client:
            response = client.post(endpoint, json=payload)

            if response.status_code == 404:
                raise OllamaModelNotFoundError(
                    f"Model '{target_model}' not found on Ollama server at {base_url}. "
                    f"Pull it using: 'ollama pull {target_model}'"
                )

            if response.status_code != 200:
                raise OllamaGenerationError(
                    f"Ollama returned HTTP {response.status_code}: {response.text}"
                )

            data = response.json()
            generated_text = data.get("response", "")
            if not generated_text:
                raise OllamaGenerationError("Ollama returned an empty response")

            return generated_text

    except httpx.ConnectError as exc:
        msg = (
            f"Could not connect to Ollama server at {base_url}. "
            "Please ensure Ollama is installed and running (`ollama serve`)."
        )
        logger.error(msg)
        raise OllamaConnectionError(msg) from exc

    except (httpx.ReadTimeout, httpx.WriteTimeout, httpx.ConnectTimeout) as exc:
        msg = (
            f"Ollama inference timed out after {req_timeout:.0f}s. "
            f"Consider using a smaller model or increasing OLLAMA_TIMEOUT_SECONDS."
        )
        logger.error(msg)
        raise OllamaTimeoutError(msg) from exc

    except (OllamaConnectionError, OllamaModelNotFoundError, OllamaTimeoutError, OllamaGenerationError):
        raise

    except Exception as exc:
        msg = f"Unexpected error while communicating with Ollama: {exc}"
        logger.error(msg)
        raise OllamaGenerationError(msg) from exc

