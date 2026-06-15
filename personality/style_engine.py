# -*- coding: utf-8 -*-

# =========================
# 🎭 STYLE ENGINE
# =========================

import re

from personality.style_dictionary import StyleDictionary


class StyleEngine:

    def __init__(self):

        self.dictionary = StyleDictionary()

    # =========================
    # 🧼 LIMPEZA DE ESTILO
    # =========================

    def limpar_excessos(self, text):

        if not text:
            return ""

        text = re.sub(r"\s+", " ", text)

        text = text.replace(" ,", ",")
        text = text.replace(" .", ".")
        text = text.replace(" !", "!")
        text = text.replace(" ?", "?")

        text = text.replace("catapimbas.", "catapimbas!")
        text = text.replace("Catapimbas.", "Catapimbas!")

        return text.strip()

    # =========================
    # 📚 CONSULTA DIRETA DE ESTILO
    # =========================

    def responder_consulta_estilo(self, user_text):

        texto = user_text.lower().strip()

        gatilhos = [
            "o que significa",
            "que significa",
            "significa o que",
            "pra que eu uso",
            "para que eu uso",
            "eu uso o termo",
            "o que quer dizer"
        ]

        if not any(gatilho in texto for gatilho in gatilhos):
            return None

        for termo in self.dictionary.all_terms():

            if termo in texto:

                info = self.dictionary.get(termo)

                if not info:
                    continue

                significado = info.get("meaning", "")
                uso = info.get("recommended_use", "")
                tipo = info.get("type", "expressao")

                resposta = f'"{termo}" é um termo do seu jeito de falar, do tipo {tipo}.'

                if significado:
                    resposta += f" Significa: {significado}"

                if uso:
                    resposta += f" Uso recomendado: {uso}"

                return resposta

        return None

    # =========================
    # 📚 CONTEXTO DE ESTILO
    # =========================

    def get_style_context(self, user_text):

        context = self.dictionary.get_context_for_prompt(user_text)

        if not context:
            return ""

        return (
            "\n\nReferencias de estilo relevantes:\n"
            + context
            + "\nUse isso apenas se combinar naturalmente com a resposta."
            + "\nNao invente significado para esses termos."
            + "\nSe o usuario perguntar o significado de um termo, use exatamente o significado listado."
            + "\nNao force bordoes."
        )

    # =========================
    # ✨ ENRIQUECER RESPOSTA
    # =========================

    def enriquecer_resposta(self, response):

        response = self.limpar_excessos(response)

        return response