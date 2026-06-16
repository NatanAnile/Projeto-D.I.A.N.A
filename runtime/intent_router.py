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
        (r"\becolhe\b", "escolhe"),
        (r"\barrtigo\b", "artigo"),
        (r"\bartgo\b", "artigo"),
        (r"\barrtigos\b", "artigos"),
        (r"\bvoc~e\b", "voce"),
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

    chat_terms = r"(?:chat|live chat|mensagem|mensagens|bate papo|bate-papo)"
    action_terms = (
        r"(?:le|leia|ler|ve|ver|olha|olhar|resuma|resume|resumir|"
        r"confere|conferir|checa|checar|consulta|consultar|"
        r"verifica|verificar|mostra|mostrar)"
    )

    if re.search(r"\b" + action_terms + r"\b.*\b" + chat_terms + r"\b", normalized):
        return True

    question_patterns = [
        r"\bconsegue\s+(ver|ler|checar|conferir|acessar)\b.*\b" + chat_terms + r"\b",
        r"\b" + chat_terms + r"\b.*\b(tem|falou|disse|mandou|enviou|chegou|mexeu)\b",
        r"\btem\s+(algo|alguma\s+coisa|mensagem|mensagens)\s+(no|do)\s+chat\b",
        r"\bve\s+se\s+tem\b.*\b" + chat_terms + r"\b",
        r"\bverifica\s+se\s+tem\b.*\b" + chat_terms + r"\b",
        r"\bo\s+que\s+o\s+chat\s+(falou|disse|mandou)\b",
        r"\bo\s+que\s+(estao|tao)\s+falando\s+no\s+chat\b",
        r"\balguem\s+(falou|disse|mandou|perguntou)\b.*\bchat\b",
    ]

    return any(re.search(pattern, normalized) for pattern in question_patterns)


def is_repeat_last_operational_task_intent(text):
    normalized = normalize_text(text)

    repeat_patterns = [
        r"\btenta\s+de\s+novo\b",
        r"\btente\s+de\s+novo\b",
        r"\bfaz\s+de\s+novo\b",
        r"\bfazer\s+de\s+novo\b",
        r"\brepete\b",
        r"\brepita\b",
        r"\bmais\s+uma\s+vez\b",
        r"\bde\s+novo\b",
        r"\btenta\s+outra\s+vez\b",
        r"\btente\s+outra\s+vez\b",
        r"\broda\s+de\s+novo\b",
        r"\bexecuta\s+de\s+novo\b",
        r"\bmanda\s+de\s+novo\b",
        r"\bvai\s+de\s+novo\b",
    ]

    return any(re.search(pattern, normalized) for pattern in repeat_patterns)


def is_read_file_intent(text):
    normalized = normalize_text(text)

    file_terms = r"(?:arquivo|arquivos|texto|transcricao|read_files|\.txt|\.md|\.json|\.jsonl|\.py|\.csv)"
    action_terms = r"(?:le|leia|ler|abre|abrir|resume|resuma|resumir|ve|ver|olha|analisa|analise|explica|explique|interpreta|interprete|fala|fale|diz|lista|liste|listar|mostra|mostrar|escolhe|escolha|pega|pegar)"

    if re.search(r"\b" + action_terms + r"\b.*\b" + file_terms + r"\b", normalized):
        return True

    # Arquivos conhecidos podem ser pedidos sem a palavra "arquivo".
    if re.search(r"\b(resume|resuma|resumir|analisa|analise|explica|explique|le|leia|ler)\b.*\b(artigo\s+cientifico|artigo|roteiro|piada|live|transcricao)\b", normalized):
        return True

    # Listagem de pasta/read_files.
    if re.search(r"\b(arquivo|arquivos|read_files)\b.*\b(quais|qual|tem|existem|disponiveis|disponivel|lista|liste|listar|mostra|mostrar)\b", normalized):
        return True

    if re.search(r"\b(quais|qual|me\s+fala|me\s+diz|lista|liste|mostra)\b.*\b(arquivo|arquivos|read_files)\b", normalized):
        return True

    if re.search(r"\b(escolhe|escolha|pega|pegue)\b.*\barquivo\b", normalized):
        return True

    if re.search(r"\b(no|do|nesse|neste|desse|deste)\s+arquivo\b.*\b(identifica|identifique|acha|ache|encontra|encontre|ponto\s+critico|ultima\s+frase|primeira\s+frase|entendeu|entende|resume|analisa|explica)\b", normalized):
        return True

    if re.search(r"\b(o\s+que\s+(voce|você)\s+entendeu|me\s+diz\s+o\s+que\s+entendeu|me\s+fala\s+o\s+que\s+entendeu)\b.*\b(arquivo|texto|dele|disso|desse|deste)\b", normalized):
        return True

    if re.search(r"\b(resume|resuma|resumir|analisa|analise|explica|explique|interpreta|interprete|leia|ler|le|ve|ver)\b.*\b(ele|isso|esse|essa|desse|deste|dele|arquivo|texto|agora)\b", normalized):
        return True

    if re.search(r"\b(primeiro|primeira|segundo|segunda|ultimo|ultima)\s+arquivo\b", normalized):
        return True

    if re.search(r"\b(le|leia|ler)\b.*\b(primeiro|primeira|segundo|segunda|ultimo|ultima)\b", normalized):
        return True

    if re.search(r"\b\S+\.(txt|md|json|jsonl|csv)\b", normalized):
        return True

    return False


def is_read_screen_intent(text):
    normalized = normalize_text(text)
    return bool(re.search(r"\b(tela|print|screenshot|screen)\b", normalized) and re.search(r"\b(v[eê]|ver|leia|ler|captura|capturar|olha|analisar|analisa)\b", normalized))


def detect_capability(text):
    if is_read_chat_intent(text):
        return "read_chat"
    if is_repeat_last_operational_task_intent(text):
        return "repeat_last_operational_task"
    if is_read_file_intent(text):
        return "read_file"
    if is_read_screen_intent(text):
        return "read_screen"
    return "none"
