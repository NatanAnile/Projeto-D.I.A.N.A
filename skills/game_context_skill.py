# -*- coding: utf-8 -*-

# =========================
# 🎮 GAME CONTEXT SKILL
# =========================

from skills.base_skill import BaseSkill, SkillContext


class GameContextSkill(BaseSkill):

    def __init__(self):

        context = SkillContext(
            skill_name="GameContextSkill",
            min_cooldown=0,
            max_cooldown=0
        )

        super().__init__(context)

    def detectar_pedido(self, user_text):

        texto = user_text.lower().strip()

        gatilhos = [
            "qual é o desafio",
            "qual e o desafio",
            "o que eu estou jogando",
            "o que eu to jogando",
            "o que está acontecendo no jogo",
            "o que esta acontecendo no jogo",
            "contexto do jogo",
            "estado do jogo"
        ]

        for gatilho in gatilhos:

            if gatilho in texto:
                return True

        return False

    def get_context(self, user_text="", conversation=None):

        if not self.detectar_pedido(user_text):
            return None

        print("🧩 Skill ativada: GameContextSkill")

        return (
            "CAPACIDADE SOLICITADA: GameContextSkill\n"
            "Status: ainda não conectada.\n"
            "A Diana ainda não recebe automaticamente o estado atual do jogo.\n"
            "Não invente fase, boss, item, tentativa ou desafio atual.\n"
            "Responda dizendo que ainda precisa receber o contexto do jogo."
        )