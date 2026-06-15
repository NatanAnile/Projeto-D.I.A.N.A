# -*- coding: utf-8 -*-

# =========================
# 👁️ READ SCREEN SKILL
# =========================

from skills.base_skill import BaseSkill, SkillContext
from integrations.screen_capture import capturar_tela


class ReadScreenSkill(BaseSkill):

    def __init__(self):

        context = SkillContext(
            skill_name="ReadScreenSkill",
            min_cooldown=0,
            max_cooldown=0
        )

        super().__init__(context)

        self.last_screenshot_path = None

    def detectar_pedido(self, user_text):

        texto = user_text.lower().strip()

        gatilhos = [
            "olha a tela",
            "vê a tela",
            "ve a tela",
            "enxerga a tela",
            "o que está na tela",
            "o que esta na tela",
            "analisa a tela",
            "vê o jogo",
            "ve o jogo",
            "tira um print",
            "captura a tela",
            "print da tela"
        ]

        for gatilho in gatilhos:

            if gatilho in texto:
                return True

        return False

    def get_direct_response(self, user_text="", conversation=None, force=False):

        if not force and not self.detectar_pedido(user_text):
            return None

        print("🧩 Skill direta ativada: ReadScreenSkill")

        screenshot_path, erro = capturar_tela()

        if erro:

            return (
                "Tentei capturar a tela, Neitan, mas deu erro: "
                + erro
            )

        self.last_screenshot_path = screenshot_path

        return (
            "Capturei um print da tela em "
            + screenshot_path
            + ". Ainda não estou analisando imagem diretamente, mas a captura sob demanda já está funcionando."
        )

    def get_context(self, user_text="", conversation=None):

        return None