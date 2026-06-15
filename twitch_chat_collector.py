# -*- coding: utf-8 -*-

# =========================
# 💬 TWITCH CHAT COLLECTOR
# =========================

import socket
import time
import random
from datetime import datetime
from pathlib import Path

from config import TWITCH_CHANNEL, CHAT_LOG_PATH, CHAT_MAX_LINES


SERVER = "irc.chat.twitch.tv"
PORT = 6667


# =========================
# 🧼 LIMPEZA DE MENSAGEM
# =========================

def limpar_texto(texto):

    texto = texto.replace("\r", "")
    texto = texto.replace("\n", " ")
    texto = " ".join(texto.split())

    return texto.strip()


# =========================
# 📝 SALVAR MENSAGEM
# =========================

def salvar_mensagem(usuario, mensagem):

    caminho = Path(CHAT_LOG_PATH)
    caminho.parent.mkdir(parents=True, exist_ok=True)

    horario = datetime.now().strftime("%H:%M:%S")
    linha = f"[{horario}] {usuario}: {mensagem}"

    linhas = []

    if caminho.exists():

        try:

            linhas = caminho.read_text(encoding="utf-8").splitlines()

        except Exception:

            linhas = []

    linhas.append(linha)

    if len(linhas) > CHAT_MAX_LINES:
        linhas = linhas[-CHAT_MAX_LINES:]

    caminho.write_text("\n".join(linhas), encoding="utf-8")

    print(linha)


# =========================
# 🔍 PARSE PRIVMSG
# =========================

def parse_privmsg(raw_message):

    if " PRIVMSG " not in raw_message:
        return None, None

    try:

        prefixo, conteudo = raw_message.split(" PRIVMSG ", 1)

        usuario = prefixo.split("!", 1)[0].replace(":", "").strip()

        if " :" not in conteudo:
            return None, None

        mensagem = conteudo.split(" :", 1)[1].strip()
        mensagem = limpar_texto(mensagem)

        if not usuario or not mensagem:
            return None, None

        return usuario, mensagem

    except Exception:

        return None, None


# =========================
# 🔌 CONECTAR TWITCH
# =========================

def conectar_twitch():

    canal = TWITCH_CHANNEL.lower().strip().replace("#", "")

    if not canal or canal == "seu_canal_aqui":

        print("⚠️ Configure TWITCH_CHANNEL no config.py antes de iniciar.")
        return None

    nick = "justinfan" + str(random.randint(10000, 99999))

    sock = socket.socket()
    sock.connect((SERVER, PORT))

    sock.send("PASS SCHMOOPIIE\r\n".encode("utf-8"))
    sock.send(f"NICK {nick}\r\n".encode("utf-8"))
    sock.send(f"JOIN #{canal}\r\n".encode("utf-8"))

    print(f"💬 Conectado ao chat da Twitch: #{canal}")
    print("💾 Salvando mensagens em:", CHAT_LOG_PATH)
    print("Pressione Ctrl+C para encerrar.")

    return sock


# =========================
# 🔁 LOOP PRINCIPAL
# =========================

def main():

    sock = conectar_twitch()

    if sock is None:
        return

    buffer = ""

    while True:

        try:

            data = sock.recv(2048).decode("utf-8", errors="ignore")

            if not data:

                print("⚠️ Conexão vazia. Tentando reconectar em 5 segundos...")
                time.sleep(5)
                sock = conectar_twitch()
                buffer = ""
                continue

            buffer += data

            while "\r\n" in buffer:

                raw_message, buffer = buffer.split("\r\n", 1)

                if raw_message.startswith("PING"):

                    sock.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
                    continue

                usuario, mensagem = parse_privmsg(raw_message)

                if usuario and mensagem:
                    salvar_mensagem(usuario, mensagem)

        except KeyboardInterrupt:

            print("\nEncerrando coletor da Twitch...")

            try:
                sock.close()
            except Exception:
                pass

            break

        except Exception as e:

            print("⚠️ Erro no coletor:", e)
            print("Tentando reconectar em 5 segundos...")

            try:
                sock.close()
            except Exception:
                pass

            time.sleep(5)

            sock = conectar_twitch()
            buffer = ""


if __name__ == "__main__":
    main()