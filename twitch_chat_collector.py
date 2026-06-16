# -*- coding: utf-8 -*-

# =========================
# 💬 TWITCH CHAT COLLECTOR
# =========================

"""Coletor simples do chat da Twitch para a Diana.

Corrige os pontos frágeis da versão antiga:
- `CHAT_LOG_PATH` agora é resolvido a partir do `PROJECT_ROOT`, então não depende
  da pasta de onde o Python foi chamado.
- Parser IRC aceita mensagens com ou sem IRCv3 tags.
- Adiciona modo `--test-write` para validar se a Diana está lendo o mesmo arquivo.
- Reconexão fecha socket antigo com segurança.
- Logs mostram o caminho absoluto do arquivo escrito.
"""

import os
import re
import socket
import ssl
import sys
import time
import random
from datetime import datetime
from pathlib import Path

from config import PROJECT_ROOT, TWITCH_CHANNEL, CHAT_LOG_PATH, CHAT_MAX_LINES


SERVER = os.getenv("TWITCH_IRC_SERVER", "irc.chat.twitch.tv")
PORT = int(os.getenv("TWITCH_IRC_PORT", "6667"))
USE_SSL = os.getenv("TWITCH_IRC_SSL", "false").lower().strip() in {"1", "true", "yes", "on"}
DEBUG_RAW = os.getenv("TWITCH_COLLECTOR_DEBUG", "false").lower().strip() in {"1", "true", "yes", "on"}
SOCKET_TIMEOUT_SECONDS = float(os.getenv("TWITCH_SOCKET_TIMEOUT_SECONDS", "1.0"))
RECONNECT_SECONDS = float(os.getenv("TWITCH_RECONNECT_SECONDS", "5.0"))


# =========================
# 📁 CAMINHO ABSOLUTO DO LOG
# =========================

def resolver_chat_log_path():
    caminho = Path(CHAT_LOG_PATH)

    if not caminho.is_absolute():
        caminho = Path(PROJECT_ROOT) / caminho

    return caminho.resolve()


CHAT_LOG_ABSOLUTE_PATH = resolver_chat_log_path()


# =========================
# 🧼 LIMPEZA DE MENSAGEM
# =========================

def limpar_texto(texto):
    texto = str(texto or "")
    texto = texto.replace("\r", "")
    texto = texto.replace("\n", " ")
    texto = " ".join(texto.split())
    return texto.strip()


# =========================
# 📝 SALVAR MENSAGEM
# =========================

def salvar_mensagem(usuario, mensagem):
    caminho = CHAT_LOG_ABSOLUTE_PATH
    caminho.parent.mkdir(parents=True, exist_ok=True)

    usuario = limpar_texto(usuario)
    mensagem = limpar_texto(mensagem)

    if not usuario or not mensagem:
        return

    horario = datetime.now().strftime("%H:%M:%S")
    linha = f"[{horario}] {usuario}: {mensagem}"

    linhas = []

    if caminho.exists():
        try:
            linhas = caminho.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            linhas = []

    linhas.append(linha)

    if len(linhas) > CHAT_MAX_LINES:
        linhas = linhas[-CHAT_MAX_LINES:]

    caminho.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print(linha, flush=True)


# =========================
# 🔍 PARSE PRIVMSG
# =========================

def parse_privmsg(raw_message):
    raw_message = str(raw_message or "").strip()

    if not raw_message:
        return None, None

    # Twitch pode enviar tags IRCv3 quando CAP REQ é usado:
    # @badge-info=... :usuario!usuario@usuario.tmi.twitch.tv PRIVMSG #canal :mensagem
    if raw_message.startswith("@") and " " in raw_message:
        raw_message = raw_message.split(" ", 1)[1].strip()

    match = re.match(r"^:([^!\s]+)![^\s]+\s+PRIVMSG\s+#[^\s]+\s+:(.*)$", raw_message)

    if not match:
        return None, None

    usuario = limpar_texto(match.group(1))
    mensagem = limpar_texto(match.group(2))

    if not usuario or not mensagem:
        return None, None

    return usuario, mensagem


# =========================
# 🔌 SOCKET / CONEXÃO
# =========================

def criar_socket():
    sock = socket.create_connection((SERVER, PORT), timeout=10)
    sock.settimeout(SOCKET_TIMEOUT_SECONDS)

    if USE_SSL:
        contexto = ssl.create_default_context()
        sock = contexto.wrap_socket(sock, server_hostname=SERVER)
        sock.settimeout(SOCKET_TIMEOUT_SECONDS)

    return sock


def enviar(sock, texto):
    sock.send((texto + "\r\n").encode("utf-8"))


def conectar_twitch():
    canal = str(TWITCH_CHANNEL or "").lower().strip().replace("#", "")

    if not canal or canal == "seu_canal_aqui":
        print("⚠️ Configure TWITCH_CHANNEL no config.py antes de iniciar.")
        return None

    nick = "justinfan" + str(random.randint(10000, 99999))

    try:
        sock = criar_socket()
    except Exception as e:
        print("⚠️ Não consegui abrir conexão com a Twitch:", e)
        return None

    # Anônimo/read-only. Não envia mensagem no chat; só lê.
    enviar(sock, "PASS SCHMOOPIIE")
    enviar(sock, f"NICK {nick}")
    enviar(sock, "CAP REQ :twitch.tv/commands")
    enviar(sock, f"JOIN #{canal}")

    print(f"💬 Conectando ao chat da Twitch: #{canal}")
    print("💾 Salvando mensagens em:", str(CHAT_LOG_ABSOLUTE_PATH))
    print("Pressione Ctrl+C para encerrar.")

    return sock


def fechar_socket(sock):
    if not sock:
        return

    try:
        sock.close()
    except Exception:
        pass


# =========================
# 🧪 TESTE LOCAL
# =========================

def test_write():
    salvar_mensagem("teste_chat", "Mensagem de teste gravada pelo coletor da Diana.")
    print("✅ Teste escrito em:", str(CHAT_LOG_ABSOLUTE_PATH))
    print("Agora peça para a Diana: lê o chat")


# =========================
# 🔁 LOOP PRINCIPAL
# =========================

def main():
    if "--test-write" in sys.argv:
        test_write()
        return

    sock = conectar_twitch()
    buffer = ""

    while True:
        if sock is None:
            print(f"Tentando reconectar em {RECONNECT_SECONDS:.0f} segundos...")
            time.sleep(RECONNECT_SECONDS)
            sock = conectar_twitch()
            buffer = ""
            continue

        try:
            data = sock.recv(4096).decode("utf-8", errors="ignore")

            if not data:
                print("⚠️ Conexão vazia. Reconectando...")
                fechar_socket(sock)
                sock = None
                buffer = ""
                continue

            buffer += data

            while "\r\n" in buffer:
                raw_message, buffer = buffer.split("\r\n", 1)
                raw_message = raw_message.strip()

                if not raw_message:
                    continue

                if DEBUG_RAW:
                    print("IRC_RAW:", raw_message)

                if raw_message.startswith("PING"):
                    enviar(sock, "PONG :tmi.twitch.tv")
                    continue

                if " NOTICE " in raw_message or " 001 " in raw_message or " 366 " in raw_message:
                    if DEBUG_RAW:
                        print("IRC_INFO:", raw_message)
                    continue

                usuario, mensagem = parse_privmsg(raw_message)

                if usuario and mensagem:
                    salvar_mensagem(usuario, mensagem)

        except socket.timeout:
            continue

        except KeyboardInterrupt:
            print("\nEncerrando coletor da Twitch...")
            fechar_socket(sock)
            break

        except Exception as e:
            print("⚠️ Erro no coletor:", e)
            print(f"Tentando reconectar em {RECONNECT_SECONDS:.0f} segundos...")
            fechar_socket(sock)
            sock = None
            buffer = ""
            time.sleep(RECONNECT_SECONDS)


if __name__ == "__main__":
    main()
