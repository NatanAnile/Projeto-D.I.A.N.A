# -*- coding: utf-8 -*-

# =========================
# 💬 COMMENT SKILL SYSTEM
# =========================

import json
import random
import re
import time
from pathlib import Path

from skills.base_skill import BaseSkill, SkillContext


class CommentSkill(BaseSkill):
    """Camada de comentário/persona.

    CommentSkill não é uma skill de personalidade específica. Ele é o
    seletor/gerenciador de ações de comentário. As ações reais ficam em
    skill_actions.json: improvisar_caos, elogiar_ironicamente, etc.
    """

    ACTIONS_PATH = Path(__file__).with_name("skill_actions.json")

    def __init__(self):
        context = SkillContext(
            skill_name="CommentSkill",
            min_cooldown=0,
            max_cooldown=0
        )
        super().__init__(context)

        self.last_action = None
        self.action_history = []
        self.global_last_used = 0
        self.global_min_cooldown = 1.25
        self.ambient_chance = 0.92
        self.spontaneous_chance = 0.88
        self.all_actions = self.load_actions()

    # =========================
    # 📦 CARREGAR AÇÕES
    # =========================

    def load_actions(self):
        fallback = {
            "fazer_comentario_curto": {
                "cooldown": 8,
                "prompts": ["Faça um comentário curto, contextual e com personalidade."]
            },
            "improvisar_caos": {
                "cooldown": 6,
                "prompts": ["Improvisa uma reação curta, caótica e contextual sem inventar fato."]
            },
            "assumir_chute": {
                "cooldown": 12,
                "prompts": ["Assuma o erro com deboche curto e corrija o rumo."]
            }
        }

        try:
            data = json.loads(self.ACTIONS_PATH.read_text(encoding="utf-8"))
            actions = data.get("comment", {}) if isinstance(data, dict) else {}
        except Exception:
            actions = {}

        if not isinstance(actions, dict) or not actions:
            actions = fallback

        resolved = {}
        for name, config in actions.items():
            if not isinstance(config, dict):
                continue
            if "alias_of" in config:
                continue
            prompts = config.get("prompts", [])
            if isinstance(prompts, str):
                prompts = [prompts]
            prompts = [str(p).strip() for p in prompts if str(p).strip()]
            if not prompts:
                continue
            resolved[name] = {
                "prompts": prompts,
                "cooldown": max(0, int(config.get("cooldown", 10) or 10)),
                "last_used": 0
            }

        # Resolve aliases depois dos alvos existirem.
        for name, config in actions.items():
            if not isinstance(config, dict) or "alias_of" not in config:
                continue
            target = str(config.get("alias_of", "")).strip()
            if target in resolved:
                resolved[name] = resolved[target]

        for name, config in fallback.items():
            if name not in resolved:
                resolved[name] = {
                    "prompts": list(config["prompts"]),
                    "cooldown": int(config["cooldown"]),
                    "last_used": 0
                }

        return resolved

    # =========================
    # ⏱️ COOLDOWN DINÂMICO
    # =========================

    def action_available(self, action_name):
        action = self.all_actions.get(action_name)
        if not action:
            return False
        return time.time() - action.get("last_used", 0) >= action.get("cooldown", 10)

    def global_available(self):
        return time.time() - self.global_last_used >= self.global_min_cooldown

    def mark_used(self, action_name):
        now = time.time()
        self.global_last_used = now
        self.last_action = action_name
        self.action_history.append(action_name)
        self.action_history = self.action_history[-6:]
        if action_name in self.all_actions:
            self.all_actions[action_name]["last_used"] = now

    # =========================
    # 🧭 SELEÇÃO DE AÇÃO
    # =========================

    def _looks_like_operational_ambiguous(self, user_text, capability, confidence):
        if str(capability or "none").lower().strip() != "none":
            return False
        text = str(user_text or "").lower()
        task_terms = [
            "arquivo", "arquivos", "read_files", "chat", "mensagem", "mensagens",
            "tela", "print", "screenshot", "artigo", "transcrição", "transcricao",
            "resume", "resuma", "analisa", "analise", "explica", "explique",
            "lê", "le ", "ler", "leia", "vê", "ve ", "ver", "olha", "lista",
            "quais tem", "escolhe", "escolha", "pega", "pegue"
        ]
        return any(term in text for term in task_terms) and float(confidence or 0.0) < 0.45

    def _preferencias_por_contexto(self, user_text, turn_context, relation, source, topic):
        capability = str(turn_context.get("requested_capability", "none")).lower().strip()
        text = str(user_text or "").lower()
        options = []

        if source == "CHAT_USER" or capability == "read_chat" or "chat" in topic:
            options += ["zoar_chat", "fazer_comentario_curto", "improvisar_caos"]

        if relation in ["feedback", "correcao"] or any(x in text for x in ["errou", "errada", "errado", "bug", "não funcionou", "nao funcionou"]):
            options += ["assumir_chute", "improvisar_caos", "reclamar_dramaticamente"]

        if any(x in text for x in ["morri", "perdi", "falhei", "errei", "de novo"]):
            options += ["elogiar_ironicamente", "reclamar_dramaticamente", "improvisar_caos"]

        if any(x in text for x in ["você", "voce", "diana", "criatura"]):
            options += ["discordar_de_forma_absurda", "brigar_de_brincadeira", "improvisar_caos"]

        options += [
            "improvisar_caos",
            "fazer_comentario_curto",
            "comentario_com_gancho",
            "elogiar_ironicamente",
            "reclamar_dramaticamente",
            "discordar_de_forma_absurda"
        ]
        return [action for action in options if action in self.all_actions]

    def _choose_action(self, options):
        unique = []
        for action in options:
            if action not in unique:
                unique.append(action)

        available = [a for a in unique if self.action_available(a) and a != self.last_action]
        if not available:
            available = [a for a in unique if a != self.last_action]
        if not available:
            available = unique or ["improvisar_caos"]

        # Penaliza vício recente sem engessar: ações repetidas ainda podem sair se não houver opção.
        weighted = []
        recent = set(self.action_history[-3:])
        for action in available:
            weight = 1 if action in recent else 3
            weighted.extend([action] * weight)
        return random.choice(weighted)

    # =========================
    # 🧠 CONTEXTO PARA PROMPT
    # =========================

    def get_context(self, user_text="", conversation=None, primary_active=False, primary_name=None, turn_context=None):
        turn_context = turn_context or {}
        action_name = str(turn_context.get("personality_action", "none")).strip()
        reason = str(turn_context.get("personality_reason", "")).strip()
        relation = str(turn_context.get("relation", "")).strip()
        source = str(turn_context.get("source", "OWNER")).upper().strip()
        topic = str(turn_context.get("topic", "")).lower().strip()
        capability = str(turn_context.get("requested_capability", "none")).strip()
        explicit = bool(turn_context.get("personality_explicit", False))
        confidence = float(turn_context.get("confidence", 0.0) or 0.0)

        if self._looks_like_operational_ambiguous(user_text, capability, confidence):
            return None

        if not self.global_available() and not explicit:
            return None

        if action_name == "none" or action_name not in self.all_actions:
            if random.random() > self.spontaneous_chance:
                return None
            action_name = self._choose_action(self._preferencias_por_contexto(user_text, turn_context, relation, source, topic))
            reason = reason or "Espontaneidade contextual da Diana."

        chat_context = source == "CHAT_USER" or capability == "read_chat" or "chat" in topic
        if action_name == "zoar_chat" and not chat_context:
            action_name = "improvisar_caos"
            reason = "Sem contexto real de chat; improvisar sem inventar plateia."

        if confidence < 0.45 and not explicit:
            if action_name not in ["improvisar_caos", "fazer_comentario_curto", "assumir_chute"]:
                action_name = self._choose_action(["improvisar_caos", "fazer_comentario_curto", "assumir_chute"])
            reason = reason or "Interpretação incerta; manter personalidade sem inventar tarefa."

        intent = str(turn_context.get("intent", "")).lower().strip()
        tarefa_direta = any(term in intent for term in ["contar", "piada", "explicar", "resumir", "ler", "listar", "mostrar"])
        if tarefa_direta and action_name in ["pedir_algo", "zoar_chat"]:
            action_name = "fazer_comentario_curto"
            reason = "Tarefa direta detectada; comentário tempera sem substituir."

        if not self.action_available(action_name) and not explicit:
            action_name = self._choose_action(self._preferencias_por_contexto(user_text, turn_context, relation, source, topic))

        if not explicit and random.random() > self.ambient_chance:
            return None

        return self.montar_contexto(
            action_name=action_name,
            explicit=explicit,
            primary_active=primary_active,
            primary_name=primary_name,
            reason=reason,
            must_answer=""
        )

    # =========================
    # 🧩 CONTEXTO
    # =========================

    def montar_contexto(self, action_name, explicit=False, primary_active=False, primary_name=None, reason="", must_answer=""):
        action = self.all_actions.get(action_name)
        if not action:
            return None

        prompt = random.choice(action.get("prompts", []))
        self.mark_used(action_name)

        if explicit:
            print("🧩 Skill de personalidade executada -> " + action_name + " (explícita)")
        else:
            print("🧩 Skill de personalidade executada -> " + action_name)

        contexto_primario = ""
        if primary_active and primary_name:
            contexto_primario = (
                "\nExiste uma capacidade principal ativa: " + primary_name + "."
                "\nA personalidade não pode atrapalhar nem substituir essa capacidade."
            )

        must = ""
        if must_answer:
            must = "\nResposta obrigatória: " + must_answer

        return (
            "SISTEMA DE COMENTÁRIO/PERSONALIDADE ATIVO\n"
            "Ação de personalidade executada: " + action_name + "\n"
            "Motivo contextual: " + (reason or "comentário dinâmico") + "\n"
            "Instrução de estilo: " + prompt
            + contexto_primario
            + must
            + "\nRegras:"
            "\n- Use a ação como impulso criativo, não como frase pronta."
            "\n- Continue ligada ao assunto atual."
            "\n- Crie algo novo para esta conversa."
            "\n- Não puxe live, Twitch, chat ou canal sem contexto real."
            "\n- Não diga que uma skill foi ativada."
        )
