# -*- coding: utf-8 -*-

# =========================
# 🧠 SESSION PREFERENCE RESPONDER
# =========================

import re
import unicodedata


LABELS = {
    "filme_favorito": "filme favorito",
    "comida_favorita": "comida favorita",
    "jogo_favorito": "jogo favorito",
    "serie_favorita": "série favorita",
    "banda_favorita": "banda favorita",
    "franquia_de_jogo_favorito": "franquia de jogo favorita",
    "franquia_de_jogo_favorita": "franquia de jogo favorita",
    "gosta_de": "coisas que você disse gostar",
}

ALIASES = {
    "filme": "filme_favorito",
    "comida": "comida_favorita",
    "jogo": "jogo_favorito",
    "serie": "serie_favorita",
    "série": "serie_favorita",
    "banda": "banda_favorita",
    "franquia": "franquia_de_jogo_favorito",
    "franquia de jogo": "franquia_de_jogo_favorito",
}


def normalize(text):
    text = str(text or "").lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^a-z0-9_ ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


class SessionPreferenceResponder:

    def __init__(self, session_context):
        self.session_context = session_context

    def _prefs(self):
        profile = getattr(self.session_context, "profile", {}) or {}
        current = getattr(self.session_context, "current", {}) or {}
        owner = profile.get("owner", {}) or {}
        base = dict(owner.get("known_preferences", {}) or {})
        session = dict(current.get("owner_session_preferences", {}) or {})
        base.update(session)
        return base

    def _label(self, key):
        return LABELS.get(key, str(key).replace("_", " "))

    def _format_value(self, value):
        if isinstance(value, list):
            return ", ".join(str(v) for v in value if str(v).strip())
        return str(value).strip()

    def _specific_key(self, text):
        norm = normalize(text)

        for alias, key in ALIASES.items():
            if re.search(r"\b" + re.escape(normalize(alias)) + r"\b", norm):
                return key

        match = re.search(r"(?:meu|minha)\s+([a-z0-9_ ]{2,40})\s+favorit", norm)
        if match:
            categoria = match.group(1).strip()
            if categoria in ALIASES:
                return ALIASES[categoria]
            categoria = re.sub(r"\s+", "_", categoria).strip("_")
            return categoria + "_favorito"

        return ""

    def responder(self, user_text):
        prefs = self._prefs()
        norm = normalize(user_text)

        wants_all = bool(re.search(r"\b(todas|todos|lista|quais)\b.*\b(coisas|favorit|preferencias|preferencias)\b", norm))

        if wants_all:
            if not prefs:
                return "Não tenho nenhuma preferência sua salva no contexto de sessão ainda. Ata vazia, caos em branco."

            partes = []
            for key in sorted(prefs.keys()):
                value = self._format_value(prefs[key])
                if value:
                    partes.append(f"{self._label(key)}: {value}")

            if not partes:
                return "Tenho o campo de preferências, mas ele está vazio. Organização digna de gaveta de cabo velho."

            return "Suas preferências salvas são: " + "; ".join(partes) + "."

        key = self._specific_key(user_text)
        if not key:
            return "Se for preferência sua, me dá a categoria direito. Minha bola de cristal está em manutenção preventiva."

        value = prefs.get(key)
        if value is None:
            # tenta compat simples favorito/favorita
            if key.endswith("_favorito"):
                value = prefs.get(key[:-1] + "a")
            elif key.endswith("_favorita"):
                value = prefs.get(key[:-1] + "o")

        value = self._format_value(value)
        if value:
            return f"Preferência salva — {self._label(key)}: {value}."

        return f"Ainda não tenho seu {self._label(key)} salvo no contexto de sessão. Não vou sortear preferência no bingo da mentira."
