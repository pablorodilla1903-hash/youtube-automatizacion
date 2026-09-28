"""Elección de tema y guion completo (título, descripción, tags, segmentos, Short)."""
from __future__ import annotations

import json
from pathlib import Path

from . import llm
from .util import log

LANG_NAME = {"es": "Spanish (neutral Latin American Spanish, understandable in Spain too)", "en": "English (US)"}


def history_path(channel_id: str) -> Path:
    return Path("data/historial") / f"{channel_id}.json"


def load_history(channel_id: str) -> list[dict]:
    p = history_path(channel_id)
    return json.loads(p.read_text("utf-8")) if p.exists() else []


def save_history(channel_id: str, history: list[dict]) -> None:
    p = history_path(channel_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(history, ensure_ascii=False, indent=2), "utf-8")


def next_queued_topic(channel_id: str, history: list[dict]) -> str | None:
    p = Path("config") / f"temas_{channel_id}.txt"
    if not p.exists():
        return None
    used = {h.get("topic", "").strip().lower() for h in history}
    for line in p.read_text("utf-8").splitlines():
        t = line.strip()
        if t and not t.startswith("#") and t.lower() not in used:
            return t
    return None


def _prompt(cfg: dict, history: list[dict], forced_topic: str | None) -> str:
    lang = LANG_NAME[cfg["idioma"]]
    past = "\n".join(f"- {h['title']}" for h in history[-120:]) or "(none yet)"
    words = int(cfg["palabras_video"])
    pillars = "\n".join(f"- {p}" for p in cfg["pilares"])
    topic_block = (
        f'The topic is FIXED by the channel owner: "{forced_topic}". Write about exactly that.'
        if forced_topic
        else f"""Choose ONE fresh topic yourself, rotating between these content pillars:
{pillars}
Pick a topic with proven search demand and curiosity (famous brands, famous people, shocking numbers,
events people already search for). It must NOT repeat or closely resemble any past video below."""
    )
    short_block = (
        """
  "short": {
    "title": "YouTube Shorts title, max 60 chars, ends with #shorts",
    "description": "2 lines + 3 hashtags",
    "segments": [ {"text": "...", "broll": ["...", "..."]} ]
  },"""
        if cfg.get("short")
        else ""
    )
    return f"""You are the head writer of the faceless YouTube channel "{cfg['nombre']}".
Niche: {cfg['nicho'].strip()}
Target audience: {cfg['publico']}
Output language for ALL viewer-facing text: {lang}.

{topic_block}

Past videos (do not repeat):
{past}

Write a complete long-form video package. Rules for the narration script:
- About {words} words in total (this is critical: ~{words // 150} minutes of voice-over).
- First 2 sentences = a brutal hook that promises a payoff and creates curiosity (no greetings, no "welcome back", no channel name).
- Storytelling structure: hook → context → rising tension → twists with concrete facts, names, dates and numbers → payoff → one-line lesson.
- Open loops ("but that was not the worst part...") every ~60 seconds to keep retention high.
- Short, spoken sentences. Written to be read aloud by a text-to-speech voice: no emojis, no headings,
  no stage directions, no brackets, spell out symbols (write "percent", "dollars", "million" in the output language).
- Only use well-documented, verifiable facts. If unsure of an exact figure, round it and say "around"/"about". Never invent quotes.
- Near the middle, one natural line inviting viewers to subscribe (one sentence, not salesy).
- End with a question to the viewers to drive comments.
- Split the script into 14-22 segments of 50-110 words. For each segment give 2 stock-footage search queries
  IN ENGLISH (2-4 concrete visual words each, e.g. "stock market crash screen", "empty shopping mall"),
  describing generic footage that exists on Pexels (no brand names, no specific people).

Also write a separate vertical YouTube Short (if requested below) of 110-140 words: one surprising fact from the same
story, hook in the first 5 words, ending with a line that invites viewers to watch the full video on the channel.

Return ONLY valid JSON with this exact structure:
{{
  "topic": "short description of the chosen topic",
  "title": "click-worthy but honest title, max 65 characters, curiosity + specific entity/number",
  "alt_titles": ["two alternative titles for A/B testing", "..."],
  "thumbnail_text": "2 to 4 punchy words for the thumbnail (different from the title)",
  "thumbnail_highlight": "the single word from thumbnail_text to highlight in color",
  "description": "SEO description: first 2 lines hook with main keywords, then a 4-6 line summary, then 5 chapter-like bullet points without timestamps",
  "tags": ["15 to 25 SEO tags mixing broad and long-tail keywords"],
  "hashtags": ["#three", "#relevant", "#hashtags"],
  "pinned_comment": "a comment to pin that sparks discussion",
  "segments": [ {{"text": "narration...", "broll": ["query one", "query two"]}} ],{short_block}
  "sources_to_check": ["key facts the owner should double-check before publishing — WRITE THESE IN SPANISH"]
}}"""


def _validator(cfg: dict):
    min_words = int(cfg["palabras_video"]) * 0.65

    def validate(d: dict) -> None:
        for k in ("title", "description", "tags", "segments", "thumbnail_text"):
            if not d.get(k):
                raise ValueError(f"falta el campo {k}")
        words = sum(len(s.get("text", "").split()) for s in d["segments"])
        if words < min_words:
            raise ValueError(f"guion demasiado corto ({words} palabras)")
        if cfg.get("short") and not (d.get("short") or {}).get("segments"):
            raise ValueError("falta el Short")

    return validate


def written_scripts(channel_id: str, history: list[dict]) -> list[Path]:
    """Guiones ya escritos (guiones/<canal>/*.json) que aún no se han usado, en orden."""
    used = {h.get("script_file") for h in history}
    return [p for p in sorted((Path("guiones") / channel_id).glob("*.json")) if p.name not in used]


def generate_package(channel_id: str, cfg: dict) -> dict:
    history = load_history(channel_id)
    pending = written_scripts(channel_id, history)
    if pending:
        log(f"  Guion ya escrito: {pending[0].name} (quedan {len(pending) - 1} después de este)")
        pkg = json.loads(pending[0].read_text("utf-8"))
        _validator(cfg)(pkg)
        pkg["script_file"] = pending[0].name
        pkg["scripts_left"] = len(pending) - 1
    elif not llm.available():
        raise RuntimeError(
            f"No quedan guiones en guiones/{channel_id}/ y no hay clave de IA configurada. "
            "Pídele a Claude una nueva tanda de guiones."
        )
    else:
        forced = next_queued_topic(channel_id, history)
        if forced:
            log(f"  Tema de la cola manual: {forced}")
        pkg = llm.generate_json(_prompt(cfg, history, forced), validate=_validator(cfg))
        if forced:
            pkg["topic"] = forced
    for seg in pkg["segments"] + (pkg.get("short") or {}).get("segments", []):
        seg["text"] = seg["text"].strip()
        seg["broll"] = [q for q in seg.get("broll", []) if isinstance(q, str) and q.strip()][:3]
    return pkg
