# -*- coding: utf-8 -*-

# =========================
# 🧼 STT POSTPROCESSOR
# =========================

import json
import re
from pathlib import Path


def _replace_word(text, wrong, right, flags=re.IGNORECASE):
    return re.sub(r"(?<!\w)" + re.escape(wrong) + r"(?!\w)", right, text, flags=flags)


_CUSTOM_VARIANTS_CACHE = None


def _load_custom_variants():

    global _CUSTOM_VARIANTS_CACHE

    if _CUSTOM_VARIANTS_CACHE is not None:
        return _CUSTOM_VARIANTS_CACHE

    path = Path(__file__).with_name("stt_custom_variants.json")
    variants = {}

    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            raw = data.get("replacements", {})
            if isinstance(raw, dict):
                variants = {str(k): str(v) for k, v in raw.items() if str(k).strip() and str(v).strip()}
        except Exception as e:
            print("⚠️ STT custom variants ignorado por erro:", e)

    _CUSTOM_VARIANTS_CACHE = variants
    return variants


def postprocess_stt_text(text):

    text = str(text or "").strip()

    if not text:
        return ""

    text = re.sub(r"\s+", " ", text).strip()

    # Vocativos/nomes comuns que o STT costuma distorcer.
    replacements = {
        "taquinha": "Diana",
        "diana": "Diana",
        "diana": "Diana",
        "tasca": "Diana",
        "tasquihna": "Diana",
        "pasquinha": "Diana",
        "tascuinha": "Diana",
        "neiton": "Neitan",
        "neitão": "Neitan",
        "naiton": "Neitan",
        "nathan": "Natan",
        "natan anile": "Natan Anile",
        "allen": "Alien",
        "alen": "Alien",
        "motola": "Motorola",
        "motorola": "Motorola",
        "uol jump": "wall jump",
        "uou jump": "wall jump",
        "uol jampe": "wall jump",
        "shainisparque": "shinespark",
        "xainisparque": "shinespark",
        "ranndomaiser": "randomizer",
        "randomaiser": "randomizer",
        "spidran": "speedrun",
        "mocobol": "mockball",
        "tasquigna": "Diana",
        "tazquinha": "Diana",
        "naitam": "Neitan",
        "ual jump": "wall jump",
        "chaine spark": "shinespark",
        "rendomizer": "randomizer",
        "spid ham": "speedrun",
        "mok bol": "mockball",
        "grappling bram": "grappling beam",
        "grapple bram": "grapple beam",
        "x rei climb": "X-Ray Climb",
        "cristal fléshi": "Crystal Flash",
        "cristal fleshi": "Crystal Flash",
        "snes nove xis": "Snes9x",
    }

    replacements.update(_load_custom_variants())

    for wrong, right in replacements.items():
        text = _replace_word(text, wrong, right)

    # Vocativo torto no começo da fala. Melhor remover do que contaminar intenção.
    text = re.sub(r"^\s*(moley|molly|molei|moli|mole)\s*,\s*", "", text, flags=re.IGNORECASE)

    # Correções de contexto para Alien/Aliens.
    if re.search(r"\balien\b", text, flags=re.IGNORECASE):
        text = re.sub(r"\b(o\s+)?esgate\b", "O Resgate", text, flags=re.IGNORECASE)
        text = re.sub(r"\bAlien\s*2\s*,\s*o\s+O\s+Resgate\b", "Alien 2, O Resgate", text, flags=re.IGNORECASE)
        text = re.sub(r"\bAlien\s*2\s*,\s*O\s+Resgate\b", "Alien 2, O Resgate", text, flags=re.IGNORECASE)
        text = re.sub(r"\bAliens?\s*,\s*O\s+Resgate\b", "Aliens: O Resgate", text, flags=re.IGNORECASE)

    text = re.sub(r"\s+([,.!?;:])", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text
