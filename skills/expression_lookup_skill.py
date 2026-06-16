# -*- coding: utf-8 -*-

# =========================
# 📚 EXPRESSION LOOKUP SKILL
# =========================

import re
import unicodedata

from personality.expression_rules import EXPRESSION_RULES
from skills.base_skill import BaseSkill, SkillContext


def _normalize(text):
    text = str(text or "").lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^a-z0-9_ ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


class ExpressionLookupSkill(BaseSkill):

    def __init__(self):
        context = SkillContext(
            skill_name="ExpressionLookupSkill",
            min_cooldown=0,
            max_cooldown=0,
        )
        super().__init__(context)
        self.index = {_normalize(key): key for key in EXPRESSION_RULES.keys()}

    def extrair_termo(self, user_text):
        text = str(user_text or "").strip()
        patterns = [
            r"o\s+que\s+significa\s+(.+)$",
            r"oque\s+significa\s+(.+)$",
            r"que\s+significa\s+(.+)$",
            r"significado\s+de\s+(.+)$",
            r"o\s+que\s+quer\s+dizer\s+(.+)$",
        ]
        lower = text.lower().strip()
        for pattern in patterns:
            match = re.search(pattern, lower, flags=re.IGNORECASE)
            if match:
                termo = match.group(1).strip()
                termo = re.split(r"[?.!,;:]", termo, maxsplit=1)[0].strip()
                termo = termo.strip(" '\"`“”‘’")
                return termo
        return ""

    def get_direct_response(self, user_text="", conversation=None, force=False):
        termo = self.extrair_termo(user_text)
        if not termo:
            return None

        norm = _normalize(termo)
        chave = self.index.get(norm)

        if not chave:
            print("🧩 Skill direta ativada: ExpressionLookupSkill -> não encontrado")
            return f"Não tenho '{termo}' no meu dicionário de expressões ainda. Não vou inventar significado no fundo da gaveta."

        data = EXPRESSION_RULES.get(chave, {})
        significado = str(data.get("significado", "")).strip()
        exemplos = data.get("exemplos", []) or []

        print("🧩 Skill direta ativada: ExpressionLookupSkill -> " + chave)

        resposta = f"{chave} significa {significado}."
        if exemplos:
            resposta += " Exemplo: " + str(exemplos[0]).strip()
        return resposta
