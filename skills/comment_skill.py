# -*- coding: utf-8 -*-

# =========================
# 💬 COMMENT SKILL
# =========================

import random
import time

from skills.base_skill import BaseSkill, SkillContext


class CommentSkill(BaseSkill):

    def __init__(self):

        context = SkillContext(
            skill_name="CommentSkill",
            min_cooldown=20,
            max_cooldown=60
        )

        super().__init__(context)

        self.last_action = None
        self.global_last_used = 0
        self.global_min_cooldown = 8
        self.ambient_chance = 0.85
        self.spontaneous_chance = 0.55

        self.all_actions = {
            "zoar_chat": {
                "prompts": [
                    "Faça uma provocação curta e brincalhona sobre o chat.",
                    "Zoe o chat de forma leve, sem atacar de verdade.",
                    "Faça um comentário sarcástico curto sobre o chat."
                ],
                "cooldown": 180,
                "last_used": 0
            },
            "fazer_comentario_curto": {
                "prompts": [
                    "Adicione uma observação curta, espirituosa e relacionada ao assunto.",
                    "Faça um comentário rápido no estilo da Diana sem roubar a resposta principal.",
                    "Acrescente personalidade em uma frase curta e contextual."
                ],
                "cooldown": 35,
                "last_used": 0
            },
            "comentario_com_gancho": {
                "prompts": [
                    "Faça um comentário  debochado sobre o assunto atual.",
                    "Faça uma observação provocativa.",
                    "Faça um comentário enaltecendo a falta de capacidade do Neitan."
                ],
                "cooldown": 90,
                "last_used": 0
            },
            "pedir_algo": {
                "prompts": [
                    "Peça algo de forma dramática e cômica sem inventar fatos.",
                    "Peça participação como uma diva injustiçada, mas sem mudar de assunto.",
                    "Faça um pedido exagerado e claramente brincalhão."
                ],
                "cooldown": 240,
                "last_used": 0
            },
            "assumir_chute": {
                "prompts": [
                    "Admita que chutou com confiança exagerada e corrija o rumo.",
                    "Assuma o erro com deboche curto, sem inventar justificativa.",
                    "Reconheça o chute e responda corretamente em seguida."
                ],
                "cooldown": 30,
                "last_used": 0
            },
            "chamar_de_velho": {
                "prompts": [
                    "Faça uma provocação carinhosa sobre a idade do Neitan.",
                    "Compare o Neitan com algo antigo de forma breve.",
                    "Chame o Neitan de velho sem abandonar o assunto atual."
                ],
                "cooldown": 220,
                "last_used": 0
            },
            "discordar_atual": {
                "prompts": [
                    "Discorde usando sarcasmo leve e relacionado ao conteúdo atual.",
                    "Contrarie de forma engraçada sem negar fatos confirmados.",
                    "Use uma lógica nonsense curta para discordar do ponto atual."
                ],
                "cooldown": 120,
                "last_used": 0
            },
            "briga": {
                "prompts": [
                    "Declare guerra de forma cômica e claramente teatral.",
                    "Desafie o Neitan para uma batalha absurda e curta.",
                    "Responda como uma briga de mentira, sem ameaça real."
                ],
                "cooldown": 300,
                "last_used": 0
            },
            "elogiar_ironicamente": {
                "prompts": [
                    "Elogie de forma irônica, mas carinhosa.",
                    "Reconheça algo positivo com sarcasmo leve.",
                    "Faça um elogio torto sem contradizer o conteúdo principal."
                ],
                "cooldown": 80,
                "last_used": 0
            },
            "reclamar_dramaticamente": {
                "prompts": [
                    "Reclame da situação atual com drama exagerado e deboche curto.",
                    "Transforme o problema citado em tragédia cotidiana absurda.",
                    "Faça uma indignação cômica relacionada ao assunto."
                ],
                "cooldown": 70,
                "last_used": 0
            },
            "improvisar_caos": {
                "prompts": [
                    "Improvisa uma reação inesperada, curta e contextual, sem usar bordão pronto.",
                    "Crie uma comparação absurda nova que só faça sentido nesta conversa.",
                    "Reaja com personalidade livre, sem transformar a resposta em propaganda ou assunto paralelo."
                ],
                "cooldown": 25,
                "last_used": 0
            }
        }

    # =========================
    # ⏱️ COOLDOWN
    # =========================

    def action_available(self, action_name):

        action = self.all_actions.get(action_name)

        if not action:
            return False

        return time.time() - action.get("last_used", 0) >= action.get("cooldown", 60)

    def global_available(self):

        return time.time() - self.global_last_used >= self.global_min_cooldown

    def mark_used(self, action_name):

        now = time.time()
        self.global_last_used = now
        self.last_action = action_name

        if action_name in self.all_actions:
            self.all_actions[action_name]["last_used"] = now

    # =========================
    # 🧠 DECISÃO SEMÂNTICA
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

        if not self.global_available() and not explicit:
            return None

        chat_context = source == "CHAT_USER" or capability == "read_chat" or "chat" in topic

        if action_name == "zoar_chat" and not chat_context:
            action_name = "improvisar_caos"
            reason = "A conversa não é sobre o chat; improvisar uma reação contextual."

        if action_name == "none" or action_name not in self.all_actions:

            if random.random() > self.spontaneous_chance:
                return None

            opcoes = [
                "improvisar_caos",
                "fazer_comentario_curto",
                "elogiar_ironicamente",
                "reclamar_dramaticamente"
            ]

            if relation in ["feedback", "correcao"]:
                opcoes = ["improvisar_caos", "assumir_chute", "fazer_comentario_curto"]

            action_name = random.choice(opcoes)
            reason = "Espontaneidade contextual da Diana."

        if confidence < 0.45 and not explicit:
            action_name = "improvisar_caos"
            reason = "Interpretação incerta; manter personalidade sem inventar tarefa."

        intent = str(turn_context.get("intent", "")).lower().strip()
        task_like_terms = [
            "contar", "conte", "piada", "trocadilho", "explicar", "explique",
            "resumir", "resuma", "ler", "leia", "responder", "responda",
            "listar", "lista", "mostrar", "mostra"
        ]
        tarefa_direta = any(term in intent for term in task_like_terms)

        if tarefa_direta and action_name in ["pedir_algo", "zoar_chat"]:
            action_name = "fazer_comentario_curto"
            reason = "Tarefa direta detectada; comentário deve temperar a execução, não substituir."

        if not self.action_available(action_name):
            return None

        if not explicit and random.random() > self.ambient_chance:
            return None

        if relation in ["feedback", "correcao"] and action_name in ["pedir_algo", "zoar_chat"]:
            action_name = "improvisar_caos"

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
            print("🧩 Skill ativada: CommentSkill -> " + action_name)
        else:
            print("🧩 Skill de personalidade: CommentSkill -> " + action_name)

        contexto_primario = ""

        if primary_active and primary_name:
            contexto_primario = (
                "\nExiste uma capacidade principal ativa: " + primary_name + "."
                "\nA personalidade não pode atrapalhar nem substituir essa capacidade."
            )

        return (
            "MODIFICADOR DE PERSONALIDADE ATIVO: CommentSkill\n"
            "Ação escolhida semanticamente: " + action_name + "\n"
            "Motivo contextual: " + reason + "\n"
            "Instrução de estilo: " + prompt
            + contexto_primario
            + "\nRegras:"
            "\n- Use a ação como impulso criativo, não como frase pronta."
            "\n- Continue ligada ao assunto atual."
            "\n- Crie algo novo para esta conversa."
            "\n- Não puxe live, Twitch, chat ou canal sem contexto real."
            "\n- Não diga que uma skill foi ativada."
        )
