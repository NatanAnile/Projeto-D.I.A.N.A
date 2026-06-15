# -*- coding: utf-8 -*-

# =========================
# 🧭 RETRIEVAL DETERMINÍSTICO
# =========================

from __future__ import annotations

import re
from typing import Any, Dict, Optional


def formatar_resposta_de_campo(entry: Dict[str, Any], field: str, field_data: Dict[str, Any]) -> str:
    nome = str(entry.get("name", "esta entrada")).strip()
    status = str(field_data.get("status", "unknown")).strip()
    value = field_data.get("value")

    if status == "unknown":
        labels = {
            "area": "a área", "room": "a sala", "requirements": "os requisitos",
            "boss": "o chefe necessário", "effect": "o efeito", "uses": "os usos",
            "acquisition": "a forma de aquisição",
        }
        return f"A base ainda não informa {labels.get(field, 'esse campo')} de {nome}, Neitan."

    if status == "none":
        labels = {
            "requirements": "não possui requisitos cadastrados",
            "boss": "não exige derrotar chefe ou miniboss",
            "acquisition": "não possui evento obrigatório de aquisição",
        }
        return f"{nome} {labels.get(field, 'não possui esse requisito')}, Neitan."

    if field == "area":
        room = entry.get("raw", {}).get("room")
        complemento = f", na {room}" if room else ""
        return f"{nome} fica em {value}{complemento}, Neitan."

    if field == "room":
        area = entry.get("raw", {}).get("area")
        complemento = f", em {area}" if area else ""
        return f"{nome} fica na {value}{complemento}, Neitan."

    if field == "boss":
        return f"Para obter {nome} pela progressão normal, você precisa derrotar {value}, Neitan."

    if field == "requirements":
        data = value if isinstance(value, dict) else {}
        parts = []
        if data.get("all_items"):
            parts.append("todos estes itens: " + ", ".join(data.get("all_items") or []))
        if data.get("any_items"):
            parts.append("pelo menos um destes itens: " + ", ".join(data.get("any_items") or []))
        if data.get("minimum_energy_tanks") is not None:
            parts.append(f"pelo menos {data['minimum_energy_tanks']} Energy Tanks")
        if data.get("minimum_reserve_tanks") is not None:
            parts.append(f"pelo menos {data['minimum_reserve_tanks']} Reserve Tanks")
        for key, amount in (data.get("ammo") or {}).items():
            parts.append(f"{amount} de {key.replace('_', ' ')}")
        if not parts:
            return f"A base marca os requisitos de {nome} como conhecidos, mas não lista nenhum requisito específico, Neitan."
        return f"Para {nome}, a base exige " + "; ".join(parts) + "."

    if field in {"effect", "uses"}:
        values = value if isinstance(value, list) else [value]
        return f"{nome}: " + " ".join(str(item) for item in values if item)

    if field == "acquisition":
        data = value if isinstance(value, dict) else {}
        notes = data.get("normal_route_notes")
        if notes:
            return f"{nome}: {notes}"
        return f"A aquisição de {nome} está cadastrada, mas sem descrição detalhada, Neitan."

    return f"{nome}: {value}"


class RetrievalResponder:
    def __init__(self, prompt_builder):
        self.prompt_builder = prompt_builder

    def resolve(self, retrieved: Optional[Dict[str, Any]]) -> Optional[str]:
        if not retrieved:
            return None

        if retrieved.get("personal_query"):
            facts = retrieved.get("owner_facts", [])
            mem0_memories = retrieved.get("mem0_memories", [])
            if facts:
                fact = facts[0]
                key = str(fact.get("key", "")).strip()
                value = str(fact.get("value", "")).strip()
                labels = {
                    "filme_favorito": "filme favorito", "comida_favorita": "comida favorita",
                    "jogo_favorito": "jogo favorito", "serie_favorita": "série favorita",
                    "desenho_favorito": "desenho favorito", "banda_favorita": "banda favorita",
                    "franquia_de_jogo_favorita": "franquia de jogo favorita",
                    "doom_favorito": "Doom favorito", "metroid_favorito": "Metroid favorito",
                    "zelda_favorito": "Zelda favorito",
                }
                label = labels.get(key, key.replace("_", " "))
                if value:
                    return f"Seu {label} é {value}, Neitan."
            if mem0_memories:
                return None
            return "Eu não tenho essa informação no meu perfil, no Mem0 nem no histórico atual, Neitan."

        # Knowledge local foi removido na 0.5.5.
        # Este responder agora só resolve memória pessoal do Neitan.
        return None

    @staticmethod
    def validate_grounded_response(response: str, retrieved: Optional[Dict[str, Any]]) -> str:
        return response
