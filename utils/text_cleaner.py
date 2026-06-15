# -*- coding: utf-8 -*-

# =========================
# 🧼 TEXT CLEANER
# =========================

import re


def remove_emojis(texto):

    if not texto:
        return ""

    emoji_pattern = re.compile(
        "["
        "\U0001F300-\U0001F5FF"
        "\U0001F600-\U0001F64F"
        "\U0001F680-\U0001F6FF"
        "\U0001F700-\U0001F77F"
        "\U0001F780-\U0001F7FF"
        "\U0001F800-\U0001F8FF"
        "\U0001F900-\U0001F9FF"
        "\U0001FA00-\U0001FA6F"
        "\U0001FA70-\U0001FAFF"
        "\U00002700-\U000027BF"
        "\U00002600-\U000026FF"
        "]+",
        flags=re.UNICODE
    )

    texto = emoji_pattern.sub("", str(texto))
    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()


def remove_non_latin_blocks(texto):

    if not texto:
        return ""

    resultado = ""

    for char in str(texto):

        code = ord(char)

        if 0x4E00 <= code <= 0x9FFF:
            continue

        if 0x3040 <= code <= 0x30FF:
            continue

        if 0xAC00 <= code <= 0xD7AF:
            continue

        if 0x3000 <= code <= 0x303F:
            continue

        if 0xFF00 <= code <= 0xFFEF:
            continue

        resultado += char

    return resultado


def clean_for_tts(text):

    text = str(text or "").lower()

    text = re.sub(r"\*.*?\*", "", text)
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"[^\w\s,.!?áàâãéêíóôõúç]", "", text)
    text = re.sub(r"[!?.,]{2,}", ".", text)
    text = re.sub(r"\s+[!?.,]\s+", " ", text)
    text = re.sub(r"!{2,}", ".", text)
    text = re.sub(r"\?{2,}", ".", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()
