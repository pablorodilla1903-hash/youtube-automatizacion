"""Cliente de IA gratuito: Google Gemini (AI Studio, sin tarjeta) con Groq de respaldo."""
from __future__ import annotations

import json
import os
import re

import requests

from .util import log

GEMINI_MODELS = [
    m.strip()
    for m in os.environ.get("GEMINI_MODELS", "gemini-2.5-flash,gemini-2.5-flash-lite").split(",")
    if m.strip()
]
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")


def _parse_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


def _gemini(prompt: str, model: str, key: str) -> dict:
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
        json={
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.9,
                "responseMimeType": "application/json",
                "maxOutputTokens": 16384,
            },
        },
        timeout=240,
    )
    r.raise_for_status()
    data = r.json()
    parts = data["candidates"][0]["content"]["parts"]
    return _parse_json("".join(p.get("text", "") for p in parts))


def _groq(prompt: str, key: str) -> dict:
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={
            "model": GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.9,
            "response_format": {"type": "json_object"},
            "max_tokens": 8000,
        },
        timeout=240,
    )
    r.raise_for_status()
    return _parse_json(r.json()["choices"][0]["message"]["content"])


def available() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GROQ_API_KEY"))


def generate_json(prompt: str, validate=None) -> dict:
    """Pide JSON a la IA probando proveedores en orden hasta obtener uno válido."""
    attempts = []
    if key := os.environ.get("GEMINI_API_KEY"):
        attempts += [(f"Gemini {m}", lambda m=m: _gemini(prompt, m, key)) for m in GEMINI_MODELS]
    if key := os.environ.get("GROQ_API_KEY"):
        attempts.append((f"Groq {GROQ_MODEL}", lambda: _groq(prompt, key)))
    if not attempts:
        raise RuntimeError("Falta GEMINI_API_KEY (o GROQ_API_KEY) en los secretos")

    errors = []
    for name, fn in attempts:
        for _ in range(2):
            try:
                out = fn()
                if validate:
                    validate(out)
                log(f"  IA: respuesta válida de {name}")
                return out
            except Exception as e:  # noqa: BLE001
                errors.append(f"{name}: {e}")
                log(f"  ⚠ {name}: {str(e)[:300]}")
    raise RuntimeError("Ningún proveedor de IA respondió bien:\n" + "\n".join(errors))
