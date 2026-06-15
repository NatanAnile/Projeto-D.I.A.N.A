# -*- coding: utf-8 -*-

# =========================
# 📦 TIPOS DO RUNTIME DA DIANA
# =========================

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class InputPacket:
    """Resultado da triagem de entrada antes do cérebro da Diana.

    raw_text: texto original vindo do terminal/STT.
    text: texto que o resto do sistema deve processar.
    corrected_text: texto corrigido quando o firewall recuperou intenção clara.
    source: canal bruto de entrada, por exemplo OWNER_TEXT ou OWNER_STT.
    quality: OK, MICRO, RECOVERED, SUSPECT ou BLOCKED.
    intent_hint: pista opcional para o DialogueActGate.
    allow_llm / allow_memory / allow_retrieval: permissões de segurança do turno.
    direct_response: resposta curta quando a entrada deve ser respondida sem LLM.
    reason: motivo humano para log.
    """

    raw_text: str
    text: str
    corrected_text: str = ""
    source: str = "OWNER_TEXT"
    quality: str = "OK"
    intent_hint: str = ""
    allow_llm: bool = True
    allow_memory: bool = True
    allow_retrieval: bool = True
    direct_response: str = ""
    reason: str = "entrada aprovada"
    metadata: Dict[str, str] = field(default_factory=dict)

    @property
    def changed(self) -> bool:
        return bool(self.corrected_text and self.corrected_text.strip() != self.raw_text.strip())

    def to_turn_context(self):
        return {
            "input_raw_text": self.raw_text,
            "input_text": self.text,
            "input_corrected_text": self.corrected_text,
            "input_source": self.source,
            "input_quality": self.quality,
            "input_intent_hint": self.intent_hint,
            "input_firewall_reason": self.reason,
            "allow_llm": self.allow_llm,
            "allow_memory": self.allow_memory,
            "allow_retrieval": self.allow_retrieval,
        }
