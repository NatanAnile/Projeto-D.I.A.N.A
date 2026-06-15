# -*- coding: utf-8 -*-

# =========================
# 🛡️ INPUT FIREWALL — STT SANITY
# =========================

"""Triagem leve antes do LLM.

O objetivo não é entender tudo; é impedir que lixo óbvio do STT vire prompt.
Este módulo só corrige intenções de alta confiança e bloqueia alucinações comuns.
"""

import re
import unicodedata
from difflib import SequenceMatcher

from runtime.runtime_types import InputPacket


def normalize_text(text):
    text = str(text or "").lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    text = re.sub(r"[^a-z0-9_%+\- /]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


class InputFirewall:
    """Firewall de entrada para voz/texto antes dos gates de diálogo."""

    MICRO_PING_EXACT = {
        "ai", "ei", "opa", "oi", "hm", "hmm", "uhum", "aham", "fala",
        "e ai", "eai", "eae", "eaí", "e aí",
    }

    # Frases típicas de alucinação/encerramento que STT costuma cuspir quando pega lixo.
    STT_HALLUCINATION_PATTERNS = [
        r"^muito obrigado\s*(pra|para)?\s*(gente|assistir|assistirem)?$",
        r"^obrigado\s+(por|pela)\s+(assistir|legenda|atencao)",
        r"^legendas?\s+(pela|por)\s+",
        r"^inscreva se no canal$",
        r"^ate a proxima$",
        r"^tchau tchau$",
    ]

    # Correções determinísticas de variantes recorrentes do STT.
    PHRASE_CORRECTIONS = {
        "manga um piada": "manda uma piada",
        "manga uma piada": "manda uma piada",
        "manga piada": "manda piada",
        "mando uma piada": "manda uma piada",
        "mando um piada": "manda uma piada",
        "manda um piada": "manda uma piada",
        "manda uma piada pra gente": "manda uma piada pra gente",
        "conta um piada": "conta uma piada",
        "conta piada": "conta uma piada",
    }

    COMMAND_CANONICALS = {
        "request_joke": [
            "manda uma piada",
            "conta uma piada",
            "faz uma piada",
            "solta uma piada",
            "faz um trocadilho",
            "manda um trocadilho",
        ],
    }

    def analyze(self, text, source="OWNER_TEXT"):
        raw_text = str(text or "").strip()
        source = str(source or "OWNER_TEXT").upper().strip()
        normalized = normalize_text(raw_text)

        if not normalized:
            return InputPacket(
                raw_text=raw_text,
                text=raw_text,
                source=source,
                quality="BLOCKED",
                allow_llm=False,
                allow_memory=False,
                allow_retrieval=False,
                direct_response="Não peguei nada útil aqui, Neitan.",
                reason="entrada vazia após normalização",
            )

        # Comandos internos digitados continuam intactos.
        if normalized.startswith("/") or raw_text.startswith("/"):
            return InputPacket(raw_text=raw_text, text=raw_text, source=source, reason="comando interno liberado")

        if normalized in self.MICRO_PING_EXACT:
            return InputPacket(
                raw_text=raw_text,
                text=normalized,
                corrected_text=normalized,
                source=source,
                quality="MICRO",
                intent_hint="micro_ping",
                allow_llm=False,
                allow_memory=False,
                allow_retrieval=False,
                reason="microentrada/backchannel curto",
            )

        if source.endswith("STT") and self._looks_like_stt_hallucination(normalized):
            return InputPacket(
                raw_text=raw_text,
                text=raw_text,
                source=source,
                quality="BLOCKED",
                intent_hint="stt_repeat",
                allow_llm=False,
                allow_memory=False,
                allow_retrieval=False,
                direct_response="Não peguei direito. O STT cuspiu cara de encerramento de vídeo, então repete essa com carinho técnico.",
                reason="alucinação comum de STT bloqueada",
            )

        corrected = self.PHRASE_CORRECTIONS.get(normalized, "")
        if corrected:
            return InputPacket(
                raw_text=raw_text,
                text=corrected,
                corrected_text=corrected,
                source=source,
                quality="RECOVERED",
                intent_hint=self._intent_for_text(corrected) or "",
                allow_llm=False if self._intent_for_text(corrected) in {"request_joke"} else True,
                allow_memory=False,
                allow_retrieval=False,
                reason="correção determinística de variante STT",
            )

        fuzzy_intent, fuzzy_text, score = self._fuzzy_command(normalized)
        if source.endswith("STT") and fuzzy_intent and score >= 0.83:
            return InputPacket(
                raw_text=raw_text,
                text=fuzzy_text,
                corrected_text=fuzzy_text,
                source=source,
                quality="RECOVERED",
                intent_hint=fuzzy_intent,
                allow_llm=False,
                allow_memory=False,
                allow_retrieval=False,
                reason=f"comando STT recuperado por similaridade {score:.2f}",
                metadata={"score": f"{score:.2f}"},
            )

        # Entrada curtíssima via STT, sem intenção reconhecida, não merece LLM.
        if source.endswith("STT") and len(normalized) <= 3:
            return InputPacket(
                raw_text=raw_text,
                text=normalized,
                corrected_text=normalized,
                source=source,
                quality="SUSPECT",
                intent_hint="micro_ping",
                allow_llm=False,
                allow_memory=False,
                allow_retrieval=False,
                reason="entrada STT curta demais; tratada como microentrada",
            )

        return InputPacket(
            raw_text=raw_text,
            text=raw_text,
            source=source,
            quality="OK",
            intent_hint=self._intent_for_text(normalized),
            allow_llm=True,
            allow_memory=True,
            allow_retrieval=True,
            reason="entrada aprovada",
        )

    def _looks_like_stt_hallucination(self, normalized):
        return any(re.search(pattern, normalized) for pattern in self.STT_HALLUCINATION_PATTERNS)

    def _intent_for_text(self, normalized):
        if re.search(r"\b(piada|piadas|piadoca|trocadilho|humor)\b", normalized) and re.search(r"\b(manda|mando|manga|conta|conte|faz|solta|me conta|me conte)\b", normalized):
            return "request_joke"
        if normalized in self.MICRO_PING_EXACT:
            return "micro_ping"
        return ""

    def _fuzzy_command(self, normalized):
        best_intent = ""
        best_text = ""
        best_score = 0.0

        for intent, phrases in self.COMMAND_CANONICALS.items():
            for phrase in phrases:
                score = SequenceMatcher(None, normalized, phrase).ratio()
                if score > best_score:
                    best_intent = intent
                    best_text = phrase
                    best_score = score

        return best_intent, best_text, best_score
