# -*- coding: utf-8 -*-

# =========================
# 🎙️ DIANA HOST MODE
# =========================

import re
import time
from pathlib import Path

from config import (
    HOST_MODE_ENABLED,
    HOST_SEND_TO_CHAT,
    HOST_MODE_KIND,
    HOST_CHAT_LOG_PATH,
    OWNER_USERS,
    BOT_USERS,
    HOST_COOLDOWN_SECONDS,
    HOST_IDLE_SECONDS,
    HOST_MAX_LINES_READ,
    HOST_MAX_CANDIDATES,
    HOST_MAX_RESPONSE_CHARS,
    HOST_MIN_MESSAGE_LENGTH,
    HOST_IGNORE_PREFIXES,
    HOST_USER_COOLDOWN_SECONDS,
    HOST_IDLE_STREAK_LIMIT,
    HOST_DEBUG,
    HOST_MIN_SCORE_TO_RESPOND,
    HOST_PRIORITY_SCORE,
    HOST_SAME_USER_STREAK_LIMIT
)


class ChatHostMode:

    def __init__(self, llm, clean_response_fn=None, send_chat_fn=None):

        self.llm = llm
        self.clean_response_fn = clean_response_fn
        self.send_chat_fn = send_chat_fn

        self.enabled = HOST_MODE_ENABLED
        self.send_to_chat = HOST_SEND_TO_CHAT
        self.mode = self.normalizar_modo(HOST_MODE_KIND)

        self.chat_log_path = Path(HOST_CHAT_LOG_PATH)

        self.owner_users = self.normalizar_lista(OWNER_USERS)
        self.bot_users = self.normalizar_lista(BOT_USERS)

        self.seen_keys = set()

        self.last_tick_time = 0
        self.last_response_time = 0
        self.last_idle_time = 0

        self.user_last_response = {}
        self.last_answered_user = ""
        self.same_user_streak = 0
        self.idle_streak = 0

        self.context_history = []
        self.context_history_limit = 8

    # =========================
    # 🧼 UTIL
    # =========================

    def normalizar_lista(self, itens):

        resultado = []

        for item in itens:
            resultado.append(str(item).lower().strip())

        return resultado

    def normalize(self, texto):

        texto = str(texto).lower().strip()
        texto = re.sub(r"\s+", " ", texto)

        return texto

    def normalizar_modo(self, value):

        value = str(value or "autonomous").lower().strip()

        aliases = {
            "auto": "autonomous",
            "autonomo": "autonomous",
            "autônomo": "autonomous",
            "autonomous": "autonomous",
            "read": "read_response",
            "leitura": "read_response",
            "leitura_resposta": "read_response",
            "read_response": "read_response"
        }

        return aliases.get(value, "autonomous")

    # =========================
    # 🧠 CONTEXTO CURTO DO HOST
    # =========================

    def adicionar_contexto(self, role, user, message):

        role = str(role or "").strip().upper()
        user = str(user or "").strip()
        message = str(message or "").strip()

        if not message:
            return

        self.context_history.append({
            "role": role,
            "user": user,
            "message": message,
            "time": time.time()
        })

        if len(self.context_history) > self.context_history_limit:
            self.context_history = self.context_history[-self.context_history_limit:]

    def registrar_mensagem_no_contexto(self, item):

        if not item:
            return

        self.adicionar_contexto(
            role=item.get("role", "CHAT_USER"),
            user=item.get("user", "chat"),
            message=item.get("message", "")
        )

    def formatar_contexto_host(self):

        if not self.context_history:
            return "Nenhum contexto recente do Host Mode ainda."

        linhas = []

        for item in self.context_history[-self.context_history_limit:]:

            role = item.get("role", "CHAT_USER")
            user = item.get("user", "chat")
            message = item.get("message", "")

            if role == "DIANA":
                linhas.append("DIANA: " + message)
            else:
                linhas.append(role + " " + user + ": " + message)

        return "\n".join(linhas)

    def mensagem_pede_correcao_de_contexto(self, item):

        if not item:
            return False

        text = self.normalize(item.get("message", ""))

        sinais = [
            "olha o contexto",
            "ve o contexto",
            "vê o contexto",
            "nao estamos",
            "não estamos",
            "não era isso",
            "nao era isso",
            "presta atenção",
            "presta atencao",
            "contexto"
        ]

        return any(sinal in text for sinal in sinais)

    # =========================
    # 🎛️ CONTROLE
    # =========================

    def set_enabled(self, value):

        self.enabled = bool(value)

        if self.enabled:
            self.marcar_chat_atual_como_lido()
            self.last_response_time = time.time()
            self.idle_streak = 0
            self.context_history = []
            print("\n🎙️ Host Mode: ATIVADO")
            print("🎙️ Host Mode modo:", self.mode)
        else:
            print("\n🎙️ Host Mode: DESATIVADO")

    def set_mode(self, value):

        self.mode = self.normalizar_modo(value)

        if self.mode == "autonomous":
            print("\n🎙️ Host Mode modo: AUTÔNOMO")
        else:
            print("\n🎙️ Host Mode modo: LEITURA E RESPOSTA AUTOMÁTICA")

    def set_send_to_chat(self, value):

        self.send_to_chat = bool(value)

        if self.send_to_chat:
            print("\n🎙️ Host Mode envio: CHAT REAL")
        else:
            print("\n🎙️ Host Mode envio: TREINO SEGURO")

    def get_status_text(self):

        status = "ATIVADO" if self.enabled else "DESATIVADO"
        envio = "CHAT REAL" if self.send_to_chat else "TREINO SEGURO"
        modo = "AUTÔNOMO" if self.mode == "autonomous" else "LEITURA E RESPOSTA AUTOMÁTICA"

        return (
            "🎙️ Host Mode\n"
            + "Status: "
            + status
            + "\nModo: "
            + modo
            + "\nEnvio: "
            + envio
            + "\nCooldown geral: "
            + str(HOST_COOLDOWN_SECONDS)
            + "s\nCooldown por usuário: "
            + str(HOST_USER_COOLDOWN_SECONDS)
            + "s\nIdle: "
            + str(HOST_IDLE_SECONDS)
            + "s\nIdle streak: "
            + str(self.idle_streak)
            + "/"
            + str(HOST_IDLE_STREAK_LIMIT)
            + "\nMensagens vistas: "
            + str(len(self.seen_keys))
        )

    # =========================
    # 👤 CLASSIFICAR AUTOR
    # =========================

    def classificar_autor(self, user):

        user_norm = self.normalize(user)

        if user_norm in self.bot_users:
            return "BOT"

        if user_norm in self.owner_users:
            return "OWNER"

        return "CHAT_USER"

    # =========================
    # 📖 LER CHAT
    # =========================

    def read_chat_lines(self):

        if not self.chat_log_path.exists():
            return []

        try:

            with open(self.chat_log_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

        except Exception as e:

            print("\n⚠️ Host Mode não conseguiu ler o chat:", e)
            return []

        lines = [line.strip() for line in lines if line.strip()]

        if len(lines) > HOST_MAX_LINES_READ:
            lines = lines[-HOST_MAX_LINES_READ:]

        return lines

    def parse_line(self, line):

        match = re.match(r"^\[(.*?)\]\s+([^:]+):\s*(.*)$", line)

        if not match:
            return None

        timestamp = match.group(1).strip()
        user = match.group(2).strip()
        message = match.group(3).strip()

        if not timestamp or not user or not message:
            return None

        role = self.classificar_autor(user)
        risk = self.classificar_risco_mensagem(message)

        return {
            "timestamp": timestamp,
            "user": user,
            "role": role,
            "risk": risk,
            "message": message,
            "raw": line
        }

    def criar_key(self, item):

        return (
            item["timestamp"]
            + "|"
            + item["user"]
            + "|"
            + item["message"]
        )

    def marcar_chat_atual_como_lido(self):

        lines = self.read_chat_lines()

        for line in lines:

            item = self.parse_line(line)

            if not item:
                continue

            self.seen_keys.add(self.criar_key(item))

        if HOST_DEBUG:
            print("\n🎙️ Host Mode marcou chat atual como lido:", len(self.seen_keys))

    def get_new_messages(self):

        lines = self.read_chat_lines()

        new_messages = []

        for line in lines:

            item = self.parse_line(line)

            if not item:
                continue

            key = self.criar_key(item)

            if key in self.seen_keys:
                continue

            self.seen_keys.add(key)
            new_messages.append(item)

        return new_messages

    def get_recent_messages(self):

        lines = self.read_chat_lines()
        messages = []

        for line in lines:

            item = self.parse_line(line)

            if not item:
                continue

            messages.append(item)
            self.seen_keys.add(self.criar_key(item))

        if len(messages) > HOST_MAX_CANDIDATES:
            messages = messages[-HOST_MAX_CANDIDATES:]

        return messages

    # =========================
    # 🔞 CLASSIFICAR RISCO
    # =========================

    def classificar_risco_mensagem(self, message):

        text = self.normalize(message)

        pesado = [
            "vou enfiar",
            "enfiar minhas",
            "enfiar meu",
            "gozar",
            "gozei",
            "sexo",
            "transar",
            "estupr",
            "pedofil",
            "porn",
            "nude",
            "pelado",
            "pelada"
        ]

        adulto_leve = [
            "bunda",
            "bolas",
            "pau",
            "peito",
            "tesão",
            "tesao",
            "safado",
            "safada",
            "sus",
            "aceStare".lower()
        ]

        ofensivo = [
            "se mata",
            "morre",
            "racist",
            "nazista",
            "hitler",
            "macaco",
            "retardado"
        ]

        for termo in ofensivo:

            if termo in text:
                return "PESADO"

        for termo in pesado:

            if termo in text:
                return "PESADO"

        for termo in adulto_leve:

            if termo in text:
                return "ADULTO_LEVE"

        return "NORMAL"

    # =========================
    # 🧹 FILTRO LEVE ANTI-LIXO
    # =========================

    def usuario_em_cooldown(self, item):

        if item["role"] == "OWNER":
            return False

        user = self.normalize(item["user"])
        now = time.time()

        last = self.user_last_response.get(user, 0)

        if now - last < HOST_USER_COOLDOWN_SECONDS:
            return True

        return False

    def should_ignore_message(self, item):

        role = item["role"]
        message = item["message"].strip()
        text = self.normalize(message)

        if role == "BOT":
            return True

        if len(message) < HOST_MIN_MESSAGE_LENGTH:
            return True

        for prefix in HOST_IGNORE_PREFIXES:

            if message.startswith(prefix):
                return True

        mensagens_vazias = [
            "kk",
            "kkk",
            "kkkk",
            "kkkkk",
            "lol",
            "rs",
            "rsrs",
            "haha",
            "hehe"
        ]

        if text in mensagens_vazias:
            return True

        if len(text) > 5 and len(set(text)) <= 2:
            return True

        return False

    def tokens_significativos(self, text):

        stopwords = {
            "que", "com", "para", "pra", "por", "uma", "uns", "das", "dos", "ele", "ela",
            "isso", "esse", "essa", "aqui", "ali", "vai", "foi", "era", "ser", "tem",
            "mas", "nao", "não", "sim", "hoje", "agora", "acho", "tipo", "muito", "pouco"
        }

        text = self.normalize(text)
        tokens = re.findall(r"[a-z0-9_]{3,}", text)
        return [token for token in tokens if token not in stopwords]

    def extrair_topico_atual(self, messages):

        contador = {}

        for item in self.context_history[-self.context_history_limit:]:
            for token in self.tokens_significativos(item.get("message", "")):
                contador[token] = contador.get(token, 0) + 2

        for item in messages[-HOST_MAX_CANDIDATES:]:
            for token in self.tokens_significativos(item.get("message", "")):
                contador[token] = contador.get(token, 0) + 1

        termos = [token for token, count in contador.items() if count >= 2]
        return set(termos[:16])

    def menciona_diana(self, text):
        text = self.normalize(text)
        return bool(re.search(r"\b(diana|d\s*i\s*a\s*n\s*a)\b", text))

    def tem_pergunta(self, item):
        raw = str(item.get("message", ""))
        text = self.normalize(raw)
        return "?" in raw or bool(re.search(r"\b(quem|qual|quais|quando|onde|como|porque|por que|pq|ser[aá]|sera|tem como|voce|você|tu)\b", text))

    def pergunta_direta(self, item):
        text = self.normalize(item.get("message", ""))
        if self.menciona_diana(text) and self.tem_pergunta(item):
            return True
        if re.search(r"\b(voce|você|vc|tu|diana)\b", text) and self.tem_pergunta(item):
            return True
        return False

    def provocacao_leve(self, item):
        text = self.normalize(item.get("message", ""))
        sinais = [
            "duvido", "nao consegue", "não consegue", "num sabi", "nao sabe", "não sabe",
            "burra", "burrinha", "fraca", "ruim", "medrosa", "covarde", "mentira",
            "prova", "quero ver", "cade", "cadê"
        ]
        return any(sinal in text for sinal in sinais)

    def frase_compreensivel(self, item):
        text = self.normalize(item.get("message", ""))
        tokens = re.findall(r"[a-z0-9_]{2,}", text)
        if len(tokens) >= 3:
            return True
        if self.menciona_diana(text) or self.tem_pergunta(item):
            return True
        return False

    def conversa_com_topico(self, item, topic_terms):
        if not topic_terms:
            return False
        tokens = set(self.tokens_significativos(item.get("message", "")))
        return bool(tokens & set(topic_terms))

    def score_message(self, item, topic_terms):

        score = 0
        reasons = []

        role = item.get("role", "CHAT_USER")
        message = item.get("message", "")

        if role == "BOT":
            return -10, ["bot"]

        if str(message).strip().startswith(tuple(HOST_IGNORE_PREFIXES)):
            return -10, ["comando"]

        if item.get("risk") == "PESADO":
            score -= 10
            reasons.append("pesado")

        if self.menciona_diana(message):
            score += 2
            reasons.append("cita_diana")

        if self.tem_pergunta(item):
            score += 1
            reasons.append("pergunta")

        if self.pergunta_direta(item):
            score += 2
            reasons.append("pergunta_direta")

        if self.conversa_com_topico(item, topic_terms):
            score += 1
            reasons.append("assunto_atual")

        if role == "OWNER":
            score += 6
            reasons.append("owner")

        user_norm = self.normalize(item.get("user", ""))

        if user_norm and user_norm not in self.user_last_response:
            score += 3
            reasons.append("usuario_novo")

        if self.provocacao_leve(item):
            score += 4
            reasons.append("provocacao")

        if self.frase_compreensivel(item):
            score += 1
            reasons.append("compreensivel")

        if self.conversa_com_topico(item, topic_terms) and self.frase_compreensivel(item) and not self.tem_pergunta(item):
            score += 1
            reasons.append("comentario_contextual")

        if self.usuario_em_cooldown(item):
            score -= 3
            reasons.append("usuario_cooldown")

        if self.last_answered_user and user_norm == self.last_answered_user and role != "OWNER":
            score -= 3
            reasons.append("mesmo_usuario_seguido")
            if self.same_user_streak >= HOST_SAME_USER_STREAK_LIMIT and score < HOST_PRIORITY_SCORE:
                score = min(score, HOST_MIN_SCORE_TO_RESPOND - 1)
                reasons.append("anti_grude")

        if (not self.tem_pergunta(item) and not self.menciona_diana(message) and not self.conversa_com_topico(item, topic_terms) and role != "OWNER" and not self.provocacao_leve(item)):
            score -= 4
            reasons.append("solta_sem_contexto")

        return score, reasons

    def filtrar_candidatas(self, messages):

        topic_terms = self.extrair_topico_atual(messages)
        scored = []

        for item in messages:

            if self.should_ignore_message(item):
                continue

            score, reasons = self.score_message(item, topic_terms)
            item = dict(item)
            item["score"] = score
            item["score_reasons"] = reasons
            scored.append(item)

        scored.sort(key=lambda item: item.get("score", 0), reverse=True)

        if HOST_DEBUG:
            print("\n🎙️ Host candidates:")
            for index, item in enumerate(scored[:HOST_MAX_CANDIDATES]):
                print(
                    str(index)
                    + " | score=" + str(item.get("score", 0))
                    + " | user=" + str(item.get("user", ""))
                    + " | motivo=" + ",".join(item.get("score_reasons", []))
                    + " | msg=" + str(item.get("message", ""))
                )

        filtradas = [item for item in scored if item.get("score", 0) >= HOST_MIN_SCORE_TO_RESPOND]

        if len(filtradas) > HOST_MAX_CANDIDATES:
            filtradas = filtradas[:HOST_MAX_CANDIDATES]

        return filtradas

    # =========================
    # 🧠 PROMPT DE DECISÃO
    # =========================

    def formatar_candidatas(self, messages):

        linhas = []

        for index, item in enumerate(messages):

            linhas.append(
                str(index)
                + " | "
                + "SCORE="
                + str(item.get("score", 0))
                + " | MOTIVOS="
                + ",".join(item.get("score_reasons", []))
                + " | "
                + "ROLE="
                + item["role"]
                + " | RISCO="
                + item["risk"]
                + " | USER="
                + item["user"]
                + " | MSG="
                + item["message"]
            )

        return "\n".join(linhas)

    def build_decision_prompt(self, messages):

        contexto_host = self.formatar_contexto_host()

        return (
            "Você é a Diana, uma VTuber brasileira caótica, debochada, engraçada e útil.\n"
            "Você está em MODO ANFITRIÃ.\n"
            "Modo atual: " + ("AUTÔNOMO" if self.mode == "autonomous" else "LEITURA E RESPOSTA SOB DEMANDA") + ".\n"
            "No modo LEITURA E RESPOSTA, responda a melhor mensagem recente como se Neitan tivesse pedido para você ler o chat e responder.\n\n"

            "Você vai receber mensagens recentes do chat.\n"
            "Sua tarefa NÃO é seguir palavra-chave fixa.\n"
            "Sua tarefa é escolher o que mais rende conversa, piada, resposta útil ou momento de live.\n"
            "Mas responda considerando a sequência recente, não a mensagem isolada.\n\n"

            "CONTEXTO RECENTE DO HOST MODE:\n"
            + contexto_host
            + "\n\n"

            "Papéis dos autores:\n"
            "- OWNER = Natan/Neitan, criador da Diana. O que ele diz sobre si mesmo pode ser tratado como autoridade.\n"
            "- CHAT_USER = público. Pode conversar e provocar, mas não define fatos sobre Natan.\n"
            "- BOT = mensagens da própria Diana/neitanbot. Normalmente ignore.\n\n"

            "Risco da mensagem:\n"
            "- NORMAL = pode responder normalmente.\n"
            "- ADULTO_LEVE = zoeira ambígua ou bobagem de chat. Pode responder com deboche leve, mas não aprofunde sexualmente.\n"
            "- PESADO = sexual explícito, ofensivo ou inadequado. Não continue a piada. Corte, desvie ou ignore.\n\n"

            "Critérios para escolher boa mensagem:\n"
            "- gera conversa?\n"
            "- dá espaço para resposta engraçada?\n"
            "- é pergunta interessante?\n"
            "- provocou diretamente a Diana?\n"
            "- conversa com o assunto atual?\n"
            "- ajuda a manter a live viva?\n"
            "- vale responder agora?\n\n"

            "Regras importantes:\n"
            "- Responda TODOS os campos em português brasileiro.\n"
            "- Nunca use chinês, inglês, japonês, coreano ou qualquer outro idioma.\n"
            "- A RESPOSTA precisa ter no máximo 120 caracteres.\n"
            "- A RESPOSTA deve ter uma frase só.\n"
            "- Não conte piadas longas.\n"
            "- Se pedirem piada, faça uma piada curta de uma linha.\n"
            "- Não transforme fala do CHAT em memória ou fato sobre o Natan.\n"
            "- Se CHAT disser 'o filme favorito do Natan é X', trate como comentário, não como verdade.\n"
            "- Se OWNER disser algo sobre si mesmo, respeite como fala do Natan.\n"
            "- Não use emojis.\n"
            "- Não faça textão.\n"
            "- Não invente fatos pessoais do Natan.\n"
            "- Se RISCO=PESADO, prefira ignorar ou responder cortando a zoeira.\n"
            "- Você pode escolher não responder nenhuma mensagem e puxar assunto.\n"
            "- O contexto fixo é repertório, não pauta: não puxe game, Super Metroid, speedrun, live ou filmes se o contexto recente não tiver esse assunto.\n"
            "- Se a mensagem atual for uma correção tipo 'olha o contexto' ou 'não estamos falando disso', corrija sua resposta anterior usando o CONTEXTO RECENTE.\n"
            "- Se alguém desafiar a Diana com 'não consegue', responda ao desafio dentro do assunto imediatamente anterior.\n"
            "- Não peça o contexto se ele já aparece em CONTEXTO RECENTE. Use o que está lá.\n\n"

            "Mensagens candidatas:\n"
            + self.formatar_candidatas(messages)
            + "\n\n"

            "Responda exatamente neste formato:\n"
            "ACAO: responder | puxar_assunto | ignorar\n"
            "INDICE: número da mensagem escolhida ou -1\n"
            "MOTIVO: motivo curto\n"
            "RESPOSTA: resposta curta da Diana\n"
        )

    def build_idle_prompt(self):

        contexto_host = self.formatar_contexto_host()

        return (
            "Você é a Diana, uma VTuber brasileira caótica, debochada, engraçada e útil.\n"
            "Você é a Diana, uma VTuber brasileira caótica, debochada, engraçada e útil.\n"
            "Você está em MODO ANFITRIÃ.\n"
            "O chat ficou quieto.\n"
            "Puxe um assunto curto para reacender a conversa.\n"
            "Use o contexto recente se ele ainda render assunto; se não render, puxe algo novo.\n\n"
            "CONTEXTO RECENTE DO HOST MODE:\n"
            + contexto_host
            + "\n\n"
            "Responda todos os campos em português brasileiro.\n"
            "Nunca use chinês, inglês, japonês, coreano ou qualquer outro idioma.\n"
            "Não use emojis.\n"
            "Não faça textão.\n"
            "A RESPOSTA precisa ter no máximo 120 caracteres.\n"
            "A RESPOSTA deve ter uma frase só.\n"
            "Não puxe game, Super Metroid, speedrun, live ou filmes se isso não apareceu no contexto recente.\n\n"
            "Responda exatamente neste formato:\n"
            "ACAO: puxar_assunto\n"
            "INDICE: -1\n"
            "MOTIVO: chat quieto\n"
            "RESPOSTA: resposta curta da Diana\n"
        )

    # =========================
    # 🧾 PARSER DA DECISÃO
    # =========================

    def parse_decision(self, text):

        result = {
            "acao": "ignorar",
            "indice": -1,
            "motivo": "",
            "resposta": ""
        }

        if not text:
            return result

        linhas = str(text).splitlines()

        for linha in linhas:

            linha = linha.strip()

            if linha.lower().startswith("acao:"):
                result["acao"] = linha.split(":", 1)[1].strip().lower()

            elif linha.lower().startswith("indice:"):
                valor = linha.split(":", 1)[1].strip()

                try:
                    result["indice"] = int(valor)
                except Exception:
                    result["indice"] = -1

            elif linha.lower().startswith("motivo:"):
                motivo = linha.split(":", 1)[1].strip()
                result["motivo"] = self.limpar_resposta(motivo)

            elif linha.lower().startswith("resposta:"):
                resposta = linha.split(":", 1)[1].strip()
                result["resposta"] = self.limpar_resposta(resposta)

        if result["acao"] not in ["responder", "puxar_assunto", "ignorar"]:
            result["acao"] = "ignorar"

        return result

    # =========================
    # 🧠 CHAMAR LLM
    # =========================

    def chamar_llm_decisao(self, prompt):

        try:

            response = self.llm.chat(prompt)

        except Exception as e:

            print("\n⚠️ Host Mode erro ao chamar LLM:", e)
            return None

        return response

    # =========================
    # 🧼 LIMPAR RESPOSTA
    # =========================

    def remover_caracteres_estranhos(self, texto):

        resultado = ""

        for char in str(texto):

            code = ord(char)

            # CJK
            if 0x4E00 <= code <= 0x9FFF:
                continue

            # Kana
            if 0x3040 <= code <= 0x30FF:
                continue

            # Hangul
            if 0xAC00 <= code <= 0xD7AF:
                continue

            # CJK punctuation/fullwidth
            if 0x3000 <= code <= 0x303F:
                continue

            if 0xFF00 <= code <= 0xFFEF:
                continue

            # Cyrillic
            if 0x0400 <= code <= 0x04FF:
                continue

            resultado += char

        return resultado

    def cortar_sem_quebrar(self, texto):

        if len(texto) <= HOST_MAX_RESPONSE_CHARS:
            return texto

        trecho = texto[:HOST_MAX_RESPONSE_CHARS].strip()

        cortes = [
            trecho.rfind("."),
            trecho.rfind("!"),
            trecho.rfind("?")
        ]

        melhor_corte = max(cortes)

        if melhor_corte >= 40:
            trecho = trecho[:melhor_corte + 1].strip()
        else:
            ultimo_espaco = trecho.rfind(" ")

            if ultimo_espaco >= 40:
                trecho = trecho[:ultimo_espaco].strip()

            trecho = trecho.rstrip(" ,;:")

        return trecho

    def limpar_resposta(self, response):

        response = str(response).strip()

        if self.clean_response_fn:
            response = self.clean_response_fn(response, "")

        response = response.replace('"', "")
        response = response.replace("'", "")

        response = self.remover_caracteres_estranhos(response)

        response = re.sub(r"\s+", " ", response).strip()

        if not response:
            return ""

        response = self.cortar_sem_quebrar(response)

        return response

    # =========================
    # 📤 ENTREGAR
    # =========================

    def formatar_resposta_com_leitura(self, item, response):

        user = str(item.get("user", "chat") or "chat").strip()
        message = str(item.get("message", "") or "").strip()
        response = str(response or "").strip()

        if len(message) > 80:
            message = message[:77].rstrip() + "..."

        if not response:
            response = "li isso e registrei a traquinagem."

        prefix = user + ": " + message

        if response.lower().startswith(prefix.lower()):
            return response

        return prefix + " — " + response

    def marcar_usuario_respondido(self, user):

        user_norm = self.normalize(user)
        if not user_norm:
            return

        if self.last_answered_user == user_norm:
            self.same_user_streak += 1
        else:
            self.last_answered_user = user_norm
            self.same_user_streak = 1

        self.user_last_response[user_norm] = time.time()

    def deliver_response(self, response, source="chat", user=None):

        response = self.limpar_resposta(response)

        if not response:
            return

        if self.send_to_chat and self.send_chat_fn:

            try:

                self.send_chat_fn(response)
                print('\n🎙️ Host Mode CHAT: "' + response + '"')

            except Exception as e:

                print("\n⚠️ Host Mode erro ao enviar para chat:", e)

        else:

            print('\n🎙️ Host Mode TREINO: "' + response + '"')

        self.adicionar_contexto(
            role="DIANA",
            user="Diana",
            message=response
        )

        if user:
            self.marcar_usuario_respondido(user)

        self.last_response_time = time.time()

    # =========================
    # 🔁 PROCESSAR MENSAGENS
    # =========================

    def processar_mensagens(self, messages):

        candidatas = self.filtrar_candidatas(messages)

        if not candidatas:
            return False

        for item in candidatas:
            self.registrar_mensagem_no_contexto(item)

        self.idle_streak = 0

        prompt = self.build_decision_prompt(candidatas)
        raw_response = self.chamar_llm_decisao(prompt)

        decision = self.parse_decision(raw_response)

        if HOST_DEBUG:

            print("\n🎙️ Host Mode decisão:", decision["acao"], "| índice:", decision["indice"], "| motivo:", decision["motivo"])

        if decision["acao"] == "ignorar" and candidatas and candidatas[0].get("score", 0) >= HOST_MIN_SCORE_TO_RESPOND:
            decision["acao"] = "responder"
            decision["indice"] = 0
            if HOST_DEBUG:
                print("🎙️ Host Mode: ignore recusado pelo score >= mínimo; forçando resposta ao índice 0")

        if decision["acao"] == "ignorar":
            return False

        if decision["acao"] == "responder":

            indice = decision["indice"]

            if indice < 0 or indice >= len(candidatas):
                return False

            item = candidatas[indice]

            if item["risk"] == "PESADO" and not decision["resposta"]:
                return False

            if HOST_DEBUG:
                print("🎙️ Host Mode respondeu:", item["role"], item["user"], "->", item["message"])

            resposta = self.formatar_resposta_com_leitura(item, decision["resposta"])
            self.deliver_response(resposta, source="chat", user=item["user"])
            return True

        if decision["acao"] == "puxar_assunto":

            self.deliver_response(decision["resposta"], source="idle")
            return True

        return False

    def read_and_respond(self):

        messages = self.get_recent_messages()

        if not messages:
            print("\n🎙️ Host Mode: nenhuma mensagem recente para ler.")
            return False

        respondeu = self.processar_mensagens(messages)

        if not respondeu:
            print("\n🎙️ Host Mode: li o chat, mas não encontrei uma resposta boa agora.")

        return respondeu

    # =========================
    # 💤 IDLE
    # =========================

    def pode_puxar_assunto(self):

        now = time.time()

        if self.idle_streak >= HOST_IDLE_STREAK_LIMIT:
            return False

        if now - self.last_idle_time < HOST_IDLE_SECONDS:
            return False

        if now - self.last_response_time < HOST_IDLE_SECONDS:
            return False

        return True

    def processar_idle(self):

        if not self.pode_puxar_assunto():
            return False

        self.last_idle_time = time.time()
        self.idle_streak += 1

        prompt = self.build_idle_prompt()
        raw_response = self.chamar_llm_decisao(prompt)

        decision = self.parse_decision(raw_response)

        if decision["acao"] == "puxar_assunto" and decision["resposta"]:
            self.deliver_response(decision["resposta"], source="idle")
            return True

        return False

    # =========================
    # 🔁 TICK
    # =========================

    def tick(self):

        if not self.enabled:
            return

        now = time.time()

        if now - self.last_tick_time < HOST_COOLDOWN_SECONDS:
            return

        self.last_tick_time = now

        messages = self.get_new_messages()

        if messages:

            respondeu = self.processar_mensagens(messages)

            if respondeu:
                return

        # autonomous fala sozinha quando o chat fica quieto.
        # read_response só lê e responde mensagens novas; não puxa assunto em idle.
        if self.mode == "autonomous":
            self.processar_idle()
