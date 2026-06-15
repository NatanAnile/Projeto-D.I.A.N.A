# -*- coding: utf-8 -*-

# =========================
# 🧠 SKILL SYSTEM
# =========================

from skills.comment_skill import CommentSkill
from skills.read_file_skill import ReadFileSkill
from skills.read_chat_skill import ReadChatSkill
from skills.read_screen_skill import ReadScreenSkill
from skills.style_skill import StyleSkill
from skills.game_context_skill import GameContextSkill
from skills.donate_skill import DonateSkill
from skills.command_skill import CommandSkill
from skills.chat_reply_skill import ChatReplySkill


class SkillManager:

    MIN_SEMANTIC_CONFIDENCE = 0.45
    OPERATIONAL_CAPABILITIES = {"read_chat", "read_file", "read_screen", "send_chat", "style_query"}

    def __init__(self, context=None):

        self.context = context
        self.chat_reply_skill = ChatReplySkill()

        self.read_chat_skill = ReadChatSkill()
        self.read_file_skill = ReadFileSkill()
        self.read_screen_skill = ReadScreenSkill()

        self.direct_skills = [
            self.read_chat_skill,
            self.read_file_skill,
            self.read_screen_skill,
            DonateSkill(),
            CommandSkill()
        ]

        self.primary_skills = [
            self.read_chat_skill,
            self.read_file_skill,
            StyleSkill(),
            GameContextSkill()
        ]

        self.modifier_skills = [CommentSkill()]

    # =========================
    # 🔐 CAPACIDADES
    # =========================

    def is_operational(self, capability):

        return str(capability or "none").lower().strip() in self.OPERATIONAL_CAPABILITIES

    # =========================
    # ⚡ RESPOSTA DIRETA
    # =========================

    def verificar_resposta_direta(self, user_text="", conversation=None, turn_context=None):

        turn_context = turn_context or {}
        capability = str(turn_context.get("requested_capability", "none")).lower().strip()
        confidence = float(turn_context.get("confidence", 0.0) or 0.0)

        if capability == "read_screen" and confidence >= self.MIN_SEMANTIC_CONFIDENCE:
            return self.read_screen_skill.get_direct_response(user_text=user_text, conversation=conversation, force=True)

        if capability == "read_chat" and confidence >= self.MIN_SEMANTIC_CONFIDENCE:
            return self.read_chat_skill.get_direct_response(user_text=user_text, conversation=conversation, force=True)

        if capability == "read_file" and confidence >= self.MIN_SEMANTIC_CONFIDENCE:
            try:
                return self.read_file_skill.get_direct_response(user_text=user_text, conversation=conversation, force=True)
            except TypeError:
                return None

        if capability == "send_chat" and confidence >= self.MIN_SEMANTIC_CONFIDENCE:

            mensagem_direta = self.chat_reply_skill.extrair_mensagem_direta(user_text)

            if not mensagem_direta:
                return "Não encontrei o texto exato para mandar no chat. Usa assim: manda no chat: sua mensagem"

            enviado = self.chat_reply_skill.enviar_para_chat(
                user_text=user_text,
                response=mensagem_direta,
                force=True
            )

            if enviado:
                return "Mandei no chat: " + mensagem_direta

            return "Não consegui mandar essa mensagem no chat."

        # Fallback técnico apenas quando o interpretador falhar.
        if confidence >= self.MIN_SEMANTIC_CONFIDENCE:
            return None

        for skill in self.direct_skills:

            if not hasattr(skill, "get_direct_response"):
                continue

            try:
                response = skill.get_direct_response(user_text=user_text, conversation=conversation)
            except TypeError:
                response = skill.get_direct_response(user_text=user_text, conversation=conversation)

            if response:
                return response

        return None

    # =========================
    # 🧩 CONTEXTO PARA PROMPT
    # =========================

    def verificar_skills(self, user_text="", conversation=None, turn_context=None):

        contextos = []
        primary_context = None
        primary_name = None
        turn_context = turn_context or {}
        capability = str(turn_context.get("requested_capability", "none")).lower().strip()
        confidence = float(turn_context.get("confidence", 0.0) or 0.0)

        # Em modo operacional, não entra CommentSkill.
        if self.is_operational(capability):
            if capability == "read_chat" and confidence >= self.MIN_SEMANTIC_CONFIDENCE:
                primary_context = self.read_chat_skill.get_context(user_text=user_text, conversation=conversation, force=True)
                primary_name = "ReadChatSkill"

            elif capability == "read_file" and confidence >= self.MIN_SEMANTIC_CONFIDENCE:
                primary_context = self.read_file_skill.get_context(user_text=user_text, conversation=conversation, force=True)
                primary_name = "ReadFileSkill"

            elif capability == "style_query":
                for skill in self.primary_skills:
                    if isinstance(skill, StyleSkill):
                        primary_context = skill.get_context(user_text=user_text, conversation=conversation)
                        primary_name = "StyleSkill"
                        break

            if primary_context:
                contextos.append(primary_context)

            return "\n\n".join(contextos) if contextos else None

        for skill in self.primary_skills:

            if not hasattr(skill, "get_context"):
                continue

            try:
                contexto = skill.get_context(user_text=user_text, conversation=conversation, turn_context=turn_context)
            except TypeError:
                contexto = skill.get_context(user_text=user_text, conversation=conversation)

            if contexto:
                primary_context = contexto
                primary_name = skill.__class__.__name__
                contextos.append(contexto)
                break

        for skill in self.modifier_skills:

            if not hasattr(skill, "get_context"):
                continue

            try:
                contexto = skill.get_context(
                    user_text=user_text,
                    conversation=conversation,
                    primary_active=primary_context is not None,
                    primary_name=primary_name,
                    turn_context=turn_context
                )
            except TypeError:
                contexto = skill.get_context(user_text=user_text, conversation=conversation)

            if contexto:
                contextos.append(contexto)

        if not contextos:
            return None

        return "\n\n".join(contextos)

    # =========================
    # 💬 ENVIAR RESPOSTA AO CHAT
    # =========================

    def enviar_resposta_para_chat_se_precisar(self, user_text="", response="", turn_context=None):

        turn_context = turn_context or {}
        capability = str(turn_context.get("requested_capability", "none")).lower().strip()
        confidence = float(turn_context.get("confidence", 0.0) or 0.0)

        if capability != "send_chat" or confidence < self.MIN_SEMANTIC_CONFIDENCE:
            return False

        return self.chat_reply_skill.enviar_para_chat(
            user_text=user_text,
            response=response,
            force=True
        )
