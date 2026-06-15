# -*- coding: utf-8 -*-

# =========================
# 🕹️ COMMAND SKILL
# =========================

from skills.base_skill import BaseSkill, SkillContext


class CommandSkill(BaseSkill):

    def __init__(self):

        context = SkillContext(
            skill_name="CommandSkill",
            min_cooldown=0,
            max_cooldown=0
        )

        super().__init__(context)

    def detectar_pedido(self, user_text):

        texto = user_text.lower().strip()

        gatilhos = [
            "manda comando",
            "executa comando",
            "ativa comando",
            "desativa comando",
            "manda udp",
            "streamer.bot",
            "streamer bot",
            "aperta botão",
            "aperta botao",
            "pressiona botão",
            "pressiona botao"
        ]

        for gatilho in gatilhos:

            if gatilho in texto:
                return True

        return False

    def get_direct_response(self, user_text="", conversation=None):

        if not self.detectar_pedido(user_text):
            return None

        print("🧩 Skill direta ativada: CommandSkill")

        return (
            "Ainda não executo comandos externos diretamente nesse fluxo. "
            "Então eu não vou fingir que apertei botão, mandei UDP ou acionei o Streamer.bot."
        )

    def get_context(self, user_text="", conversation=None):

        return None