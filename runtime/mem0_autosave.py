# -*- coding: utf-8 -*-

# =========================
# 🧠 MEM0 AUTOSAVE HELPERS
# =========================

import re


def normalizar_mem0_autosave(text):
    text = str(text or "").lower().strip()
    text = re.sub(r"[^a-záàâãéêíóôõúç0-9 _/-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def limpar_valor_memoria(valor):
    valor = str(valor or "").strip()
    if "?" in valor:
        return ""
    valor = re.split(r"\b(mas qual|qual desses|qual dos|e qual|sao cinco|são cinco)\b", valor, maxsplit=1, flags=re.IGNORECASE)[0]
    valor = re.split(r"[.!?]", valor, maxsplit=1)[0]
    valor = valor.strip(" .,!?:;\"\'")
    valor = re.sub(r"^(o|a|os|as)\s+", "", valor).strip()
    valor = re.sub(r"^(muito|bastante|demais)\s+", "", valor, flags=re.IGNORECASE).strip()
    valor = re.sub(r"\s+demais$", "", valor, flags=re.IGNORECASE).strip()
    if not valor or len(valor) > 80:
        return ""
    return valor


def chave_generica_memoria(categoria):
    categoria = normalizar_mem0_autosave(categoria)
    categoria = re.sub(r"[^a-z0-9_ ]+", " ", categoria)
    categoria = re.sub(r"\s+", "_", categoria).strip("_")
    categoria = re.sub(r"^(?:o|a|os|as)_+", "", categoria)
    if not categoria or len(categoria) > 40:
        return ""
    bloqueados = {"coisa", "negocio", "bagulho", "isso", "aquilo"}
    if categoria in bloqueados:
        return ""
    return categoria + "_favorito"


def extrair_memoria_direta_mem0(text):
    texto_original = str(text or "").strip()
    normalized = normalizar_mem0_autosave(texto_original)

    patterns = [
        (r"\b(?:o )?meu filme alien favorito (?:é|e|eh)\s+(.+)$", "filme_alien_favorito"),
        (r"\bmeu filme favorito (?:é|e|eh)\s+(.+)$", "filme_favorito"),
        (r"\bmeu jogo favorito (?:é|e|eh)\s+(.+)$", "jogo_favorito"),
        (r"\bminha comida favorita (?:é|e|eh)\s+(.+)$", "comida_favorita"),
        (r"\bme chama de\s+(.+)$", "apelido_preferido"),
        (r"\bpode me chamar de\s+(.+)$", "apelido_preferido"),
    ]

    gosto_patterns = [
        r"\b(?:eu\s+)?gosto\s+muito\s+de\s+(.+)$",
        r"\b(?:eu\s+)?gosto\s+bastante\s+de\s+(.+)$",
        r"\b(?:eu\s+)?gosto\s+de\s+(.+)$",
        r"\b(?:eu\s+)?curto\s+muito\s+(.+)$",
        r"\b(?:eu\s+)?curto\s+demais\s+(.+)$",
        r"\b(?:eu\s+)?curto\s+(.+)$",
        r"\btambém\s+gosto\s+de\s+(.+)$",
        r"\btambem\s+gosto\s+de\s+(.+)$",
        r"\btambém\s+curto\s+(.+)$",
        r"\btambem\s+curto\s+(.+)$",
    ]
    for pattern in gosto_patterns:
        match = re.search(pattern, normalized)
        if match:
            value = limpar_valor_memoria(match.group(1))
            if value:
                return f"gosta_de: {value}"

    favor_verb = r"(?:é|e|eh|continua\s+sendo|segue\s+sendo|agora\s+é|agora\s+e|agora\s+eh)"
    contexto = r"(?:\s+(?:de|do|da|dos|das|em|no|na|nos|nas|pra|para|pro|nessa|nesse)\s+[a-záàâãéêíóôõúç0-9_ %+.-]{2,80})?"
    favorite_patterns = [
        r"\b(?:pra|para|pro)\s+([a-záàâãéêíóôõúç0-9_ %+.-]{2,60})\s*,?\s+(?:o\s+)?meu\s+favorit[oa]s?\s+" + favor_verb + r"\s+(.+)$",
        r"\b(?:pra|para|pro)\s+([a-záàâãéêíóôõúç0-9_ %+.-]{2,60})\s*,?\s+(?:a\s+)?minha\s+favorit[oa]s?\s+" + favor_verb + r"\s+(.+)$",
        r"\b(?:o\s+)?meu\s+([a-záàâãéêíóôõúç0-9_ %+.-]{2,60})\s+favorit[oa]s?" + contexto + r"\s+" + favor_verb + r"\s+(.+)$",
        r"\b(?:a\s+)?minha\s+([a-záàâãéêíóôõúç0-9_ %+.-]{2,60})\s+favorit[oa]s?" + contexto + r"\s+" + favor_verb + r"\s+(.+)$",
    ]

    for pattern in favorite_patterns:
        generic_match = re.search(pattern, normalized)
        if generic_match:
            key = chave_generica_memoria(generic_match.group(1))
            value = limpar_valor_memoria(generic_match.group(2))
            if value in ["motola", "motorola"] or ("celular" in key and "motorola" in value):
                value = "Motorola"
            if "codec" in key:
                low = normalizar_mem0_autosave(value)
                if "av1" in low:
                    value = "av1"
                elif "h 265" in low or "h.265" in low or "h265" in low:
                    value = "h 265"
                elif "h 264" in low or "h.264" in low or "h264" in low:
                    value = "h 264"
            if key and value:
                return f"{key}: {value}"

    for pattern, key in patterns:
        match = re.search(pattern, normalized)
        if not match:
            continue
        value = limpar_valor_memoria(match.group(1))
        if value in ["motola", "motorola"] or ("celular" in key and "motorola" in value):
            value = "Motorola"
        if key == "filme_alien_favorito":
            low = normalizar_mem0_autosave(value)
            if "alien 2" in low or "aliens" in low or "resgate" in low:
                value = "Aliens: O Resgate"
        if value:
            return f"{key}: {value}"

    return ""


def deve_salvar_mem0_auto(text, response, smart_filter=True, min_chars=12):
    if not smart_filter:
        return True

    normalized = normalizar_mem0_autosave(text)
    if len(normalized) < int(min_chars or 0):
        return False

    tokens = set(normalized.split())
    simple_tokens = {
        "oi", "olá", "ola", "e", "aí", "ai", "eai", "eae", "fala", "salve",
        "bom", "boa", "dia", "tarde", "noite", "sim", "não", "nao", "ok",
        "blz", "beleza", "valeu", "obrigado", "obrigada", "kk", "kkk", "haha"
    }
    if tokens and tokens.issubset(simple_tokens) and len(tokens) <= 5:
        return False

    if normalized.endswith("?") or re.search(r"\b(qual|quais|quem|quando|onde|como|por que|porque)\b", normalized):
        has_memory_write_signal = re.search(
            r"\b(lembra|memoriza|salva|guarda|anota|meu|minha|meus|minhas|eu sou|eu gosto|eu curto|eu prefiro)\b",
            normalized,
        )
        if not has_memory_write_signal:
            return False

    memory_patterns = [
        r"\b(lembra|memoriza|salva|guarda|anota)\b",
        r"\b(meu|minha|meus|minhas)\b.+\b(eh|é|era|sao|são|foi|fica|vai ser)\b",
        r"\b(eu sou|eu era|eu gosto|eu curto|eu prefiro|eu odeio|eu nao gosto|eu não gosto|também gosto|tambem gosto|também curto|tambem curto|gosto bastante|curto demais)\b",
        r"\b(pode me chamar|me chama de|troca .+ para|troca .+ pra|atualiza .+ agora|agora .+ eh|agora .+ é|continua sendo|segue sendo)\b",
        r"\b(o|a) .+ (eh|é) .+\b",
    ]
    return any(re.search(pattern, normalized) for pattern in memory_patterns)
