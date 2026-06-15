# -*- coding: utf-8 -*-

# =========================
# 🧭 INTENT ROUTER — SKILLS ANTES DO KNOWLEDGE
# =========================

import re
import unicodedata


def canonicalize_file_typos(text):
    text = str(text or "").strip()
    replacements = [
        (r"\boa\s+rquivos\b", "os arquivos"),
        (r"\boa\s+rquivo\b", "o arquivo"),
        (r"\bor\s+quivos\b", "os arquivos"),
        (r"\bor\s+quivo\b", "o arquivo"),
        (r"\bar\s+quivos\b", "arquivos"),
        (r"\bar\s+quivo\b", "arquivo"),
        (r"\brquivos\b", "arquivos"),
        (r"\brquivo\b", "arquivo"),
        (r"\barquvios\b", "arquivos"),
        (r"\barquvio\b", "arquivo"),
        (r"\barqivos\b", "arquivos"),
        (r"\barqivo\b", "arquivo"),
        (r"\baarquivos\b", "arquivos"),
        (r"\baarquivo\b", "arquivo"),
    ]
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_text(text):
    text = str(text or "").lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^a-z0-9_!.+\- /]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = canonicalize_file_typos(text)
    return text


def is_read_chat_intent(text):
    normalized = normalize_text(text)
    return bool(
        re.search(r"\b(l[eê]|leia|ler|lê|ve|v[eê]|olha|resuma|resume)\b.*\b(chat|mensagem|mensagens)\b", normalized)
        or re.search(r"\b(o\s+que\s+o\s+chat\s+(falou|disse)|tem\s+algo\s+no\s+chat|responde\s+o\s+chat)\b", normalized)
    )


def is_read_file_intent(text):
    normalized = normalize_text(text)

    if re.search(r"\b(l[eê]|leia|ler|lê|abre|abrir|resume|resuma|resumir|ve|v[eê]|ver|olha|analisa|analise|explica|explique)\b.*\b(arquivo|texto|transcricao|transcrição|\.txt|\.md|\.json|\.py|\.csv)\b", normalized):
        return True

    if re.search(r"\b(resume|resuma|resumir|analisa|analise|explica|explique|leia|ler|l[eê]|ve|ver)\b.*\b(ele|isso|esse|essa|agora)\b", normalized):
        return True

    if re.search(r"\b(arquivo|arquivos)\b.*\b(disponiveis|disponivel|leitura|ler|listar|lista|liste)\b", normalized):
        return True

    if re.search(r"\b(lista|liste|me\s+diz|quais|mostra)\b.*\b(arquivo|arquivos)\b", normalized):
        return True

    if re.search(r"\b(primeiro|primeira|segundo|segunda|ultimo|ultima)\s+arquivo\b", normalized):
        return True

    if re.search(r"\b(l[eê]|leia|ler|lê)\b.*\b(primeiro|primeira|segundo|segunda|ultimo|ultima)\b", normalized):
        return True

    # Nome direto com extensão deve ser skill de arquivo, não knowledge.
    if re.search(r"\b\S+\.(txt|md|json|jsonl|csv)\b", normalized):
        return True

    return False


def is_read_screen_intent(text):
    normalized = normalize_text(text)
    return bool(re.search(r"\b(tela|print|screenshot|screen)\b", normalized) and re.search(r"\b(v[eê]|ver|leia|ler|captura|capturar|olha|analisar|analisa)\b", normalized))


def detect_capability(text):
    if is_read_chat_intent(text):
        return "read_chat"
    if is_read_file_intent(text):
        return "read_file"
    if is_read_screen_intent(text):
        return "read_screen"
    return "none"
