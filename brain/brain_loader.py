# -*- coding: utf-8 -*-

# =========================
# 🧠 DIANA BRAIN LOADER
# =========================

import json
from pathlib import Path


# Limites intencionais para manter o prompt leve.
# Se o Brain crescer, ajuste estes números conscientemente.
MAX_RESPONSE_STYLE_RULES = 10
MAX_STYLE_BOUNDARIES = 8
MAX_VOCABULARY_POLICY_RULES = 6
MAX_EXAMPLES = 4


class DianaBrain:

    def __init__(self, brain_path="brain/diana_brain.json"):

        self.brain_path = Path(brain_path)
        self.data = {}
        self.load()

    def load(self):

        try:
            with open(self.brain_path, "r", encoding="utf-8") as file:
                self.data = json.load(file)
        except Exception as erro:
            print("⚠️ Erro ao carregar Diana Brain:", erro)
            self.data = {}

    def get(self, key, default=None):

        return self.data.get(key, default)

    def _format_list(self, items):

        if not items:
            return ""

        return "\n".join("- " + str(item) for item in items)

    def _format_relationships(self):

        relationships = self.data.get("relationships", {})

        if not relationships:
            return ""

        linhas = []

        for name, info in relationships.items():
            relationship = info.get("relationship", "")
            behavior = info.get("behavior", "")
            aliases = ", ".join(info.get("aliases", []))
            input_identifiers = ", ".join(info.get("input_identifiers", []))

            linhas.append(f"{name}: {relationship}")

            if aliases:
                linhas.append(f"Como reconhecer/chamar: {aliases}")

            if input_identifiers:
                linhas.append(f"Identificadores de entrada, nunca usar como tratamento: {input_identifiers}")

            if behavior:
                linhas.append(f"Como tratar: {behavior}")

        return "\n".join(linhas)

    def _format_examples(self, max_examples=MAX_EXAMPLES):

        rules = self.data.get("rules", {})
        examples = rules.get("examples", [])

        if not examples:
            examples = self.data.get("examples", [])

        if not examples:
            return ""

        linhas = [
            "ATENÇÃO: estes exemplos mostram apenas o estilo e formato esperado da resposta.",
            "Eles NÃO são memórias reais. NÃO são conversas que aconteceram.",
            "Nunca use o conteúdo dos exemplos como fonte de informação sobre o Neitan.",
            "Use os exemplos somente para aprender ritmo e forma. Não copie literalmente."
        ]

        for ex in examples[:max_examples]:
            user = str(ex.get("user", "")).strip()
            diana = str(ex.get("diana", "")).strip()

            if not user or not diana:
                continue

            linhas.append("Usuário: " + user)
            linhas.append("Diana: " + diana)

        return "\n".join(linhas)

    def _format_vocabulary(self, max_items=6):

        vocabulary = self.data.get("vocabulary", {})

        if not vocabulary:
            return ""

        linhas = [
            "Vocabulário próprio ativo. Use somente se encaixar perfeitamente.",
            "Não use em saudação simples ou resposta técnica simples."
        ]

        for index, (key, info) in enumerate(vocabulary.items()):
            if index >= max_items:
                break

            if isinstance(info, dict):
                meaning = info.get("meaning", "")
                use_when = info.get("use_when", "")
                linha = f"{key}: {meaning}"

                if use_when:
                    linha += f" | usar quando: {use_when}"

                linhas.append(linha)
            else:
                linhas.append(f"{key}: {info}")

        return "\n".join(linhas)

    def build_brain_context(self):

        personality = self.data.get("personality", {})
        emotional = self.data.get("emotional_analysis", {})
        rules = self.data.get("rules", {})
        actions = self.data.get("actions", {})

        partes = []

        partes.append("# DIANA BRAIN")

        if emotional:
            partes.append(
                "Estado atual: "
                + str(emotional.get("current_state", ""))
                + " — "
                + str(emotional.get("sentiment", ""))
            )

        partes.append("# IDENTIDADE")
        partes.append("Nome: " + str(personality.get("name", "Diana")))
        partes.append("Papel: " + str(personality.get("role", "VTuber caótica do Neitan")))
        partes.append(str(personality.get("description", "")))

        traits = personality.get("traits", [])
        if traits:
            partes.append("# TRAÇOS")
            partes.append(self._format_list(traits))

        relationships = self._format_relationships()
        if relationships:
            partes.append("# RELAÇÕES")
            partes.append(relationships)

        response_style = rules.get("response_style", [])
        if response_style:
            partes.append("# REGRAS DE RESPOSTA PRIORITÁRIAS")
            partes.append(self._format_list(response_style[:MAX_RESPONSE_STYLE_RULES]))

        style_boundaries = rules.get("style_boundaries", [])
        if style_boundaries:
            partes.append("# LIMITES DE ESTILO")
            partes.append(self._format_list(style_boundaries[:MAX_STYLE_BOUNDARIES]))

        vocabulary_policy = rules.get("vocabulary_policy", [])
        if vocabulary_policy:
            partes.append("# POLÍTICA DE VOCABULÁRIO")
            partes.append(self._format_list(vocabulary_policy[:MAX_VOCABULARY_POLICY_RULES]))

        action_instructions = actions.get("instructions", [])
        if action_instructions:
            partes.append("# ACTIONS — FORMATO OBRIGATÓRIO")
            partes.append(self._format_list(action_instructions))

        examples = self._format_examples(max_examples=MAX_EXAMPLES)
        if examples:
            partes.append("# EXEMPLOS DE RITMO E FORMATO — NÃO SÃO MEMÓRIAS")
            partes.append(examples)

        vocabulary = self._format_vocabulary()
        if vocabulary:
            partes.append("# VOCABULÁRIO ATIVO DA DIANA")
            partes.append(vocabulary)

        return "\n\n".join(part for part in partes if str(part).strip())
