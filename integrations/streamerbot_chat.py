# -*- coding: utf-8 -*-

# =========================
# 💬 STREAMER.BOT CHAT OUTPUT
# =========================

import time
import re
from pathlib import Path

from config import (
    CHAT_REPLY_ENABLED,
    CHAT_REPLY_QUEUE_PATH,
    CHAT_REPLY_MAX_CHARS,
    CHAT_BLOCK_LINKS,
    CHAT_ALLOW_CHAOS
)


# =========================
# 🎛️ ESTADO EM TEMPO DE EXECUÇÃO
# =========================

CHAT_RUNTIME_CHAOS_MODE = CHAT_ALLOW_CHAOS


# =========================
# 🎛️ MODO CAOS DO CHAT
# =========================

def set_chat_chaos_mode(enabled):

    global CHAT_RUNTIME_CHAOS_MODE

    CHAT_RUNTIME_CHAOS_MODE = bool(enabled)

    if CHAT_RUNTIME_CHAOS_MODE:
        print("💬 Modo caos do chat: ATIVADO")
    else:
        print("💬 Modo caos do chat: DESATIVADO")


def get_chat_chaos_mode():

    return CHAT_RUNTIME_CHAOS_MODE


# =========================
# 🧼 LIMPAR MENSAGEM PARA CHAT
# =========================

def limpar_mensagem_chat(texto):

    global CHAT_RUNTIME_CHAOS_MODE

    if not texto:
        return ""

    texto = str(texto).strip()

    # Remove marcações internas da Diana.
    texto = re.sub(r"\[Enviado no chat:.*?\]", "", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\[Resumo do chat:.*?\]", "", texto, flags=re.IGNORECASE)

    # Modo seguro: remove links e markdown de link.
    if CHAT_BLOCK_LINKS and not CHAT_RUNTIME_CHAOS_MODE:

        # Markdown link: [texto](url) -> texto
        texto = re.sub(r"\[([^\]]+)\]\((https?://[^\)]+)\)", r"\1", texto)

        # URLs puras
        texto = re.sub(r"https?://\S+", "", texto)

    # Remove markdown visual que polui o chat.
    texto = texto.replace("**", "")
    texto = texto.replace("__", "")
    texto = texto.replace("`", "")

    texto = texto.replace('"', "'")
    texto = texto.replace("\n", " ")

    texto = re.sub(r"\s+", " ", texto)
    texto = texto.strip()

    if len(texto) > CHAT_REPLY_MAX_CHARS:
        texto = texto[:CHAT_REPLY_MAX_CHARS - 3].strip() + "..."

    return texto


# =========================
# 🔎 DETECTAR PEDIDO DE ENVIO AO CHAT
# =========================

def deve_enviar_para_chat(texto_usuario):

    texto = texto_usuario.lower().strip()

    gatilhos = [
        "manda no chat",
        "mandar no chat",
        "envia no chat",
        "enviar no chat",
        "responde no chat",
        "responda no chat",
        "fala no chat",
        "falar no chat",
        "manda isso no chat",
        "manda ela no chat",
        "manda ele no chat",
        "manda a piada no chat",
        "manda essa piada no chat",
        "manda a resposta no chat",
        "manda essa resposta no chat",
        "joga no chat",
        "joga ela no chat",
        "joga isso no chat"
    ]

    for gatilho in gatilhos:

        if gatilho in texto:
            return True

    return False


# =========================
# ✂️ EXTRAIR MENSAGEM DIRETA
# =========================

def extrair_mensagem_direta_chat(texto_usuario):

    if ":" not in texto_usuario:
        return None

    texto_lower = texto_usuario.lower()

    gatilhos = [
        "manda no chat",
        "envia no chat",
        "fala no chat",
        "joga no chat",
        "manda isso no chat",
        "manda ela no chat",
        "manda ele no chat",
        "manda a piada no chat",
        "manda essa piada no chat",
        "manda a resposta no chat",
        "manda essa resposta no chat"
    ]

    if not any(gatilho in texto_lower for gatilho in gatilhos):
        return None

    mensagem = texto_usuario.split(":", 1)[1].strip()

    if not mensagem:
        return None

    return mensagem


# =========================
# 💬 ENVIAR PARA FILA DO CHAT
# =========================

def enviar_mensagem_chat(texto):

    if not CHAT_REPLY_ENABLED:
        return False

    mensagem = limpar_mensagem_chat(texto)

    if not mensagem:
        return False

    queue_path = Path(CHAT_REPLY_QUEUE_PATH)
    queue_path.mkdir(parents=True, exist_ok=True)

    timestamp = int(time.time() * 1000)
    file_path = queue_path / f"diana_chat_{timestamp}.txt"

    try:

        file_path.write_text(mensagem, encoding="utf-8")

        print("💬 Mensagem enviada para fila do chat:", mensagem)

        return True

    except Exception as e:

        print("⚠️ Erro ao enviar mensagem para fila do chat:", e)

        return False