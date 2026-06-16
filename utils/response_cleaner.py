# -*- coding: utf-8 -*-

# =========================
# 🧼 RESPONSE CLEANER
# =========================

import re


class ResponseCleaner:

    def __init__(self, allow_live_without_context=False, **kwargs):

        self.allow_live_without_context = allow_live_without_context

        self.limites_caracteres = {
            "short": 260,
            "medium": 520,
            "long": 900
        }

        self.artefatos_proibidos = [
            "ContentPane",
            "comContentPane",
            "response was cut",
            "resposta foi cortada",
            "translation:",
            "portuguese:",
            "english:",
            "japanese:",
            "chinese:",
            "korean:"
        ]

        self.expressoes_substituir = {
            "meu dear Neitan": "Neitan",
            "dear Neitan": "Neitan",
            "meu dear": "Neitan",
            "dear": "",
            "sorry": "",
            "action-movie": "filme de ação",
            "action movie": "filme de ação",
            "sistema NERV": "setup torto",
            "desvirilizar seus pensamentos": "desmontar essa tua confiança de papelão",
            "desvirilizar": "desmontar",
            "como você se sente": "olha essa situação",
            "Como você se sente": "Olha essa situação",
            "meu querido": "Neitan",
            "minha querida": "",
            "meu lindo": "Neitan",
            "meu bom": "Neitan",
            "bocudão": "Neitan",
            "Natin": "Neitan",
            "Natinho": "Neitan",
            "Neitanzinho": "Neitan",
            "neitanzinho": "Neitan",
            "Natan-anile": "Natan",
            "Natan_Anile": "Natan",
            "@Natan_Anile": "Natan",
            "natan_anile": "Natan",
            "gwau gwau": "",
            "Gwau gwau": "",
            "aiiaiai": "",
            "uju": "",
            "mimi": "",
            "tchutchuque": "",
            "ligadinha": "ligada",
            "bibiricando": "conversando",
            "bibiricar": "conversar",
            "amorzinho": "Neitan",
            "docinho": "Neitan",
            "fofucho": "Neitan",
            "coladinha": "por aqui",
            "tímida": "sem esse teatro",
            "timida": "sem esse teatro",
            "mimo": "resposta",
            "doçura": "bagunça",
            "doçura": "bagunça",
            "carinho verbal": "deboche contextual",
            "Carinho verbal": "Deboche contextual",
            "fisicamente": "virtualmente",
            "menininha": "criatura",
            "cute": "estranho",
            "Cute": "Estranho",
            "meu lindo": "Neitan",
            "Meu lindo": "Neitan",
            "lindo Neitan": "Neitan"
        }

        self.forbidden_patterns = [
            r"\bboceta\b",
            r"\bvadia\b",
            r"\bputa\b",
            r"\bpiranha\b",
            r"\bpau\b",
            r"\bcu\b",
            r"\bcastr\w*",
            r"\bcastraç[aã]o\b",
            r"\bmutil\w*",
            r"\bespanc\w*",
            r"\bmatar\b",
            r"\bsaco fora\b",
            r"\bbeij\w*\b",
            r"\babrac\w*\b",
            r"\babraç\w*\b",
            r"\bfof\w*\b",
            r"\bmeig\w*\b",
            r"\bnamorad\w*\b",
            r"\bneitanzinho\b",
            r"\bbibiric\w*\b",
            r"\bdar uma volta(?: no quarto| por ai| por aí)?\b",
            r"\bandar pelo quarto\b",
            r"\bandar por ai\b",
            r"\bandar por aí\b",
            r"\bvou andar\b",
            r"\bcaminhar pelo quarto\b",
            r"\bestou no seu quarto\b",
            r"\bestou atras de voce\b",
            r"\bestou atrás de você\b",
            r"\bdo seu lado no quarto\b",
            r"\bestou do seu lado\b",
            r"\bestou ai com voce\b",
            r"\bestou aí com você\b",
            r"\bdo seu lado\b",
            r"\bdo meu lado\b",
            r"\bsua casa\b",
            r"\bseu quarto\b",
            r"\btenho corpo\b",
            r"\bfisicamente\b",
            r"\bpegar na sua m[aã]o\b",
            r"\bno seu colo\b",
            r"\bseu colo\b",
            r"\bcolo\b",
            r"\bmimo\b",
            r"\bdoçura\b",
            r"\bcarinho\b",
            r"\bmenininha\b",
            r"\bcute\b",
            r"\blindo\b",
            r"\bamorzinho\b",
            r"\bdocinho\b",
            r"\bfofucho\b",
            r"\bcoladinha\b",
            r"\bt[ií]mida\b"
        ]

        self.termos_ingles_soltos = {
            "dear": "",
            "sweet": "",
            "honey": "",
            "darling": "",
            "baby": "",
            "sorry": "",
            "content": "conteúdo",
            "action": "ação",
            "movie": "filme"
        }

    # =========================
    # 🧰 MODO OPERACIONAL
    # =========================

    def is_operational(self, capacidade):

        capacidade = str(capacidade or "").lower().strip()

        capacidades_operacionais = [
            "read_chat",
            "read_file",
            "read_screen",
            "chat_reply",
            "send_chat",
            "memory_query",
            "repeat_last_operational_task"
        ]

        return capacidade in capacidades_operacionais

    def get_mode_for_capability(self, capacidade):

        if self.is_operational(capacidade):
            return "operational"

        return "normal"

    # =========================
    # 🧼 LIMPEZA PRINCIPAL
    # =========================

    def clean(self, text, user_text="", mode="normal", capability="none", response_budget="short", **kwargs):

        if not text:
            return ""

        original = str(text)
        text = str(text)

        if capability and capability != "none":
            mode = self.get_mode_for_capability(capability)

        text = self.extrair_speaking_se_necessario(text)
        text = self.remover_tags_internas(text)
        text = self.remover_prefixos_de_fala(text)
        text = self.remover_artefatos_llm(text)
        text = self.remover_cjk(text)
        text = self.remover_markdown_excessivo(text)
        text = self.substituir_expressoes_ruins(text)
        text = self.remover_ingles_solto(text)
        text = self.remover_linhas_meta(text)
        text = self.remover_acoes_asterisco(text, mode)
        text = self.limpar_pontuacao(text)
        text = self.remover_cta_artificial(text, user_text)
        text = self.remover_frases_proibidas(text)
        text = self.limpar_espacos(text)

        if mode == "operational":
            text = self.limitar_operacional(text)

        text = self.limitar_por_orcamento(text, response_budget)
        text = self.remover_frase_incompleta_final(text)
        text = self.limpar_espacos(text)

        if not text.strip():
            text = self.safe_character_fallback(user_text)

        return text.strip()

    # =========================
    # 🧼 LIMPEZA MÍNIMA
    # =========================

    def clean_minimal(self, text, response_budget="short"):

        if not text:
            return ""

        text = str(text)

        text = self.extrair_speaking_se_necessario(text)
        text = self.remover_prefixos_de_fala(text)
        text = self.remover_artefatos_llm(text)
        text = self.substituir_expressoes_ruins(text)
        text = self.remover_frases_proibidas(text)
        text = self.limpar_pontuacao(text)
        text = self.limpar_espacos(text)
        text = self.limitar_por_orcamento(text, response_budget)
        text = self.remover_frase_incompleta_final(text)
        text = self.limpar_espacos(text)

        return text.strip()

    # =========================
    # 🧯 FALLBACK DE PERSONAGEM
    # =========================

    def safe_character_fallback(self, user_text=""):

        texto = str(user_text or "").lower()

        if any(x in texto for x in ["oi", "olá", "ola", "e aí", "e ai"]):
            return "Oi, Neitan. Chegou testando a criatura ou só veio conferir se o PC ainda respira?"

        if "piada" in texto:
            return "Por que o bug foi ao médico? Porque estava passando mal de tanto virar feature. Horrível, mas com postura."

        if any(x in texto for x in ["bug", "glitch"]):
            return "É quando o sistema faz palhaçada fora do combinado. O código tropeça e ainda tenta fingir que foi de propósito."

        return "Neitan, essa resposta saiu torta no filtro. Reformulando: manda de novo que eu respondo sem mastigar cabo."

    # =========================
    # 🎬 ACTIONS / PREFIXOS
    # =========================

    def extrair_speaking_se_necessario(self, text):

        raw = str(text or "")

        match = re.search(r"<\s*Action\s*:\s*Speaking\s*:\s*(.*?)\s*>", raw, flags=re.IGNORECASE | re.DOTALL)

        if match:
            return match.group(1).strip()

        match = re.search(
            r"<\s*Action\s*:\s*Speaking\s*>\s*(.*?)\s*<\s*/\s*Action\s*:\s*Speaking\s*>",
            raw,
            flags=re.IGNORECASE | re.DOTALL
        )

        if match:
            return match.group(1).strip()

        raw = re.sub(r"Action\s*:\s*Emotion\s*:\s*[A-Za-zÀ-ÿ_ -]+", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"Action\s*:\s*Speaking\s*:", "", raw, flags=re.IGNORECASE)

        return raw.strip()

    def remover_prefixos_de_fala(self, text):

        text = str(text or "").strip()

        prefixos = [
            "Diana",
            "Diana",
            "Assistente",
            "IA",
            "Resposta",
            "Bot"
        ]

        for prefixo in prefixos:
            padrao = r"^\s*" + re.escape(prefixo) + r"\s*:\s*"
            text = re.sub(padrao, "", text, flags=re.IGNORECASE).strip()

        return text

    # =========================
    # 🏷️ TAGS INTERNAS
    # =========================

    def remover_tags_internas(self, text):

        text = re.sub(r"\[Enviado no chat:.*?\]", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\[Resumo do chat:.*?\]", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\[DEBUG:.*?\]", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\[SISTEMA:.*?\]", "", text, flags=re.IGNORECASE)

        return text

    # =========================
    # 🧨 ARTEFATOS DE LLM
    # =========================

    def remover_artefatos_llm(self, text):

        for artefato in self.artefatos_proibidos:
            text = text.replace(artefato, "")

        text = re.sub(r"\[\s*\d+\s*/\s*\d+\s*\]", "", text)
        text = re.sub(r":\s*\[\s*\d+\s*/\s*\d+\s*\]", "", text)

        text = re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.IGNORECASE | re.DOTALL)

        text = text.replace("<?", "")
        text = text.replace("</", "")
        text = text.replace("/>", "")
        text = text.replace("<>", "")

        padroes_meta = [
            r"^vamos pensar passo a passo[:,]?\s*",
            r"^pensando passo a passo[:,]?\s*",
            r"^analisando[:,]?\s*",
            r"^raciocínio[:,]?\s*",
            r"^raciocinio[:,]?\s*"
        ]

        for padrao in padroes_meta:
            text = re.sub(padrao, "", text, flags=re.IGNORECASE)

        return text

    # =========================
    # 🌏 REMOVER CJK / CARACTERES ESTRANHOS
    # =========================

    def remover_cjk(self, text):

        text_limpo = ""

        for char in text:
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

            text_limpo += char

        caracteres_ruins = [
            "《", "》", "「", "」", "『", "』", "【", "】",
            "，", "。", "：", "；", "！", "？",
            "、", "〜", "〰", "〽", "※", "�"
        ]

        for ruim in caracteres_ruins:
            text_limpo = text_limpo.replace(ruim, "")

        return text_limpo

    # =========================
    # 🧹 MARKDOWN / LIXO VISUAL
    # =========================

    def remover_markdown_excessivo(self, text):

        text = text.replace("**", "")
        text = text.replace("__", "")
        text = text.replace("```", "")
        text = text.replace("`", "")
        text = re.sub(r"\[([^\]]+)\]\((https?://[^\)]+)\)", r"\1", text)

        return text

    # =========================
    # 🔁 SUBSTITUIÇÕES / BLOQUEIOS
    # =========================

    def substituir_expressoes_ruins(self, text):

        for ruim, bom in self.expressoes_substituir.items():
            text = text.replace(ruim, bom)

        return text

    def remover_frases_proibidas(self, text):

        frases = re.split(r"(?<=[.!?])\s+", str(text).strip())
        filtradas = []

        for frase in frases:
            frase_limpa = frase.strip()

            if not frase_limpa:
                continue

            if any(re.search(padrao, frase_limpa, flags=re.IGNORECASE) for padrao in self.forbidden_patterns):
                continue

            filtradas.append(frase_limpa)

        if filtradas:
            return " ".join(filtradas)

        # Se todas as frases eram proibidas, retorna vazio para fallback seguro.
        return ""

    # =========================
    # 🇧🇷 REMOVER INGLÊS SOLTO
    # =========================

    def remover_ingles_solto(self, text):

        palavras = text.split()
        resultado = []

        for palavra in palavras:
            limpa = palavra.strip(".,!?;:()[]{}\"'").lower()

            if limpa in self.termos_ingles_soltos:
                substituta = self.termos_ingles_soltos[limpa]

                if substituta:
                    resultado.append(substituta)

                continue

            resultado.append(palavra)

        return " ".join(resultado)

    # =========================
    # 🧾 REMOVER LINHAS META
    # =========================

    def remover_linhas_meta(self, text):

        linhas = text.splitlines()
        filtradas = []

        proibidos = [
            "resposta:",
            "tradução:",
            "translation:",
            "portuguese:",
            "english:",
            "japanese:",
            "chinese:",
            "korean:",
            "nota:",
            "observação:",
            "observacao:",
            "explicação:",
            "explicacao:"
        ]

        for linha in linhas:
            linha_strip = linha.strip()

            if not linha_strip:
                continue

            linha_lower = linha_strip.lower()

            if any(linha_lower.startswith(termo) for termo in proibidos):
                continue

            filtradas.append(linha_strip)

        return " ".join(filtradas)

    # =========================
    # 🎭 REMOVER AÇÕES ENTRE ASTERISCOS
    # =========================

    def remover_acoes_asterisco(self, text, mode):

        if mode == "operational":
            text = re.sub(r"\*[^*]{1,180}\*", "", text)
            return text

        padroes = [
            r"\*suspiro dramático\*",
            r"\*suspira dramaticamente\*",
            r"\*olha para a câmera\*",
            r"\*risada maligna\*"
        ]

        for padrao in padroes:
            text = re.sub(padrao, "", text, flags=re.IGNORECASE)

        return text

    # =========================
    # 📺 REMOVER CTA ARTIFICIAL
    # =========================

    def assunto_permite_live(self, user_text):

        texto = str(user_text or "").lower()

        gatilhos = [
            "live",
            "twitch",
            "stream",
            "chat",
            "canal",
            "transmissão",
            "transmissao",
            "agenda",
            "host mode"
        ]

        return any(gatilho in texto for gatilho in gatilhos)

    def remover_cta_artificial(self, text, user_text=""):

        if self.allow_live_without_context:
            return text

        if self.assunto_permite_live(user_text):
            return text

        frases = re.split(r"(?<=[.!?])\s+", str(text).strip())
        filtradas = []

        termos_cta = [
            "twitch",
            "live do natan",
            "acompanhar a live",
            "aproveitar a live",
            "segue o canal",
            "canal do natan",
            "fica de olho na twitch",
            "entra na live",
            "bora pra live",
            "quando tiver live",
            "clima de live",
            "energia de live",
            "no chat da live",
            "galera do chat",
            "pessoal do chat"
        ]

        for frase in frases:
            frase_limpa = frase.strip()

            if not frase_limpa:
                continue

            frase_lower = frase_limpa.lower()

            if any(termo in frase_lower for termo in termos_cta):
                continue

            filtradas.append(frase_limpa)

        return " ".join(filtradas)

    # =========================
    # ✂️ OPERACIONAL
    # =========================

    def _proteger_nomes_de_arquivo(self, text):

        mapa = {}

        def repl(match):
            chave = "__DIANA_FILE_DOT_" + str(len(mapa)) + "__"
            mapa[chave] = match.group(0)
            return chave

        protegido = re.sub(
            r"\b[\wÀ-ÿ .+()_-]+\.(?:txt|md|json|jsonl|csv|py)\b",
            repl,
            str(text or ""),
            flags=re.IGNORECASE
        )

        return protegido, mapa

    def _restaurar_nomes_de_arquivo(self, text, mapa):

        for chave, valor in mapa.items():
            text = text.replace(chave, valor)

        return text

    def limitar_operacional(self, text):

        protegido, mapa = self._proteger_nomes_de_arquivo(text)
        frases = re.split(r"(?<=[.!?])\s+", protegido.strip())

        if len(frases) <= 2:
            return self._restaurar_nomes_de_arquivo(protegido, mapa)

        limitado = " ".join(frases[:2]).strip()
        return self._restaurar_nomes_de_arquivo(limitado, mapa)

    # =========================
    # ✂️ ORÇAMENTO / FRASE INCOMPLETA
    # =========================

    def limitar_por_orcamento(self, text, response_budget="short"):

        texto = str(text or "").strip()
        limite = self.limites_caracteres.get(str(response_budget or "short").lower(), 260)

        if len(texto) <= limite:
            return texto

        cortado = texto[:limite].strip()

        ultimo_ponto = max(cortado.rfind("."), cortado.rfind("!"), cortado.rfind("?"))

        if ultimo_ponto >= 60:
            return cortado[:ultimo_ponto + 1].strip()

        ultimo_espaco = cortado.rfind(" ")

        if ultimo_espaco >= 40:
            return cortado[:ultimo_espaco].strip() + "..."

        return cortado.strip() + "..."

    def remover_frase_incompleta_final(self, text):

        texto = str(text or "").strip()

        if not texto:
            return ""

        if texto.endswith((".", "!", "?", "…", "...")):
            return texto

        ultimo_ponto = max(texto.rfind("."), texto.rfind("!"), texto.rfind("?"))

        if ultimo_ponto >= 40:
            return texto[:ultimo_ponto + 1].strip()

        return texto

    # =========================
    # 🧽 PONTUAÇÃO / ESPAÇOS
    # =========================

    def limpar_pontuacao(self, text):

        text = re.sub(r"[!?]{3,}", "!", text)
        text = re.sub(r"\.{4,}", "...", text)
        text = re.sub(r",{2,}", ",", text)

        # Remove pontuação órfã gerada por substituições.
        text = re.sub(r"\s+([,.!?;:])", r"\1", text)
        text = re.sub(r",\s*([.!?])", r"\1", text)
        text = re.sub(r"\.\s*([!?])", r"\1", text)
        text = re.sub(r"([!?])\s*([!?])+", r"\1", text)

        text = text.replace(" ,", ",")
        text = text.replace(" .", ".")
        text = text.replace(" !", "!")
        text = text.replace(" ?", "?")
        text = text.replace(" :", ":")
        text = text.replace(" ;", ";")

        text = re.sub(r"\s+\.", ".", text)
        text = re.sub(r"\s+,", ",", text)

        return text

    def limpar_espacos(self, text):

        text = re.sub(r"\s+", " ", str(text))
        return text.strip()
