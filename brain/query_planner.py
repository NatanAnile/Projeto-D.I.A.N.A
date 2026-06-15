# -*- coding: utf-8 -*-

# =========================
# 🗺️ QUERY PLANNER AUXILIAR
# =========================

from config import QUERY_PLANNER_ENABLED, QUERY_PLANNER_TEMPERATURE, QUERY_PLANNER_MAX_TOKENS
from llm.auxiliary_ollama_llm import AuxiliaryOllamaLLM


class QueryPlanner:

    ALLOWED_SOURCES = {"knowledge", "owner", "history", "none"}
    ALLOWED_COLLECTIONS = {
        "", "techniques", "glitches", "items", "rooms", "enemies",
        "bosses", "routes", "categories"
    }
    ALLOWED_OPERATIONS = {"search", "same", "another", "first", "last", "count", "reformulate", "list", "random"}

    def __init__(self, enabled=None, llm=None):
        self.enabled = QUERY_PLANNER_ENABLED if enabled is None else bool(enabled)
        self.llm = llm or AuxiliaryOllamaLLM(enabled=self.enabled)

    def plan(self, user_text, history_text="", last_collection="", last_entry_name=""):
        if not self.enabled:
            return None

        prompt = f"""
Você é um planejador de consultas. NÃO responda ao usuário e NÃO interprete personalidade.
Transforme a mensagem atual em uma consulta curta e estruturada.

Coleções permitidas: techniques, glitches, items, rooms, enemies, bosses, routes, categories.
Operações permitidas: search, same, another, first, last, count, reformulate, list, random.
Fontes permitidas: knowledge, owner, history, none.

Regras:
- "a mesma", "explica melhor", "mais simples" => same ou reformulate.
- "outra", "diferente", "mais uma" => another.
- Se a mensagem omitir a coleção, preserve last_collection quando fizer sentido.
- "uma técnica com X-Ray" => collection=techniques e filters.contains=["X-Ray Scope"].
- Não invente nomes de entradas.
- Retorne APENAS JSON.

Estado anterior:
last_collection={last_collection}
last_entry_name={last_entry_name}

Histórico recente:
{history_text[-3500:]}

Mensagem atual:
{user_text}

Formato:
{{
  "source": "knowledge|owner|history|none",
  "collection": "",
  "operation": "search",
  "filters": {{"contains": []}},
  "requires_local_source": false
}}
""".strip()

        data = self.llm.generate_json(
            prompt,
            temperature=QUERY_PLANNER_TEMPERATURE,
            num_predict=QUERY_PLANNER_MAX_TOKENS
        )
        return self._sanitize(data)

    def _sanitize(self, data):
        if not isinstance(data, dict):
            return None

        source = str(data.get("source", "none")).strip().lower()
        collection = str(data.get("collection", "")).strip().lower()
        operation = str(data.get("operation", "search")).strip().lower()
        filters = data.get("filters", {})

        if source not in self.ALLOWED_SOURCES:
            source = "none"
        if collection not in self.ALLOWED_COLLECTIONS:
            collection = ""
        if operation not in self.ALLOWED_OPERATIONS:
            operation = "search"
        if not isinstance(filters, dict):
            filters = {}

        contains = filters.get("contains", [])
        category = str(filters.get("category", "")).strip().lower()
        limit = data.get("limit")
        try:
            limit = int(limit) if limit not in [None, ""] else None
        except (TypeError, ValueError):
            limit = None
        if isinstance(contains, str):
            contains = [contains]
        if not isinstance(contains, list):
            contains = []

        return {
            "source": source,
            "collection": collection,
            "operation": operation,
            "filters": {"contains": [str(item).strip() for item in contains if str(item).strip()], "category": category},
            "limit": limit,
            "requires_local_source": bool(data.get("requires_local_source", False))
        }
