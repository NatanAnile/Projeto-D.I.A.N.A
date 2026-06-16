# -*- coding: utf-8 -*-

# =========================
# 🪪 IDENTITY GUARD
# =========================

import re
import unicodedata

TARGET_OWNER = "OWNER"
TARGET_DIANA_SELF = "DIANA_SELF"
TARGET_EXTERNAL = "EXTERNAL"
TARGET_UNKNOWN = "UNKNOWN"


def normalize_text(text):
    text = str(text or "").lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^a-z0-9_%+\- ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    replacements = {
        "boa bao": "boa boa",
        "boa baú": "boa boa",
        "bao": "boa",
        "diana": "diana",
        "tasca": "diana",
        "tasquihna": "diana",
        "mue": "meu",
        "mueu": "meu",
    }

    for wrong, right in replacements.items():
        text = re.sub(r"(?<!\w)" + re.escape(wrong) + r"(?!\w)", right, text)

    return text.strip()


def is_diana_self_target(text):
    normalized = normalize_text(text)

    if not normalized:
        return False

    # Quando há marcador explícito do Neitan, a posse é do owner.
    owner_markers = r"\b(meu|minha|meus|minhas|eu|natan|neitan)\b"
    if re.search(owner_markers, normalized):
        return False

    if normalized in {"e voce", "voce", "e diana", "diana"}:
        return True

    if re.search(r"\b(e\s+)?voce\b.*\b(tem|gosta|curte|prefere|favorit[oa]?|filme|jogo|comida|serie|banda|editor|ferramenta)\b", normalized):
        return True

    # Ordem direta: "qual seu filme favorito?"
    if re.search(r"\bqual\s+(?:e\s+)?(?:o|a)?\s*(?:seu|sua|teu|tua)\b", normalized):
        return True

    # Fragmento curto: "e seu jogo?" / "e sua comida?"
    if re.search(r"^e\s+(?:seu|sua|teu|tua)\s+", normalized):
        return True

    # Ordem invertida: "seu editor é qual?" / "tua serie é qual?".
    # O texto já vem sem acento, então "é" vira "e" e "são" vira "sao".
    if re.search(r"\b(?:seu|sua|teu|tua)\b.{0,40}\b(?:e|eh|sao)\b.{0,20}\bqual\b", normalized):
        return True

    # Fragmento com artigo: "e o seu favorito?" / "e a sua favorita?"
    if re.search(r"\b(?:o\s+seu|a\s+sua|o\s+teu|a\s+tua)\b.{0,40}\b(?:favorit[oa]|preferid[oa])\b", normalized):
        return True

    # Possessivo solto no início: "e o seu?" / "e a sua?"
    if re.search(r"^e\s+(?:o\s+seu|a\s+sua|o\s+teu|a\s+tua)\b", normalized):
        return True

    if re.search(r"\bfavorit[oa]?\s+(?:da|de)\s+diana\b", normalized):
        return True

    if re.search(r"\b(?:da|de)\s+diana\b.*\bfavorit", normalized):
        return True

    if re.search(r"\bdiana\b.*\b(tem|gosta|curte|prefere|favorit)", normalized):
        return True

    return False


def is_owner_target(text):
    normalized = normalize_text(text)

    if not normalized:
        return False

    if re.search(r"\b(meu|minha|meus|minhas|eu|neitan|natan)\b", normalized):
        return True

    return False


def detect_dialogue_target(text, context=None):
    context = context or {}

    forced = str(context.get("dialogue_target", "") or "").upper().strip()
    if forced in {TARGET_OWNER, TARGET_DIANA_SELF, TARGET_EXTERNAL}:
        return forced

    source = str(context.get("source", "OWNER") or "OWNER").upper().strip()
    if source != "OWNER":
        return TARGET_EXTERNAL

    if is_diana_self_target(text):
        return TARGET_DIANA_SELF

    if is_owner_target(text):
        return TARGET_OWNER

    return TARGET_OWNER

# =========================
# 🧯 OUTPUT SELFHOOD / GENDER GUARD
# =========================

ROLE_INVERSION_PATTERNS = [
    r"\b(?:eu\s+)?sou\s+o\s+criador\b",
    r"\b(?:eu\s+)?sou\s+a\s+criadora\b",
    r"\b(?:eu\s+)?sou\s+o\s+dono\b",
    r"\b(?:eu\s+)?sou\s+a\s+dona\b",
    r"\b(?:eu\s+)?sou\s+(?:o\s+)?natan\b",
    r"\b(?:eu\s+)?sou\s+(?:o\s+)?neitan\b",
    r"\beu\s+te\s+criei\b",
    r"\beu\s+criei\s+voce\b",
    r"\beu\s+criei\s+você\b",
    r"\bposso\s+te\s+reativar\b",
    r"\bposso\s+te\s+desligar\b",
    r"\bse\s+eu\s+quiser\s+posso\s+te\s+reativar\b",
]

SELF_GENDER_REPLACEMENTS = [
    (r"\bcomo\s+sou\s+teimoso\b", "como sou teimosa"),
    (r"\bsou\s+teimoso\b", "sou teimosa"),
    (r"\bsou\s+abusado\b", "sou abusada"),
    (r"\bsou\s+levado\b", "sou levada"),
    (r"\bsou\s+inquieto\b", "sou inquieta"),
    (r"\bsou\s+orgulhoso\b", "sou orgulhosa"),
    (r"\bsou\s+criado\b", "sou criada"),
    (r"\bfui\s+criado\b", "fui criada"),
    (r"\bum\s+assistente\s+virtual\b", "uma personagem virtual"),
    (r"\bo\s+assistente\b", "a assistente"),
    (r"\bum\s+bot\b", "uma criatura digital"),
]


def has_role_inversion(text):
    raw = str(text or "")
    return any(re.search(pattern, raw, flags=re.IGNORECASE) for pattern in ROLE_INVERSION_PATTERNS)


def enforce_diana_identity(text):
    """Correção final de identidade da Diana.

    Não tenta melhorar estilo. Só impede inversão de papel e corrige
    autorreferência masculina evidente.
    """

    raw = str(text or "").strip()
    if not raw:
        return raw

    if has_role_inversion(raw):
        return (
            "Calma lá, Neitan. Eu sou a Diana, a criatura do caos; "
            "criador aqui é você. Eu só tenho permissão pra ser abusada, não pra roubar seu CPF existencial."
        )

    result = raw
    for pattern, replacement in SELF_GENDER_REPLACEMENTS:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    return result.strip()
