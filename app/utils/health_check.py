"""Lightweight health checks for Ollama-backed models.

Provides:
- ping(model, text): ask model to echo `text`; True if it does.
- readiness(): check configured models and return booleans per model, plus 'ready'.

Timeouts are short to avoid blocking; all exceptions resolve to False.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from typing import Any, Dict
import json
import os
from urllib import request, error as urlerror

try:  # Lazy/defensive import: allow running without ollama installed
    import ollama  # type: ignore
except Exception:  # ImportError or runtime errors
    ollama = None  # type: ignore
from app.config import get_config


TIMEOUT_SECONDS = 3


def _ollama_host() -> str:
    return os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")


def _http_post(path: str, payload: Dict[str, Any], timeout: float) -> Dict[str, Any] | None:
    try:
        url = _ollama_host().rstrip("/") + path
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        with request.urlopen(req, timeout=timeout) as resp:  # nosec - local service
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except (urlerror.URLError, json.JSONDecodeError, ValueError, TimeoutError, Exception):
        return None


def _generate_with_timeout(model: str, prompt: str, timeout: float) -> Dict[str, Any] | None:
    """Call ollama.generate with a hard timeout; return response dict or None."""
    if ollama is not None:
        try:
            with ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(ollama.generate, model=model, prompt=prompt)
                return fut.result(timeout=timeout)
        except FuturesTimeout:
            return None
        except Exception:
            return None
    # Fallback to HTTP API
    return _http_post("/api/generate", {"model": model, "prompt": prompt, "stream": False}, timeout)


def _embed_with_timeout(model: str, text: str, timeout: float) -> Dict[str, Any] | None:
    """Call ollama.embeddings with a hard timeout; return response dict or None."""
    if ollama is not None:
        try:
            with ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(ollama.embeddings, model=model, prompt=text)
                return fut.result(timeout=timeout)
        except FuturesTimeout:
            return None
        except Exception:
            return None
    # Fallback to HTTP API
    return _http_post("/api/embeddings", {"model": model, "prompt": text}, timeout)


def ping(model: str, text: str) -> bool:
    """Return True if the model replies with `text` in its response.

    For embedding models (name contains 'embed'), we attempt an embedding call and
    consider it healthy if it returns a vector successfully.
    """
    name = model.lower()
    try:
        if "embed" in name:
            resp = _embed_with_timeout(model, text, TIMEOUT_SECONDS)
            if not isinstance(resp, dict):
                return False
            vec = resp.get("embedding")
            return isinstance(vec, list) and len(vec) > 0

        # Instruct LLMs to echo the token exactly
        prompt = f"Reply with exactly this token and nothing else: {text}"
        resp = _generate_with_timeout(model, prompt, TIMEOUT_SECONDS)
        if not isinstance(resp, dict):
            return False
        content = resp.get("response") or (
            (resp.get("message") or {}).get("content")
        ) or ""
        return isinstance(content, str) and (text in content)
    except Exception:
        return False


def readiness() -> Dict[str, Any]:
    """Ping all configured models and return individual results plus overall flag.

    Returns a dict with keys equal to the concrete model names and a 'ready' key.
    Example: { 'qwen3:0.6b': True, '...': False, 'ready': False }
    """
    cfg = get_config()
    synth = cfg.get("synthesizer_model")
    judge_fast = cfg.get("judge_model_fast")
    judge_backup = cfg.get("judge_model_backup")
    embed = cfg.get("embed_model")

    results: Dict[str, bool] = {}

    for model, token in (
        (synth, "SYNTH-OK"),
        (judge_fast, "JUDGE-OK"),
        (judge_backup, "JUDGE2-OK"),
        (embed, "EMBED-OK"),
    ):
        if isinstance(model, str) and model:
            results[model] = ping(model, token)
        else:
            results[str(model)] = False

    ready_flag = all(results.values()) if results else False
    report: Dict[str, Any] = {**results, "ready": ready_flag}
    return report
