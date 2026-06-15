# -*- coding: utf-8 -*-

# =========================
# 🚦 QUERY GATE
# =========================

import re
import unicodedata


def _normalizar(texto):
    texto = str(texto or "").lower().strip()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(char for char in texto if unicodedata.category(char) != "Mn")
    texto = re.sub(r"[^a-z0-9_%+\- ]+", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


class QueryGate:

    QUERY_PATTERNS = re.compile(
        r"\b(o que e|oque e|como funciona|como pega|como conseguir|como adquirir|"
        r"qual e|qual o|quais|onde fica|onde pega|onde eu pego|me fala|me diz|"
        r"mostra|ensina|explica|explique|lista|liste|conta|conte|quant[ao]s?|"
        r"quero saber|serve para|o que faz|requisitos?|precisa|exige|usa|use|"
        r"primeir[ao]|ultim[ao]|qualquer coisa|aleatori[ao]|tem relacao com|relacionado a)\b"
    )

    SKIP_PATTERNS = re.compile(
        r"\b(vamos testar|bora testar|vamos ver|vamos falar|bora falar|quero falar|"
        r"vamos conversar|bora conversar|estamos prontos|preparad[ao]|comecar|"
        r"tudo bem|precisa ser|voce precisa|seja mais|primeiro precisa|depois criativa|"
        r"esta correto|estao corretas|vamos deixar passar|mudando de assunto|"
        r"vamos mudar de assunto|muda de assunto)\b"
    )

    CONTINUATION_PATTERNS = re.compile(
        r"\b(outra|outro|diferente|mais uma|mais um|a mesma|o mesmo|essa|esse|"
        r"e a area|e a sala|e os requisitos|e o requisito|e onde|e o chefe|"
        r"mais simples|mais direto|de forma engracada|em uma frase)\b"
    )

    HUMOR_PATTERNS = re.compile(
        r"\b(piada|trocadilho|zoeira|zoa|brinca|brincadeira|conta outra|conte outra)\b"
    )

    def decide(self, user_text, has_active_entry=False):
        normalized = _normalizar(user_text)

        if re.search(r"\b(nao precisa consultar|não precisa consultar|sem consultar|nao consulta|não consulta|nao usa knowledge|não usa knowledge|nao busca nada|não busca nada|nao precisa procurar|não precisa procurar|sem procurar|nao procurar no mem0|não procurar no mem0|sem buscar no mem0|nao puxar conhecimento|não puxar conhecimento|sem puxar conhecimento|nao usa conhecimento local|não usa conhecimento local|sem usar conhecimento local|nao usa retrieval|não usa retrieval|ignora retrieval)\b", normalized):
            return {"should_query": False, "reason": "pedido explícito para não consultar base"}

        if re.search(r"\b(testar continuidade|testando continuidade|teste de continuidade|qualquer coisa pra testar|separador)\b", normalized):
            return {"should_query": False, "reason": "fala de controle/teste sem pedido factual"}

        if self.SKIP_PATTERNS.search(normalized):
            return {"should_query": False, "reason": "mensagem conversacional/feedback sem pedido factual"}

        if self.HUMOR_PATTERNS.search(normalized):
            return {"should_query": False, "reason": "pedido criativo/humorístico não consulta base factual"}

        if re.search(r"\b(e o|e a)\s+(celular|mouse|monitor|teclado|console|comida|franquia|doom|metroid|zelda|filme|jogo)\??$", normalized):
            return {"should_query": False, "reason": "consulta curta de memória/fato pessoal", "source": "owner"}

        if re.search(r"\b(?:troca|muda|atualiza|corrige)(?:\s+ai)?\s*:?\s+(?:o\s+|a\s+)?(?:meu|minha)\s+[a-z0-9_ %+-]{2,60}\s+favorit[oa]s?\s+(?:para|pra|agora\s+e)\s+", normalized):
            return {"should_query": False, "reason": "atualização de memória/fato pessoal", "source": "owner", "operation": "update"}

        if re.search(r"\bna\s+real\s+(?:o\s+|a\s+)?[a-z0-9_ %+-]{2,60}\s+favorit[oa]s?\s+e\s+", normalized):
            return {"should_query": False, "reason": "atualização de memória/fato pessoal", "source": "owner", "operation": "update"}

        if re.search(r"\b(?:meu|minha)\s+[a-z0-9_ %+-]{2,60}\s+favorit[oa]s?\s+nao\s+e\s+.+?\s+e\s+", normalized):
            return {"should_query": False, "reason": "correção de memória/fato pessoal", "source": "owner", "operation": "update"}

        if re.search(r"\b(meu|minha|meus|minhas)\b", normalized) and re.search(r"\bfavorit[oa]s?(?:\s+(?:de|do|da|em|no|na|pra|para|pro)\s+[a-z0-9_ %+-]+)?\s+(e|eh|continua\s+sendo|segue\s+sendo|agora\s+e|sao)\b", normalized):
            return {"should_query": False, "reason": "registro de memória/fato pessoal", "source": "owner", "operation": "remember"}

        if re.search(r"\b(?:pra|para|pro)\s+[a-z0-9_ %+-]{2,60}\s*,?\s+(?:o\s+)?meu\s+favorit[oa]s?\s+(?:e|eh|continua\s+sendo|segue\s+sendo)\b", normalized):
            return {"should_query": False, "reason": "registro de memória/fato pessoal", "source": "owner", "operation": "remember"}

        if re.search(r"^\s*/?mem0\s+remember\s+", normalized):
            return {"should_query": False, "reason": "registro de memória/fato pessoal", "source": "owner", "operation": "remember"}

        if re.search(r"^qual\s+[a-z0-9_ %+-]{2,80}\s+(?:ficou\s+na\s+real|corrigid[oa]\s+ficou|atualizad[oa]\s+ficou|ficou\s+depois)", normalized):
            return {"should_query": False, "reason": "consulta de memória/fato pessoal", "source": "owner"}

        if re.search(r"\b(meu|minha|meus|minhas|do pai|sobre mim|quem sou eu|eu prefiro|eu falei|eu disse|eu citei|ficou salvo|ficou salva|ficou anotado|ficou anotada|ficou registrado|ficou registrada|deixei anotado|deixei anotada|deixei salvo|deixei salva|tinha falado|tinha citado|depois dessa atualizacao|depois do esquece|sobre [a-z0-9_ %+-]+ o que ficou)\b", normalized) and re.search(r"\b(favorit\w*|qual|que|quais|lembra|sabe|gosto|curto|prefiro|falei|disse|citei|salvo|salva|anotado|anotada|registrado|registrada|corrigido|corrigida|ficou|na real)\b", normalized):
            return {"should_query": False, "reason": "consulta de memória/fato pessoal", "source": "owner"}

        if re.search(r"^e\s+(?:o|a)\s+[a-z0-9_ %+-]{2,80}(?:\s+agora|\s+mesmo|\s+que\s+eu\s+curto|\s+que\s+eu\s+gosto)?$", normalized):
            return {"should_query": False, "reason": "consulta curta de memória/fato pessoal", "source": "owner"}

        if re.search(r"^e\s+sobre\s+[a-z0-9_ %+-]{2,80}$", normalized):
            return {"should_query": False, "reason": "consulta curta de memória/fato pessoal", "source": "owner"}

        if has_active_entry and self.CONTINUATION_PATTERNS.search(normalized):
            return {"should_query": True, "reason": "continuação de consulta ativa"}

        if self.QUERY_PATTERNS.search(normalized):
            return {"should_query": True, "reason": "intenção explícita de consulta"}

        return {"should_query": False, "reason": "nenhuma intenção de consulta detectada"}
