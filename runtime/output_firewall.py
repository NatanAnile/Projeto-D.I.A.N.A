# -*- coding: utf-8 -*-

# =========================
# 🧯 OUTPUT FIREWALL — PERSONA / CTA TRIM
# =========================

import re

from brain.identity_guard import enforce_diana_identity


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
        result = self._sanitize_file_paths(result)
        result = enforce_diana_identity(result)
        result = self._strip_verbal_tics(result)
        result = self._strip_emojis(result)
        result = self._trim_trailing_cta(result)
        return result.strip()

    def _sanitize_file_paths(self, text):
        """Remove diretórios completos da fala final.

        Skills podem usar caminho absoluto em log/debug, mas a Diana nunca deve
        falar caminhos completos do Windows/Linux para o usuário. Mantém só o nome do
        arquivo quando houver extensão.
        """

        text = str(text or "")

        windows_path = re.compile(
            r"[A-Za-z]:\\(?:[^\\/:*?\"<>|\r\n]+\\)*([^\\/:*?\"<>|\r\n]+\.[A-Za-z0-9_]+)"
        )
        linux_path = re.compile(
            r"(?:/[A-Za-z0-9_.+\- ]+)+/([A-Za-z0-9_.+\-]+\.[A-Za-z0-9_]+)"
        )

        text = windows_path.sub(r"\1", text)
        text = linux_path.sub(r"\1", text)

        return text



    def _strip_emojis(self, text):
        # Sem emoji na fala final da Diana. Mantém texto puro para chat/TTS.
        return re.sub(
            "["
            "\U0001F300-\U0001F5FF"
            "\U0001F600-\U0001F64F"
            "\U0001F680-\U0001F6FF"
            "\U0001F700-\U0001F77F"
            "\U0001F780-\U0001F7FF"
            "\U0001F800-\U0001F8FF"
            "\U0001F900-\U0001F9FF"
            "\U0001FA00-\U0001FA6F"
            "\U0001FA70-\U0001FAFF"
            "\u2600-\u27BF"
            "]+",
            "",
            str(text or ""),
        ).strip()

    def _strip_verbal_tics(self, text):
        text = str(text or "").strip()
        # Remove muleta repetitiva no começo sem podar o deboche.
        text = re.sub(r"^(vem\s+c[aá],?\s*)", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"^(olha\s+s[oó],?\s*)", "", text, flags=re.IGNORECASE).strip()
        # Evita uma piada arriscada de live quando o pedido era só executar skill.
        text = re.sub(r"\bgarota\s+de\s+programa\b", "funcionária pública do caos", text, flags=re.IGNORECASE)
        return text

    def _trim_trailing_cta(self, text):
        """Remove CTA genérico automático do final da resposta.

        Conservador: só poda se a última frase for CTA puro sem conteúdo de
        personagem. Não poda se tiver deboche, ironia ou referência de persona
        (palavras como 'caos', 'goblin', 'patifaria', 'gambiarra' etc).
        """
        text = str(text or "").strip()
        if not text:
            return text

        parts = re.split(r"(?<=[.!?])\s+", text)
        if len(parts) <= 1:
            return text

        last = parts[-1].strip()
        last_norm = last.lower()

        # Não poda se tiver marcadores de personagem — provavelmente é deboche intencional.
        persona_markers = [
            "caos", "goblin", "patifaria", "gambiarra", "fuleiro", "bagunc",
            "zureta", "trocadilho", "piada", "deboch", "travess", "teimos"
        ]
        if any(m in last_norm for m in persona_markers):
            return text

        if any(re.search(pattern, last_norm) for pattern in self.CTA_PATTERNS):
            return " ".join(parts[:-1]).strip()
        return text
