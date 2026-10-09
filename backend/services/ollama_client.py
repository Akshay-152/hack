"""Ollama integration (spec section 8).

Backend-only calls to the local Ollama API. Model and endpoint are
configurable. Every function returns (result, error) and never raises;
the app stays fully functional when Ollama is stopped. Passwords or
other auth data are never sent to the model.
"""
from __future__ import annotations

import json
import os

import requests
from flask import current_app

DEFAULT_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")
DEFAULT_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "90"))

_client_state: dict = {"model": None, "host": None}


def _settings() -> tuple[str, str]:
    try:
        host = current_app.config.get("OLLAMA_HOST") or DEFAULT_HOST
        model = current_app.config.get("OLLAMA_MODEL") or DEFAULT_MODEL
    except RuntimeError:  # outside app context
        host, model = DEFAULT_HOST, DEFAULT_MODEL
    return host.rstrip("/"), model


def check_available(timeout: int = 5) -> tuple[bool, str]:
    """Ping Ollama and verify the model tag exists. Returns (ok, message)."""
    host, model = _settings()
    try:
        res = requests.get(f"{host}/api/tags", timeout=timeout)
        res.raise_for_status()
    except requests.RequestException as exc:
        return False, f"Ollama unreachable at {host}"
    try:
        models = [m.get("name", "") for m in res.json().get("models", [])]
    except ValueError:
        return False, "Ollama returned an invalid response"
    base = model.split(":")[0]
    if model not in models and not any(m.startswith(base + ":") for m in models):
        return False, f"model {model} not available in Ollama"
    return True, model


def chat(messages: list[dict], timeout: int | None = None) -> tuple[str, str]:
    """Call /api/chat. Returns (text, error) — exactly one is non-empty."""
    host, model = _settings()
    payload = {"model": model, "messages": messages, "stream": False}
    try:
        res = requests.post(f"{host}/api/chat", json=payload,
                            timeout=timeout or DEFAULT_TIMEOUT)
        res.raise_for_status()
        data = res.json()
        text = (data.get("message") or {}).get("content", "").strip()
        if not text:
            return "", "empty response from model"
        return text, ""
    except requests.Timeout:
        return "", "AI request timed out"
    except requests.RequestException:
        return "", "AI service unavailable"
    except ValueError:
        return "", "AI returned an invalid response"
