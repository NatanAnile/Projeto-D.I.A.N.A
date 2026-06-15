# -*- coding: utf-8 -*-

# =========================
# 💸 DONATE SKILL
# =========================

from skills.base_skill import BaseSkill, SkillContext


class DonateSkill(BaseSkill):

    def __init__(self):

        context = SkillContext(
            skill_name="DonateSkill",
            min_cooldown=0,
            max_cooldown=0
        )

        super().__init__(context)

    def detectar_pedido(self, user_text):

        texto = user_text.lower().strip()

        gatilhos = [
            "leu o donate",
            "lê o donate",
            "le o donate",
            "superchat",
            "doação",
            "doacao",
            "bits",
            "membro novo",
            "novo membro"
        ]

        for gatilho in gatilhos:

            if gatilho in texto:
                return True

        return False

    def get_direct_response(self, user_text="", conversation=None):

        if not self.detectar_pedido(user_text):
            return None

        print("🧩 Skill direta ativada: DonateSkill")

        return (
            "Ainda não recebo eventos reais de donate, bits, membros ou superchat nesse fluxo. "
            "Quando essa integração for conectada, eu consigo reagir sem inventar nada."
        )

    def get_context(self, user_text="", conversation=None):

        return None