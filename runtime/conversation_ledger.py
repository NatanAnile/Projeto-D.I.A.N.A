# -*- coding: utf-8 -*-

# =========================
# 📜 DIANA CONVERSATION LEDGER
# =========================

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import time


@dataclass
class ConversationTurn:
    turn_id: int
    user_text: str
    assistant_text: str
    source_role: str = "OWNER"
    source_name: str = "Natan"
    raw_user_text: str = ""
    corrected_user_text: str = ""
    dialogue_act: str = "normal"
    dialogue_target: str = "OWNER"
    response_origin: str = "unknown"
    used_llm: bool = False
    used_retrieval: bool = False
    used_memory: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "turn_id": self.turn_id,
            "user": self.user_text,
            "assistant": self.assistant_text,
            "source_role": self.source_role,
            "source_name": self.source_name,
            "raw_user_text": self.raw_user_text,
            "corrected_user_text": self.corrected_user_text,
            "dialogue_act": self.dialogue_act,
            "dialogue_target": self.dialogue_target,
            "response_origin": self.response_origin,
            "used_llm": self.used_llm,
            "used_retrieval": self.used_retrieval,
            "used_memory": self.used_memory,
            "metadata": dict(self.metadata or {}),
            "timestamp": self.timestamp,
        }


class ConversationLedger:
    """Fonte de verdade literal da conversa visível para a Diana.

    Tudo que foi dito ao usuário deve passar por aqui: resposta do LLM,
    resposta direta, joke_bank, retrieval determinístico, firewall, skill etc.
    O histórico recente que o PromptBuilder injeta deve vir deste ledger.
    """

    def __init__(self, max_turns: int = 5):
        self.history: List[Dict[str, Any]] = []
        self.max_turns = max(1, int(max_turns or 5))
        self._next_turn_id = 1

    def add_turn(
        self,
        user_text: str,
        assistant_text: str,
        source_role: str = "OWNER",
        source_name: str = "Natan",
        turn_context: Optional[Dict[str, Any]] = None,
        **extra: Any,
    ) -> ConversationTurn:
        turn_context = turn_context or {}
        metadata = dict(extra or {})
        metadata.update({
            "quality": turn_context.get("input_quality", turn_context.get("quality", "")),
            "intent_hint": turn_context.get("intent_hint", ""),
            "retrieval_status": turn_context.get("retrieval_status", ""),
        })

        turn = ConversationTurn(
            turn_id=self._next_turn_id,
            user_text=str(user_text or "").strip(),
            assistant_text=str(assistant_text or "").strip(),
            source_role=str(turn_context.get("source", source_role or "OWNER")).upper().strip(),
            source_name=str(turn_context.get("source_name", source_name or "Natan")).strip(),
            raw_user_text=str(turn_context.get("raw_text", turn_context.get("input_raw_text", user_text)) or "").strip(),
            corrected_user_text=str(turn_context.get("corrected_text", turn_context.get("input_corrected_text", user_text)) or "").strip(),
            dialogue_act=str(turn_context.get("dialogue_act", "normal") or "normal"),
            dialogue_target=str(turn_context.get("dialogue_target", "OWNER") or "OWNER"),
            response_origin=str(turn_context.get("response_origin", "unknown") or "unknown"),
            used_llm=bool(turn_context.get("used_llm", False)),
            used_retrieval=bool(turn_context.get("used_retrieval", False)),
            used_memory=bool(turn_context.get("used_memory", False)),
            metadata=metadata,
        )
        self._next_turn_id += 1

        self.history.append(turn.to_dict())
        if len(self.history) > self.max_turns:
            self.history.pop(0)
        return turn

    def get_context(self) -> str:
        if not self.history:
            return ""

        lines = [
            "# HISTÓRICO LITERAL RECENTE — FONTE DE VERDADE DA CONVERSA",
            "Este bloco contém somente turnos realmente entregues ao usuário.",
            "Ele tem prioridade sobre resumo auxiliar e exemplos de estilo.",
        ]

        for turn in self.history:
            source_role = turn.get("source_role", "OWNER")
            source_name = turn.get("source_name", "Natan")
            origin = turn.get("response_origin", "unknown")
            act = turn.get("dialogue_act", "normal")
            used_llm = "sim" if turn.get("used_llm") else "não"
            used_retrieval = "sim" if turn.get("used_retrieval") else "não"
            lines.append(
                f"Turno #{turn.get('turn_id')} | Fonte: {source_role} | Nome: {source_name} | "
                f"act={act} | origem={origin} | llm={used_llm} | retrieval={used_retrieval}"
            )
            raw_text = str(turn.get("raw_user_text", "") or "").strip()
            corrected_text = str(turn.get("corrected_user_text", "") or "").strip()
            user_text = str(turn.get("user", "") or "").strip()
            if raw_text and corrected_text and raw_text != corrected_text:
                lines.append(f"{source_name} bruto: {raw_text}")
                lines.append(f"{source_name} corrigido: {corrected_text}")
            else:
                lines.append(f"{source_name}: {user_text}")
            lines.append(f"Diana: {turn.get('assistant', '')}")
            lines.append("")

        return "\n".join(lines).strip()

    def last_assistant_text(self) -> str:
        if not self.history:
            return ""
        return str(self.history[-1].get("assistant", "") or "")

    def clear(self) -> None:
        self.history = []
        self._next_turn_id = 1


# Compatibilidade com testes/código antigo.
ConversationHistory = ConversationLedger
