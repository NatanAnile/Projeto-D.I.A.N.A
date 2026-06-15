# -*- coding: utf-8 -*-

# =========================
# 🎭 STYLE AUTONOMY
# =========================

import json
import re
import time
import unicodedata
from pathlib import Path

import config as cfg


STYLE_AUTONOMY_ENABLED = getattr(cfg, "STYLE_AUTONOMY_ENABLED", True)

STYLE_CANDIDATES_PATH = getattr(cfg, "STYLE_CANDIDATES_PATH", "data/style/style_candidates.json")
STYLE_PROMOTED_PATH = getattr(cfg, "STYLE_PROMOTED_PATH", "data/style/style_promoted.json")

STYLE_MIN_EXPRESSION_LEN = getattr(cfg, "STYLE_MIN_EXPRESSION_LEN", 4)
STYLE_MAX_EXPRESSION_LEN = getattr(cfg, "STYLE_MAX_EXPRESSION_LEN", 80)

STYLE_AUTO_PROMOTION_ENABLED = getattr(cfg, "STYLE_AUTO_PROMOTION_ENABLED", False)

STYLE_PROMOTION_OCCURRENCES = getattr(cfg, "STYLE_PROMOTION_OCCURRENCES", 3)
STYLE_PROMOTION_SCORE = getattr(cfg, "STYLE_PROMOTION_SCORE", 1.1)

STYLE_CONTEXT_LIMIT = getattr(cfg, "STYLE_CONTEXT_LIMIT", 6)


class StyleAutonomy:

    def __init__(self):

        self.enabled = STYLE_AUTONOMY_ENABLED

        self.candidates_path = Path(STYLE_CANDIDATES_PATH)
        self.promoted_path = Path(STYLE_PROMOTED_PATH)

        self.candidates_path.parent.mkdir(parents=True, exist_ok=True)
        self.promoted_path.parent.mkdir(parents=True, exist_ok=True)

        self.candidates = self.load_json(self.candidates_path)
        self.promoted = self.load_json(self.promoted_path)

    # =========================
    # 📦 JSON
    # =========================

    def load_json(self, path):

        if not path.exists():
            return []

        try:

            data = json.loads(path.read_text(encoding="utf-8"))

            if isinstance(data, list):
                return data

            return []

        except Exception:
            return []

    def save_json(self, path, data):

        try:

            path.parent.mkdir(parents=True, exist_ok=True)

            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=4),
                encoding="utf-8"
            )

        except Exception as e:

            print("⚠️ StyleAutonomy erro ao salvar JSON:", e)

    def save_all(self):

        self.save_json(self.candidates_path, self.candidates)
        self.save_json(self.promoted_path, self.promoted)

    # =========================
    # 🧼 NORMALIZAÇÃO
    # =========================

    def normalize(self, text):

        text = str(text).lower().strip()

        text = unicodedata.normalize("NFD", text)
        text = "".join(char for char in text if unicodedata.category(char) != "Mn")

        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def remover_emojis(self, texto):

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

    def remover_caracteres_estranhos(self, texto):

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

            if 0x0400 <= code <= 0x04FF:
                continue

            resultado += char

        return resultado

    def limpar_texto(self, texto):

        texto = str(texto).strip()

        texto = self.remover_emojis(texto)
        texto = self.remover_caracteres_estranhos(texto)

        texto = texto.replace('"', "")
        texto = texto.replace("“", "")
        texto = texto.replace("”", "")
        texto = texto.replace("**", "")
        texto = texto.replace("__", "")
        texto = texto.replace("`", "")

        texto = re.sub(r"\s+", " ", texto)

        return texto.strip()

    # =========================
    # 🧩 SPLIT EM FRASES
    # =========================

    def dividir_frases(self, response_text):

        texto = str(response_text).strip()

        if not texto:
            return []

        texto = texto.replace("\n", " ")

        partes = re.split(r"(?<=[.!?])\s+", texto)

        frases = []

        for parte in partes:

            parte = self.limpar_texto(parte)

            if not parte:
                continue

            frases.append(parte)

        return frases

    # =========================
    # 🚫 FILTROS GERAIS
    # =========================

    def contem_chat_bruto(self, texto):

        texto_original = str(texto)

        padroes = [
            r"\[\d{1,2}:\d{2}:\d{2}\]\s+[^:]+:",
            r"\[\d{1,2}:\d{2}\]\s+[^:]+:",
            r"\bMENSAGENS RECENTES DO CHAT\b",
            r"\bRESUMO SEGURO DO CHAT\b",
            r"\bUSUÁRIOS PRESENTES NAS MENSAGENS LIDAS\b",
            r"\bUSUARIOS PRESENTES NAS MENSAGENS LIDAS\b",
            r"\bmensagem_da_diana\b"
        ]

        for padrao in padroes:

            if re.search(padrao, texto_original, flags=re.IGNORECASE):
                return True

        return False

    def deve_ignorar_resposta(self, user_text, response_text):

        if not self.enabled:
            return True

        if not response_text:
            return True

        texto_usuario = self.normalize(user_text)
        resposta = self.normalize(response_text)

        if not resposta:
            return True

        gatilhos_ignorar = [
            "lê o arquivo",
            "le o arquivo",
            "ler o arquivo",
            "leia o arquivo",
            "pega o arquivo",

            "olha a tela",
            "ve a tela",
            "vê a tela",
            "captura a tela",
            "tira um print",

            "lê o chat",
            "le o chat",
            "ler o chat",
            "leia o chat",
            "olha o chat",
            "o que o chat falou",
            "o que o chat disse",
            "o que estão falando no chat",
            "o que estao falando no chat",
            "tem algo no chat",
            "responde o chat",
            "responda o chat",
            "vê o chat",
            "ve o chat"
        ]

        for gatilho in gatilhos_ignorar:

            if gatilho in texto_usuario:
                return True

        if self.contem_chat_bruto(response_text):
            return True

        if len(response_text.strip()) < STYLE_MIN_EXPRESSION_LEN:
            return True

        return False

    def frase_ruim_para_extrair(self, frase):

        texto = self.normalize(frase)

        if not texto:
            return True

        if self.contem_chat_bruto(frase):
            return True

        proibidos = [
            "como ia",
            "como uma ia",
            "nao posso",
            "não posso",
            "desculpe",
            "desculpa",
            "sou apenas",
            "modelo de linguagem",
            "system prompt",
            "skill",
            "memoria",
            "memória",
            "prompt",
            "contexto extra",
            "usuario",
            "usuário",
            "diana:",
            "mensagens recentes do chat",
            "resumo seguro do chat",
            "usuários presentes",
            "usuarios presentes",
            "mensagem_da_diana"
        ]

        for termo in proibidos:

            if termo in texto:
                return True

        if len(frase) < STYLE_MIN_EXPRESSION_LEN:
            return True

        if len(frase) > 220:
            return True

        return False

    # =========================
    # 🎯 EXTRAIR ÁTOMOS DE ESTILO
    # =========================

    def extrair_atoms_da_resposta(self, response_text):

        atoms = []

        frases = self.dividir_frases(response_text)

        for frase in frases:

            if self.frase_ruim_para_extrair(frase):
                continue

            atoms_frase = self.extrair_atoms_da_frase(frase)

            for atom in atoms_frase:
                atoms.append(atom)

        return self.deduplicar_atoms(atoms)

    def extrair_atoms_da_frase(self, frase):

        atoms = []

        frase_limpa = self.limpar_texto(frase)
        texto = self.normalize(frase_limpa)

        if not texto:
            return atoms

        # =========================
        # padrão: nível 99 de X
        # =========================

        matches = re.findall(r"\bnível\s+\d+\s+de\s+([^.!?,;]+)", frase_limpa, flags=re.IGNORECASE)

        for match in matches:

            valor = self.limpar_fragmento(match)

            if valor:

                atoms.append(
                    self.criar_atom(
                        expression="nível 99 de " + valor,
                        pattern="nível 99 de {estado/defeito}",
                        function="debochar de um estado exagerado",
                        tone="sarcástico leve",
                        source_sentence=frase_limpa
                    )
                )

        # =========================
        # padrão: com confiança de X
        # =========================

        matches = re.findall(r"\bcom\s+confiança\s+de\s+([^.!?,;]+)", frase_limpa, flags=re.IGNORECASE)

        for match in matches:

            valor = self.limpar_fragmento(match)

            if valor:

                atoms.append(
                    self.criar_atom(
                        expression="com confiança de " + valor,
                        pattern="com confiança de {criatura/coisa absurda}",
                        function="assumir chute ou exagero com humor",
                        tone="debochado",
                        source_sentence=frase_limpa
                    )
                )

        # =========================
        # padrão: modo X
        # =========================

        matches = re.findall(r"\bmodo\s+([^.!?,;]+)", frase_limpa, flags=re.IGNORECASE)

        for match in matches:

            valor = self.limpar_fragmento(match)

            if valor:

                atoms.append(
                    self.criar_atom(
                        expression="modo " + valor,
                        pattern="modo {estado engraçado}",
                        function="rotular uma situação como estado cômico",
                        tone="brincalhão",
                        source_sentence=frase_limpa
                    )
                )

        # =========================
        # padrão: cartório/oráculo/bola de cristal/goblin
        # =========================

        nucleos_fortes = [
            "cartório do caos",
            "cartorio do caos",
            "oráculo quebrado",
            "oraculo quebrado",
            "bola de cristal em greve",
            "goblin sem documento",
            "goblin de cartório",
            "goblin de cartorio",
            "picolé de streamer",
            "picole de streamer",
            "carne e deadline",
            "clarividência falsa com glitter",
            "clarividencia falsa com glitter"
        ]

        for nucleo in nucleos_fortes:

            if self.normalize(nucleo) in texto:

                atoms.append(
                    self.criar_atom(
                        expression=nucleo,
                        pattern=self.inferir_pattern_nucleo(nucleo),
                        function=self.inferir_funcao_nucleo(nucleo),
                        tone="caótico debochado",
                        source_sentence=frase_limpa
                    )
                )

        # =========================
        # padrão: parece X
        # =========================

        matches = re.findall(r"\bparece\s+([^.!?,;]+)", frase_limpa, flags=re.IGNORECASE)

        for match in matches:

            valor = self.limpar_fragmento(match)

            if valor:

                atoms.append(
                    self.criar_atom(
                        expression="parece " + valor,
                        pattern="parece {comparação absurda}",
                        function="comparar uma situação com algo ridículo",
                        tone="sarcástico",
                        source_sentence=frase_limpa
                    )
                )

        # =========================
        # padrão: X de Y curto
        # =========================

        atoms.extend(self.extrair_substantivo_de_substantivo(frase_limpa))

        return self.filtrar_atoms_validos(atoms)

    def extrair_substantivo_de_substantivo(self, frase):

        atoms = []

        matches = re.findall(r"\b([A-Za-zÀ-ÿ]{4,})\s+de\s+([A-Za-zÀ-ÿ]{4,}(?:\s+[A-Za-zÀ-ÿ]{4,})?)", frase)

        bloqueados = [
            "hora de",
            "modo de",
            "tipo de",
            "coisa de",
            "resposta de",
            "frase de",
            "mensagem de",
            "arquivo de",
            "chat de",
            "live de",
            "canal de",
            "usuário de",
            "usuario de"
        ]

        for match in matches:

            expressao = (match[0] + " de " + match[1]).strip()
            expressao_norm = self.normalize(expressao)

            bloqueado = False

            for termo in bloqueados:

                if expressao_norm.startswith(self.normalize(termo)):
                    bloqueado = True
                    break

            if bloqueado:
                continue

            palavras = expressao.split()

            if len(palavras) > 5:
                continue

            atoms.append(
                self.criar_atom(
                    expression=expressao,
                    pattern="{objeto/conceito} de {coisa absurda}",
                    function="criar imagem cômica curta",
                    tone="debochado",
                    source_sentence=frase
                )
            )

        return atoms

    # =========================
    # 🧼 LIMPAR FRAGMENTO
    # =========================

    def limpar_fragmento(self, texto):

        texto = self.limpar_texto(texto)

        texto = re.sub(r"\b(meu|minha|meus|minhas|seu|sua|seus|suas)\b", "", texto, flags=re.IGNORECASE)
        texto = re.sub(r"\bné\b", "", texto, flags=re.IGNORECASE)
        texto = re.sub(r"\bvey\b", "", texto, flags=re.IGNORECASE)
        texto = re.sub(r"\bmeu querido\b", "", texto, flags=re.IGNORECASE)

        texto = texto.strip(" .,!?:;")
        texto = re.sub(r"\s+", " ", texto)

        palavras = texto.split()

        if len(palavras) > 5:
            texto = " ".join(palavras[:5])

        return texto.strip()

    # =========================
    # 🧱 CRIAR ATOM
    # =========================

    def criar_atom(self, expression, pattern, function, tone, source_sentence):

        expression = self.limpar_texto(expression)
        pattern = str(pattern).strip()
        function = str(function).strip()
        tone = str(tone).strip()
        source_sentence = self.limpar_texto(source_sentence)

        return {
            "type": "style_atom",
            "expression": expression,
            "pattern": pattern,
            "function": function,
            "tone": tone,
            "source_sentence": source_sentence,
            "score": self.calcular_score_atom(expression, pattern, function, tone, source_sentence)
        }

    def filtrar_atoms_validos(self, atoms):

        validos = []

        for atom in atoms:

            expression = atom.get("expression", "").strip()
            expression_norm = self.normalize(expression)

            if not expression:
                continue

            if len(expression) < STYLE_MIN_EXPRESSION_LEN:
                continue

            if len(expression) > STYLE_MAX_EXPRESSION_LEN:
                continue

            if self.contem_chat_bruto(expression):
                continue

            if expression_norm.endswith("?"):
                continue

            if "http" in expression_norm:
                continue

            ruins = [
                "vem que",
                "vem ca",
                "vem cá",
                "vamos la",
                "vamos lá",
                "se quiser",
                "pode me fazer",
                "giria escolhida",
                "gíria escolhida",
                "deboche com",
                "aí vai",
                "ai vai",
                "ta ai",
                "tá aí",
                "velho",
                "meu bom"
            ]

            ruim = False

            for termo in ruins:

                if self.normalize(termo) in expression_norm:
                    ruim = True
                    break

            if ruim:
                continue

            validos.append(atom)

        return validos

    def deduplicar_atoms(self, atoms):

        vistos = set()
        resultado = []

        for atom in atoms:

            key = self.gerar_key_atom(atom)

            if key in vistos:
                continue

            vistos.add(key)
            resultado.append(atom)

        return resultado

    # =========================
    # 🧮 SCORE
    # =========================

    def calcular_score_atom(self, expression, pattern, function, tone, source_sentence):

        texto = self.normalize(expression)
        source = self.normalize(source_sentence)

        score = 0.0

        fortes = [
            "goblin",
            "glitter",
            "picolé",
            "picole",
            "streamer",
            "cartório",
            "cartorio",
            "caos",
            "oráculo",
            "oraculo",
            "deadline",
            "inferno",
            "boss final",
            "powerpoint",
            "multa emocional",
            "clarividencia",
            "clarividência",
            "nível 99",
            "nivel 99"
        ]

        for termo in fortes:

            if self.normalize(termo) in texto:
                score += 0.25

        if pattern:
            score += 0.2

        if function:
            score += 0.1

        if tone:
            score += 0.1

        palavras = texto.split()

        if 2 <= len(palavras) <= 6:
            score += 0.2

        if len(palavras) > 8:
            score -= 0.25

        penalidades = [
            "twitch",
            "canal",
            "live do natan",
            "programação",
            "programacao",
            "vem torcer",
            "acompanhar a live",
            "mensagem",
            "usuário",
            "usuario"
        ]

        for termo in penalidades:

            if self.normalize(termo) in texto:
                score -= 0.25

        if source.endswith("?"):
            score -= 0.15

        if score < 0:
            score = 0.0

        if score > 1:
            score = 1.0

        return round(score, 2)

    # =========================
    # 🧠 INFERÊNCIAS
    # =========================

    def inferir_pattern_nucleo(self, nucleo):

        texto = self.normalize(nucleo)

        if "cartorio" in texto:
            return "cartório do {conceito caótico}"

        if "oraculo" in texto:
            return "oráculo {defeituoso/absurdo}"

        if "goblin" in texto:
            return "goblin de {função absurda}"

        if "picole" in texto:
            return "{objeto/pessoa} vira picolé de {contexto}"

        if "deadline" in texto:
            return "ser de carne e {problema moderno}"

        if "clarividencia" in texto:
            return "clarividência falsa com {efeito exagerado}"

        return "{expressão curta de estilo}"

    def inferir_funcao_nucleo(self, nucleo):

        texto = self.normalize(nucleo)

        if "cartorio" in texto:
            return "brincar com validação, burocracia ou memória"

        if "oraculo" in texto or "clarividencia" in texto:
            return "admitir incerteza com deboche"

        if "goblin" in texto:
            return "assumir erro, chute ou caos com humor"

        if "picole" in texto:
            return "exagerar uma situação de frio ou desconforto"

        if "deadline" in texto:
            return "zoar o Natan como humano ocupado"

        return "reforçar personalidade da Diana"

    # =========================
    # 💾 CANDIDATOS
    # =========================

    def gerar_key_atom(self, atom):

        expression = self.normalize(atom.get("expression", ""))
        pattern = self.normalize(atom.get("pattern", ""))

        return expression + "|" + pattern

    def encontrar_candidato(self, atom):

        key = self.gerar_key_atom(atom)

        for candidate in self.candidates:

            if self.gerar_key_atom(candidate) == key:
                return candidate

        return None

    def registrar_atom(self, atom):

        if not atom:
            return None

        existente = self.encontrar_candidato(atom)

        agora = self.agora()

        if existente:

            existente["occurrences"] = existente.get("occurrences", 1) + 1
            existente["updated_at"] = agora

            exemplos = existente.get("examples", [])

            source = atom.get("source_sentence", "")

            if source and source not in exemplos:
                exemplos.append(source)

            existente["examples"] = exemplos[-5:]

            if atom.get("score", 0) > existente.get("score", 0):
                existente["score"] = atom.get("score", 0)

            print(
                "🎭 Candidato de estilo:",
                existente.get("expression", ""),
                "| score:",
                existente.get("score", 0),
                "| ocorrências:",
                existente.get("occurrences", 1)
            )

            if self.deve_promover(existente):
                self.promover(existente)

            return existente

        candidate = {
            "type": "style_atom",
            "expression": atom.get("expression", ""),
            "pattern": atom.get("pattern", ""),
            "function": atom.get("function", ""),
            "tone": atom.get("tone", ""),
            "source_sentence": atom.get("source_sentence", ""),
            "examples": [atom.get("source_sentence", "")],
            "score": atom.get("score", 0),
            "occurrences": 1,
            "status": "candidate",
            "created_at": agora,
            "updated_at": agora
        }

        self.candidates.append(candidate)

        print(
            "🎭 Candidato de estilo:",
            candidate.get("expression", ""),
            "| score:",
            candidate.get("score", 0),
            "| ocorrências:",
            candidate.get("occurrences", 1)
        )

        if self.deve_promover(candidate):
            self.promover(candidate)

        return candidate

    # =========================
    # ✅ PROMOÇÃO
    # =========================

    def deve_promover(self, candidate):

        if not STYLE_AUTO_PROMOTION_ENABLED:
            return False

        if candidate.get("occurrences", 0) >= STYLE_PROMOTION_OCCURRENCES:
            return True

        if candidate.get("score", 0) >= STYLE_PROMOTION_SCORE:
            return True

        return False

    def promover(self, candidate):

        if not candidate:
            return False

        expression = candidate.get("expression", "").strip()

        if not expression:
            return False

        for item in self.promoted:

            if self.normalize(item.get("expression", "")) == self.normalize(expression):
                candidate["status"] = "promoted"
                candidate["promoted_at"] = self.agora()
                self.save_all()
                return True

        promoted_item = {
            "type": "style_atom",
            "expression": candidate.get("expression", ""),
            "pattern": candidate.get("pattern", ""),
            "function": candidate.get("function", ""),
            "tone": candidate.get("tone", ""),
            "examples": candidate.get("examples", []),
            "source_sentence": candidate.get("source_sentence", ""),
            "promoted_at": self.agora()
        }

        self.promoted.append(promoted_item)

        candidate["status"] = "promoted"
        candidate["promoted_at"] = self.agora()
        candidate["updated_at"] = self.agora()

        print("🎭 Expressão de estilo promovida:", expression)

        self.save_all()

        return True

    def promover_ultimo(self):

        for candidate in reversed(self.candidates):

            if candidate.get("status") == "candidate":
                return self.promover(candidate)

        print("⚠️ Nenhum candidato de estilo disponível para promover.")
        return False

    def promover_ultimo_candidato(self):

        return self.promover_ultimo()

    # =========================
    # 🧠 PROCESSAR RESPOSTA
    # =========================

    def processar_interacao(self, user_text, response_text):

        return self.processar_resposta(user_text, response_text)

    def processar_resposta(self, user_text, response_text):

        if self.deve_ignorar_resposta(user_text, response_text):
            return []

        atoms = self.extrair_atoms_da_resposta(response_text)

        if not atoms:
            return []

        registrados = []

        for atom in atoms:

            registrado = self.registrar_atom(atom)

            if registrado:
                registrados.append(registrado)

        self.save_all()

        return registrados

    # =========================
    # 📚 CONTEXTO PARA PROMPT
    # =========================

    def get_style_context(self):

        if not self.promoted:
            return None

        itens = self.promoted[-STYLE_CONTEXT_LIMIT:]

        linhas = []

        linhas.append("ESTILO AUTÔNOMO PROMOVIDO DA DIANA:")
        linhas.append("Use estes átomos como inspiração de estilo, não como frases obrigatórias.")

        for item in itens:

            expression = item.get("expression", "")
            pattern = item.get("pattern", "")
            function = item.get("function", "")
            tone = item.get("tone", "")

            linha = "- " + expression

            detalhes = []

            if pattern:
                detalhes.append("padrão: " + pattern)

            if function:
                detalhes.append("função: " + function)

            if tone:
                detalhes.append("tom: " + tone)

            if detalhes:
                linha += " (" + "; ".join(detalhes) + ")"

            linhas.append(linha)

        return "\n".join(linhas)

    # =========================
    # 🧪 DEBUG
    # =========================

    def get_status_text(self):

        candidatos_ativos = 0

        for candidate in self.candidates:

            if candidate.get("status") == "candidate":
                candidatos_ativos += 1

        auto_status = "ATIVADA" if STYLE_AUTO_PROMOTION_ENABLED else "DESATIVADA"

        return (
            "🎭 StyleAutonomy\n"
            + "Candidatos ativos: "
            + str(candidatos_ativos)
            + "\nExpressões promovidas: "
            + str(len(self.promoted))
            + "\nPromoção automática: "
            + auto_status
        )

    def agora(self):

        return int(time.time())