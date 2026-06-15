# -*- coding: utf-8 -*-

# =========================
# 📚 STYLE SKILL
# =========================

from skills.base_skill import BaseSkill, SkillContext


class StyleSkill(BaseSkill):

    def __init__(self):

        context = SkillContext(
            skill_name="StyleSkill",
            min_cooldown=0,
            max_cooldown=0
        )

        super().__init__(context)

    def detectar_pedido(self, user_text):

        texto = user_text.lower().strip()

        gatilhos = [
            "meu jeito de falar",
            "meus bordões",
            "meus bordoes",
            "minhas gírias",
            "minhas girias",
            "como eu falo",
            "que termo é esse",
            "que termo e esse"
        ]

        for gatilho in gatilhos:

            if gatilho in texto:
                return True

        return False

    def get_context(self, user_text="", conversation=None):

        if not self.detectar_pedido(user_text):
            return None

        print("🧩 Skill ativada: StyleSkill")

        return (
            "CAPACIDADE SOLICITADA: StyleSkill\n"
            "Status: parcialmente conectada via StyleDictionary.\n"
            "A Diana usa o StyleDictionary e expressões autônomas como contexto leve.\n"
            "Se houver contexto de estilo no prompt, use ele sem inventar significado."
        )