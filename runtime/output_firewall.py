# -*- coding: utf-8 -*-

# =========================
# 🧯 OUTPUT FIREWALL — PERSONA / CTA TRIM
# =========================

import re


class OutputFirewall:
    """Filtro final de persona.

    Não poda o teatro da Diana. Só corrige dois vazamentos:
    1. diminutivos/apelidos proibidos do nome do usuário;
    2. call-to-action genérico no final da resposta, quando parece automático.
    """

    NAME_REPLACEMENTS = {
        r"\bNatanzinho\b": "Natan",
        r"\bNatan-zinho\b": "Natan",
        r"\bNataninho\b": "Natan",
        r"\bNeitanzinho\b": "Neitan",
        r"\bNeitan-zinho\b": "Neitan",
        r"\bNeitinho\b": "Neitan",
    }

    CTA_PATTERNS = [
        r"^(se\s+quiser|se\s+você\s+quiser|se\s+voce\s+quiser)\b",
        r"^(quer\s+que\s+eu|quer\s+que)\b",
        r"^(posso\s+te|posso\s+fazer|posso\s+explicar)\b",
        r"^(vem\s+com|manda\s+uma\s+ideia|me\s+diz)\b",
        r"^(vamos\s+conversar|vamos\s+falar)\b",
    ]

    def clean(self, text):
        result = str(text or "")
        for pattern, replacement in self.NAME_REPLACEMENTS.items():
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        result = self._strip_verbal_tics(result)
        result = self._trim_trailing_cta(result)
        return result.strip()


    def _strip_verbal_tics(self, text):
        text = str(text or "").strip()
        # Remove muleta repetitiva no começo sem podar o deboche.
        text = re.sub(r"^(vem\s+c[aá],?\s*)", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"^(olha\s+s[oó],?\s*)", "", text, flags=re.IGNORECASE).strip()
        # Evita uma piada arriscada de live quando o pedido era só executar skill.
        text = re.sub(r"\bgarota\s+de\s+programa\b", "funcionária pública do caos", text, flags=re.IGNORECASE)
        return text

    def _trim_trailing_cta(self, text):
        text = str(text or "").strip()
        if not text:
            return text

        parts = re.split(r"(?<=[.!?])\s+", text)
        if len(parts) <= 1:
            return text

        last = parts[-1].strip()
        last_norm = last.lower()
        if any(re.search(pattern, last_norm) for pattern in self.CTA_PATTERNS):
            return " ".join(parts[:-1]).strip()
        return text
