# -*- coding: utf-8 -*-

# =========================
# 💬 CHAT REPLY SKILL
# =========================

from skills.base_skill import BaseSkill, SkillContext

from integrations.streamerbot_chat import (
    deve_enviar_para_chat,
    extrair_mensagem_direta_chat,
    enviar_mensagem_chat
)


class ChatReplySkill(BaseSkill):

    def __init__(self):

        context = SkillContext(
            skill_name="ChatReplySkill",
            min_cooldown=0,
            max_cooldown=0
        )

        super().__init__(context)

    # =========================
    # 🔎 DETECTAR PEDIDO
    # =========================

    def detectar_pedido(self, user_text):

        return deve_enviar_para_chat(user_text)

    # =========================
    # ✂️ EXTRAIR MENSAGEM DIRETA
    # =========================

    def extrair_mensagem_direta(self, user_text):

        return extrair_mensagem_direta_chat(user_text)

    # =========================
    # 💬 ENVIAR RESPOSTA AO CHAT
    # =========================

    def enviar_para_chat(self, user_text, response, force=False):

        if not force and not self.detectar_pedido(user_text):
            return False

        mensagem_direta = self.extrair_mensagem_direta(user_text)

        if mensagem_direta:
            return enviar_mensagem_chat(mensagem_direta)

        return enviar_mensagem_chat(response)