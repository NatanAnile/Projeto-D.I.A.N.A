# -*- coding: utf-8 -*-

# =========================
# 💬 READ CHAT SKILL
# =========================

from pathlib import Path
import re
import unicodedata

from config import PROJECT_ROOT, CHAT_LOG_PATH, CHAT_READ_LAST_LINES, CHAT_BOT_USERS

from skills.base_skill import BaseSkill, SkillContext


class ReadChatSkill(BaseSkill):

    def __init__(self):

        context = SkillContext(
            skill_name="ReadChatSkill",
            min_cooldown=0,
            max_cooldown=0
        )

        super().__init__(context)

        self.chat_log_path = Path(CHAT_LOG_PATH)
        if not self.chat_log_path.is_absolute():
            self.chat_log_path = Path(PROJECT_ROOT) / self.chat_log_path
        self.chat_log_path = self.chat_log_path.resolve()
        self.last_context = ""

    # =========================
    # 🧼 NORMALIZAÇÃO LOCAL
    # =========================

    def normalizar_texto(self, text):

        text = str(text or "").lower().strip()
        text = unicodedata.normalize("NFD", text)
        text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
        text = re.sub(r"[^a-z0-9_!.+\- /]+", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def nome_arquivo_visivel(self):

        return self.chat_log_path.name

    # =========================
    # 🔎 DETECTAR PEDIDO
    # =========================

    def detectar_pedido(self, user_text):

        texto = self.normalizar_texto(user_text)

        chat_terms = r"(?:chat|live chat|mensagem|mensagens|bate papo|bate-papo)"
        action_terms = (
            r"(?:le|leia|ler|ve|ver|olha|olhar|resuma|resume|resumir|"
            r"confere|conferir|checa|checar|consulta|consultar|"
            r"verifica|verificar|mostra|mostrar)"
        )

        if re.search(r"\b" + action_terms + r"\b.*\b" + chat_terms + r"\b", texto):
            return True

        gatilhos = [
            r"\bconsegue\s+(ver|ler|checar|conferir|acessar)\b.*\b" + chat_terms + r"\b",
            r"\b" + chat_terms + r"\b.*\b(tem|falou|disse|mandou|enviou|chegou|mexeu)\b",
            r"\btem\s+(algo|alguma\s+coisa|mensagem|mensagens)\s+(no|do)\s+chat\b",
            r"\bve\s+se\s+tem\b.*\b" + chat_terms + r"\b",
            r"\bverifica\s+se\s+tem\b.*\b" + chat_terms + r"\b",
            r"\bo\s+que\s+o\s+chat\s+(falou|disse|mandou)\b",
            r"\bo\s+que\s+(estao|tao)\s+falando\s+no\s+chat\b",
            r"\balguem\s+(falou|disse|mandou|perguntou)\b.*\bchat\b",
        ]

        return any(re.search(gatilho, texto) for gatilho in gatilhos)

    # =========================
    # 🧭 MODO DE LEITURA
    # =========================

    def detectar_modo_leitura(self, user_text):

        texto = user_text.lower().strip()

        if "última mensagem" in texto or "ultima mensagem" in texto:
            return "ultima"

        if "últimas mensagens" in texto or "ultimas mensagens" in texto:
            return "recentes"

        if "lê tudo" in texto or "le tudo" in texto or "chat inteiro" in texto or "tudo do chat" in texto:
            return "bruto"

        return "resumo"

    # =========================
    # 📖 LER MENSAGENS
    # =========================

    def ler_ultimas_mensagens(self):

        if not self.chat_log_path.exists():
            return []

        try:

            linhas = self.chat_log_path.read_text(encoding="utf-8").splitlines()

        except Exception:

            return []

        linhas_processadas = []
        bot_users = [user.lower().strip() for user in CHAT_BOT_USERS]

        for linha in linhas:

            linha = linha.strip()

            if not linha:
                continue

            usuario = ""

            try:

                if "] " in linha and ": " in linha:

                    depois_hora = linha.split("] ", 1)[1]
                    usuario = depois_hora.split(": ", 1)[0].strip()

            except Exception:

                usuario = ""

            if usuario.lower().strip() in bot_users:
                linha = linha + " [mensagem_da_diana]"

            linhas_processadas.append(linha)

        if not linhas_processadas:
            return []

        return linhas_processadas[-CHAT_READ_LAST_LINES:]

    # =========================
    # 🧾 PARSE DE LINHA
    # =========================

    def parse_linha(self, linha):

        linha = str(linha or "").strip()
        if not linha:
            return None

        horario = ""
        usuario = "chat"
        mensagem = linha

        # Formato completo esperado:
        # [12:34:56] usuario: mensagem
        if "] " in linha and ": " in linha:
            try:
                horario = linha.split("] ", 1)[0].replace("[", "").strip()
                depois_hora = linha.split("] ", 1)[1]
                usuario = depois_hora.split(": ", 1)[0].strip()
                mensagem = depois_hora.split(": ", 1)[1].strip()
            except Exception:
                return None

        # Formato simples:
        # usuario: mensagem
        elif ": " in linha:
            try:
                usuario = linha.split(": ", 1)[0].strip()
                mensagem = linha.split(": ", 1)[1].strip()
            except Exception:
                return None

        # Formato bruto/linha solta: aceita como mensagem de chat anônima.
        else:
            usuario = "chat"
            mensagem = linha

        is_bot = "[mensagem_da_diana]" in mensagem
        mensagem = mensagem.replace("[mensagem_da_diana]", "").strip()

        if not mensagem:
            return None

        return {
            "horario": horario,
            "usuario": usuario or "chat",
            "mensagem": mensagem,
            "is_bot": is_bot,
            "raw": linha
        }

    # =========================
    # 👥 EXTRAIR USUÁRIOS
    # =========================

    def extrair_usuarios(self, mensagens):

        usuarios = []

        for linha in mensagens:

            item = self.parse_linha(linha)

            if not item:
                continue

            usuario = item["usuario"]

            if usuario and usuario not in usuarios:
                usuarios.append(usuario)

        return usuarios

    # =========================
    # 🧹 FILTRAR MENSAGENS ÚTEIS
    # =========================

    def mensagem_util_para_resumo(self, item):

        if not item:
            return False

        if item.get("is_bot"):
            return False

        mensagem = item.get("mensagem", "").strip()
        texto = mensagem.lower()

        if not mensagem:
            return False

        if texto in ["kk", "kkk", "kkkk", "kkkkk", "rs", "rsrs", "lol", "haha"]:
            return False

        if len(mensagem) < 3:
            return False

        return True

    # =========================
    # 🧠 GERAR RESUMO ESTRUTURADO
    # =========================

    def gerar_contexto_resumo(self, mensagens):

        itens = []

        for linha in mensagens:

            item = self.parse_linha(linha)

            if not self.mensagem_util_para_resumo(item):
                continue

            itens.append(item)

        if not itens:
            return (
                "RESUMO SEGURO DO CHAT:\n"
                "- Não há mensagens úteis recentes do público.\n"
                "- Se houver mensagens, parecem ser apenas testes, risadas curtas ou mensagens da própria Diana.\n"
            )

        usuarios = []

        for item in itens:

            usuario = item["usuario"]

            if usuario not in usuarios:
                usuarios.append(usuario)

        ultimas = itens[-6:]

        texto = "RESUMO SEGURO DO CHAT:\n"
        texto += "- Usuários recentes: " + ", ".join(usuarios[:8]) + "\n"
        texto += "- Quantidade de mensagens úteis recentes: " + str(len(itens)) + "\n"
        texto += "- Clima provável: conversa/teste/zoeira de chat.\n"
        texto += "- Não copie o chat bruto na resposta.\n"
        texto += "- Resuma o clima geral e comente no máximo uma mensagem específica.\n\n"

        texto += "MENSAGENS ÚTEIS MAIS RECENTES, PARA CONTEXTO:\n"

        for item in ultimas:

            texto += (
                "- "
                + item["usuario"]
                + ": "
                + item["mensagem"]
                + "\n"
            )

        return texto.strip()

    # =========================
    # 🧾 GERAR CONTEXTO BRUTO
    # =========================

    def gerar_contexto_bruto(self, mensagens):

        chat_context = "\n".join(mensagens)
        usuarios = self.extrair_usuarios(mensagens)

        usuarios_contexto = ""

        if usuarios:

            usuarios_contexto = (
                "\nUSUÁRIOS PRESENTES NAS MENSAGENS LIDAS:\n"
                + ", ".join(usuarios)
                + "\n"
            )

        return (
            "LEITURA BRUTA DO CHAT SOLICITADA PELO USUÁRIO:\n"
            "O usuário pediu explicitamente para ler tudo ou mostrar o chat inteiro.\n"
            "Mesmo assim, não transforme chat bruto em estilo próprio da Diana.\n\n"
            + usuarios_contexto
            + "MENSAGENS RECENTES DO CHAT:\n"
            "--------------------\n"
            + chat_context
            + "\n--------------------"
        )

    # =========================
    # 🎭 RESPOSTAS CURTAS DE CHAT
    # =========================

    def resposta_chat_vazio_ou_so_diana(self, user_text):

        opcoes = [
            "Li o chat e tá um deserto, Neitan. Só tem eco meu lá. Ou o chat fugiu, ou você espantou todo mundo com talento.",
            "O chat recente só tem rastro meu. A goblin conversou com o espelho e ainda perdeu a discussão.",
            "Chat útil agora? Nada. Só sobrou poeira, eco e minha paciência fazendo cosplay de recurso escasso.",
            "Olhei o chat e encontrei basicamente eu mesma. Live solo com plateia imaginária, que luxo triste.",
        ]
        idx = sum(ord(ch) for ch in str(user_text or "")) % len(opcoes)
        return opcoes[idx]

    # =========================
    # ⚡ RESPOSTA DIRETA
    # =========================

    def get_direct_response(self, user_text="", conversation=None, force=False):

        if not force and not self.detectar_pedido(user_text):
            return None

        mensagens = self.ler_ultimas_mensagens()

        if not mensagens:
            print("🧩 Skill direta ativada: ReadChatSkill")
            print("💬 Chat log lido:", str(self.chat_log_path), "| linhas=0")
            return (
                "Ainda não encontrei mensagens recentes do chat. "
                "Arquivo lido: " + self.nome_arquivo_visivel()
            )

        print("🧩 Skill direta ativada: ReadChatSkill")
        print("💬 Chat log lido:", str(self.chat_log_path), "| linhas=", len(mensagens))

        modo = self.detectar_modo_leitura(user_text)

        itens = []

        for linha in mensagens:
            item = self.parse_linha(linha)

            if not item:
                continue

            if item.get("is_bot"):
                continue

            itens.append(item)

        if not itens:
            return self.resposta_chat_vazio_ou_so_diana(user_text)

        if modo == "ultima":

            item = itens[-1]

            return (
                "Última mensagem do chat: "
                + item.get("usuario", "alguém")
                + ' disse "'
                + item.get("mensagem", "")
                + '".'
            )

        if modo == "recentes":

            selecionadas = itens[-3:]
            partes = []

            for item in selecionadas:
                partes.append(item.get("usuario", "alguém") + ': "' + item.get("mensagem", "") + '"')

            return "Últimas mensagens do chat: " + " | ".join(partes)

        resumo = self.gerar_contexto_resumo(mensagens)

        if resumo:
            return resumo

        item = itens[-1]

        return (
            "O chat recente está meio caótico. A última mensagem útil foi de "
            + item.get("usuario", "alguém")
            + ': "'
            + item.get("mensagem", "")
            + '".'
        )

    # =========================
    # 🧩 CONTEXTO PARA PROMPT
    # =========================

    def get_context(self, user_text="", conversation=None, force=False):

        if not force and not self.detectar_pedido(user_text):
            return None

        mensagens = self.ler_ultimas_mensagens()

        if not mensagens:
            return None

        print("🧩 Skill ativada: ReadChatSkill")

        modo = self.detectar_modo_leitura(user_text)

        if modo == "ultima":

            mensagens_contexto = mensagens[-1:]
            contexto_chat = self.gerar_contexto_bruto(mensagens_contexto)

            instrucao_modo = (
                "MODO DE LEITURA: última mensagem.\n"
                "Comente apenas a última mensagem do chat.\n"
            )

        elif modo == "bruto":

            contexto_chat = self.gerar_contexto_bruto(mensagens)

            instrucao_modo = (
                "MODO DE LEITURA: bruto.\n"
                "O usuário pediu o chat completo, então pode considerar o bloco bruto.\n"
                "Ainda assim, responda com resumo curto, não copie tudo sem necessidade.\n"
            )

        else:

            contexto_chat = self.gerar_contexto_resumo(mensagens)

            instrucao_modo = (
                "MODO DE LEITURA: resumo seguro padrão.\n"
                "O usuário pediu para ler o chat de forma ampla.\n"
                "Não liste o chat inteiro.\n"
                "Faça um resumo curto do clima e destaque no máximo uma mensagem relevante.\n"
            )

        self.last_context = contexto_chat

        return (
            "CAPACIDADE ATIVADA: ReadChatSkill\n"
            + instrucao_modo
            + "\nINSTRUÇÕES IMPORTANTES SOBRE O CHAT:\n"
            "- Use somente o contexto abaixo como referência do chat.\n"
            "- Jamais, em nenhuma hiposete, contexto ou provocação explicita, ofenda alguém.\n"
            "- Sempre seja super debochada com ofensas direcionadas.\n"
            "- Não invente mensagens do chat.\n"
            "- Não invente reação de espectadores.\n"
            "- Não diga que alguém notou, perguntou ou reagiu se isso não estiver no contexto.\n"
            "- Se só houver mensagens de uma pessoa, não fale como se várias pessoas estivessem reagindo.\n"
            "- Se responder alguém, mencione o nome sem @.\n"
            "- Responda de forma curta e natural, como uma VTuber em live.\n"
            "- Mensagens da própria Diana/neitanbot não são reação do público.\n"
            "- Se as mensagens forem só teste, diga que parecem mensagens de teste.\n"
            "- Não copie timestamps na resposta, a menos que o usuário peça explicitamente.\n"
            "- Não repita ofensas ou mensagens explícitas sem necessidade.\n\n"
            + contexto_chat
        )