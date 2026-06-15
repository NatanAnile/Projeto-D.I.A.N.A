# consulta informações das expressões
from personality.expression_rules import EXPRESSION_RULES


class ExpressionLorebook:

    def build_context(self, user_text):

        user_text = user_text.lower()

        encontrados = []

        for expressao, dados in EXPRESSION_RULES.items():

            if expressao.lower() in user_text:

                encontrados.append(
                    f"""
Expressão: {expressao}

Significado:
{dados["significado"]}

Funções:
{", ".join(dados["funcoes"])}

Tom:
{", ".join(dados["tom"])}

Exemplos:
{" | ".join(dados["exemplos"])}
"""
                )

        if not encontrados:
            return ""

        return "\n".join(encontrados)