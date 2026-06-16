# -*- coding: utf-8 -*-

# =========================
# 🧠 SESSION CONTEXT
# =========================

import json
import re
import unicodedata
from pathlib import Path

from config import (
    CONTEXT_PROFILE_PATH,
    CONTEXT_SESSION_SUMMARY_PATH,
    CONTEXT_CURRENT_SESSION_PATH,
    OWNER_DISPLAY_NAME,
    OWNER_CASUAL_NAME
)


class SessionContext:

    def __init__(self):

        self.profile_path = Path(CONTEXT_PROFILE_PATH)
        self.summary_path = Path(CONTEXT_SESSION_SUMMARY_PATH)
        self.current_path = Path(CONTEXT_CURRENT_SESSION_PATH)

        self.profile_path.parent.mkdir(parents=True, exist_ok=True)
        self.summary_path.parent.mkdir(parents=True, exist_ok=True)
        self.current_path.parent.mkdir(parents=True, exist_ok=True)

        self.profile = self.load_profile()
        self.current = self.load_current_session()
        self.ensure_session_summary_format()

    # =========================
    # 📦 DEFAULTS
    # =========================

    def default_profile(self):

        return {
            "owner": {
                "name": OWNER_DISPLAY_NAME,
                "casual_name": OWNER_CASUAL_NAME,
                "aliases": ["Natan", "Neitan", "natan_anile"],
                "relationship": "Natan/Neitan é o criador e parceiro de bancada da Diana.",
                "known_preferences": {
                    "filme_favorito": "Alien",
                    "comida_favorita": "pizza"
                }
            },
            "diana": {
                "identity": "Diana é uma assistente/personagem de live do Natan.",
                "style": [
                    "caótica com contexto",
                    "debochada, mas útil",
                    "espontânea sem virar propaganda de live",
                    "pode provocar o Neitan com carinho",
                    "não deve fugir do assunto só para fazer piada"
                ],
                "boundaries": [
                    "não mencionar live, Twitch, chat, canal ou agenda sem contexto real",
                    "não inventar memória",
                    "não inventar reação do chat",
                    "em skill operacional, entregar o dado primeiro"
                ],
                "self_preferences": {
                    "filmes": ["ficção científica", "terror espacial", "coisas com atmosfera estranha"]
                }
            }
        }

    def default_current_session(self):

        return {
            "session_notes": [],
            "owner_session_preferences": {},
            "diana_session_notes": [],
            "style_feedback": [],
            "last_topics": []
        }

    # =========================
    # 📦 LOAD / SAVE
    # =========================

    def load_json(self, path, default):

        if not path.exists():
            self.save_json(path, default)
            return default

        try:

            data = json.loads(path.read_text(encoding="utf-8"))

            if isinstance(data, dict):
                base = default.copy()
                base.update(data)
                return base

        except Exception:
            pass

        self.save_json(path, default)
        return default

    def save_json(self, path, data):

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=4), encoding="utf-8")

    def load_profile(self):

        return self.load_json(self.profile_path, self.default_profile())

    def load_current_session(self):

        return self.load_json(self.current_path, self.default_current_session())

    def save_current_session(self):

        self.save_json(self.current_path, self.current)

    # =========================
    # 🧼 UTIL
    # =========================

    def normalize(self, text):

        text = str(text or "").lower().strip()
        text = unicodedata.normalize("NFD", text)
        text = "".join(char for char in text if unicodedata.category(char) != "Mn")
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def add_unique(self, key, value, limit=12):

        value = str(value).strip()

        if not value:
            return

        lista = self.current.get(key, [])

        if value in lista:
            lista.remove(value)

        lista.append(value)
        self.current[key] = lista[-limit:]

    # =========================
    # 🧠 CONTEXTO PARA PROMPT
    # =========================

    def _extract_manual_summary(self, text):

        text = str(text or "").strip()

        if not text:
            return "Diana Brain sem memória longa. Prioridade: conversa curta, coerente e contextual."

        manual_header = "## CONTEXTO MANUAL"
        auto_start = "<!-- DIANA_AUTO_START -->"

        if manual_header in text:
            manual = text.split(manual_header, 1)[1]
            if auto_start in manual:
                manual = manual.split(auto_start, 1)[0]
            return manual.strip()

        if auto_start in text:
            return text.split(auto_start, 1)[0].strip().lstrip("# ").strip()

        return text

    def _build_automatic_summary_block(self):

        linhas = [
            "<!-- DIANA_AUTO_START -->",
            "## ESTADO AUTOMÁTICO DA SESSÃO",
            "",
            "### Assuntos recentes"
        ]

        topics = self.current.get("last_topics", [])
        if topics:
            for item in topics[-8:]:
                linhas.append("- " + str(item))
        else:
            linhas.append("- Nenhum assunto registrado ainda.")

        linhas.extend(["", "### Preferências citadas nesta sessão"])
        prefs = self.current.get("owner_session_preferences", {})
        if prefs:
            for chave, valor in prefs.items():
                if isinstance(valor, list):
                    valor = ", ".join(str(v) for v in valor)
                linhas.append(f"- {chave}: {valor}")
        else:
            linhas.append("- Nenhuma preferência nova registrada.")

        linhas.extend(["", "### Feedback de estilo"])
        feedback = self.current.get("style_feedback", [])
        if feedback:
            for item in feedback[-6:]:
                linhas.append("- " + str(item))
        else:
            linhas.append("- Nenhum feedback de estilo registrado.")

        linhas.extend(["", "### Notas da sessão"])
        notes = self.current.get("session_notes", [])
        if notes:
            for item in notes[-10:]:
                linhas.append("- " + str(item))
        else:
            linhas.append("- Nenhuma nota registrada.")

        linhas.extend([
            "",
            "_A seção automática é atualizada pelo programa. Edite livremente apenas o CONTEXTO MANUAL._",
            "<!-- DIANA_AUTO_END -->"
        ])

        return "\n".join(linhas)

    def ensure_session_summary_format(self):

        try:
            existing = self.summary_path.read_text(encoding="utf-8") if self.summary_path.exists() else ""
            manual = self._extract_manual_summary(existing)
            formatted = (
                "# RESUMO EPISÓDICO DA DIANA\n\n"
                "## CONTEXTO MANUAL\n"
                + manual.strip()
                + "\n\n"
                + self._build_automatic_summary_block()
                + "\n"
            )
            self.summary_path.write_text(formatted, encoding="utf-8")
        except Exception as e:
            print("⚠️ SessionContext erro ao formatar resumo:", e)

    def get_session_summary(self):

        self.ensure_session_summary_format()

        try:
            return self.summary_path.read_text(encoding="utf-8").strip()
        except Exception:
            return ""

    def get_context_for_prompt(self, turn_context=None):

        turn_context = turn_context or {}

        owner = self.profile.get("owner", {})
        diana = self.profile.get("diana", {})

        linhas = []
        linhas.append("CONTEXTO FIXO LEVE — REPERTÓRIO PASSIVO:")
        linhas.append("Este bloco existe para dar chão à conversa. Não use como lista de assuntos para puxar.")
        linhas.append("Só mencione itens daqui quando forem diretamente relevantes à mensagem atual.")
        linhas.append("")
        linhas.append("IDENTIDADE:")
        linhas.append("- OWNER local é " + owner.get("name", "Natan") + ", também chamado de " + owner.get("casual_name", "Neitan") + ".")
        linhas.append("- Relação: " + owner.get("relationship", "Natan é o criador da Diana."))
        linhas.append("- Identidade da Diana: " + diana.get("identity", "Assistente/personagem do Natan."))
        linhas.append("- Use 'Neitan' ocasionalmente em conversa casual. Não comece toda resposta com o nome dele.")

        prefs = owner.get("known_preferences", {})

        if prefs:
            linhas.append("")
            linhas.append("PREFERÊNCIAS LEVES CONHECIDAS DO OWNER — USE APENAS SE A PERGUNTA PEDIR:")

            for chave, valor in prefs.items():
                linhas.append("- " + str(chave) + ": " + str(valor))

        session_prefs = self.current.get("owner_session_preferences", {})

        if session_prefs:
            linhas.append("")
            linhas.append("PREFERÊNCIAS CITADAS NESTA SESSÃO — USE APENAS SE RELEVANTE:")

            for chave, valor in session_prefs.items():
                linhas.append("- " + str(chave) + ": " + str(valor))

        style_notes = diana.get("style", [])

        if style_notes:
            linhas.append("")
            linhas.append("ESTILO DA DIANA — COMO RESPONDER, NÃO O QUE RESPONDER:")

            for item in style_notes:
                linhas.append("- " + str(item))

        boundaries = diana.get("boundaries", [])

        if boundaries:
            linhas.append("")
            linhas.append("LIMITES IMPORTANTES:")

            for item in boundaries:
                linhas.append("- " + str(item))

        resumo = self.get_session_summary()

        if resumo:
            linhas.append("\nRESUMO EPISÓDICO ENTRE SESSÕES — CONTEXTO, NÃO ROTEIRO:")
            linhas.append(str(resumo[:1200]))

        notes = self.current.get("session_notes", [])

        if notes:
            linhas.append("\nNOTAS DA SESSÃO ATUAL — USE SÓ SE AJUDAR A RESPONDER:")

            for note in notes[-8:]:
                linhas.append("- " + str(note))

        feedback = self.current.get("style_feedback", [])

        if feedback:
            linhas.append("\nFEEDBACK DE ESTILO RECENTE — PRIORIZE QUANDO O TURNO PEDIR COMPORTAMENTO:")

            for item in feedback[-6:]:
                linhas.append("- " + str(item))

        linhas.append(
            "\nREGRAS DE USO DO CONTEXTO:"
            "\n- Contexto fixo é repertório passivo, não pauta automática."
            "\n- Não mencione Alien, pizza, Super Metroid, speedrun, live ou chat só porque aparecem aqui."
            "\n- Se o usuário pediu uma tarefa, execute a tarefa antes de usar personalidade."
            "\n- Se uma preferência não estiver no contexto, admita que não sabe em vez de inventar."
            "\n- Pode ser caótica, mas não abandone o assunto."
        )

        return "\n".join(linhas)

    # =========================
    # 🔁 ATUALIZAÇÃO LEVE
    # =========================

    def registrar_turno(self, user_text, assistant_text, turn_context=None):

        turn_context = turn_context or {}
        user_text_clean = str(user_text).strip()
        texto = self.normalize(user_text_clean)

        source_role = str(turn_context.get("source", "OWNER") or "OWNER").upper().strip()
        is_owner = source_role == "OWNER"

        topic = str(turn_context.get("topic", "")).strip()

        if topic:
            self.add_unique("last_topics", topic, limit=8)

        # Fonte externa (chat, donate, Discord, arquivo lido etc.) nunca pode
        # virar preferência/fato pessoal do Neitan. Isso evita contaminação por
        # frases como "meu editor favorito é Premiere" dentro de chat ou arquivo.
        if is_owner:
            if "não quero que" in texto or "nao quero que" in texto or "quero que" in texto:
                self.add_unique("style_feedback", user_text_clean, limit=10)

            if "não puxa live" in texto or "nao puxa live" in texto or "propaganda de live" in texto:
                self.add_unique("style_feedback", "Natan não quer que a Diana puxe live/Twitch sem contexto.", limit=10)

            if "gosto quando" in texto or "curto quando" in texto:
                self.add_unique("style_feedback", user_text_clean, limit=10)

            self.capturar_preferencias_leves(user_text_clean)

        if topic and is_owner:
            self.add_unique("session_notes", "Assunto recente: " + topic, limit=10)

        self.save_current_session()
        self.ensure_session_summary_format()

    def _valor_preferencia_limpo(self, valor):

        valor = str(valor or "").strip()

        # Não salva pergunta/continuação como parte do valor.
        if "?" in valor:
            return ""

        # Remove continuação argumentativa sem destruir códigos como H.264 ou Qwen2.5.
        valor = re.split(r"\b(mas qual|qual desses|qual dos|e qual|sao cinco|são cinco)\b", valor, maxsplit=1)[0]
        valor = re.split(r"\s+(mas|porem|porém|só que|so que)\s+", valor, maxsplit=1)[0]

        # Corta pontuação final, mas preserva ponto/hífen dentro de valores técnicos.
        valor = valor.strip(" \t\r\n")
        valor = re.sub(r"[.!?]+$", "", valor).strip()
        valor = valor.strip(" ,:;\"\'")
        valor = re.sub(r"^(o|a|os|as)\s+", "", valor).strip()

        if not valor or len(valor) > 100:
            return ""

        return valor

    def _normalizar_valor_preferencia(self, chave, valor):

        valor = str(valor or "").strip()

        low = self.normalize(valor)

        if chave == "filme_alien_favorito":
            if "alien 2" in low or "aliens" in low or "resgate" in low:
                return "Aliens: O Resgate"

        if chave == "celular_favorito" or "celular" in chave:
            if "motola" in low or "motorola" in low:
                return "Motorola"

        if "codec" in chave:
            if "av1" in low:
                return "av1"
            if "h.264" in low or "h 264" in low or "h264" in low:
                return "h 264"

        return valor

    def _chave_generica_favorito(self, categoria):

        categoria = self.normalize(categoria)
        categoria = re.sub(r"[^a-z0-9_ ]+", " ", categoria)
        categoria = re.sub(r"\s+", "_", categoria).strip("_")
        categoria = re.sub(r"^(?:o|a|os|as)_+", "", categoria)

        if not categoria or len(categoria) > 40:
            return ""

        bloqueados = {"coisa", "negocio", "bagulho", "isso", "aquilo"}
        if categoria in bloqueados:
            return ""

        # Mapa conservador: mantém compatibilidade com chaves antigas,
        # mas corrige casos que quebraram a continuidade.
        aliases = {
            "comida": "comida_favorita",
            "marca": "marca_favorito",
            "franquia": "franquia_de_jogo_favorito",
            "franquia_de_jogo": "franquia_de_jogo_favorito",
            "serie": "serie_favorita",
            "banda": "banda_favorita",
        }

        if categoria in aliases:
            return aliases[categoria]

        return categoria + "_favorito"

    def _chaves_compat_preferencia(self, chave):

        compat = {
            "comida_favorita": ["comida_favorito"],
            "franquia_de_jogo_favorito": ["franquia_de_jogo_favorita", "franquia_favorita", "franquia_favorito"],
            "franquia_de_jogo_favorita": ["franquia_de_jogo_favorito", "franquia_favorita", "franquia_favorito"],
            "marca_favorito": ["marca_favorita"],
            "marca_favorita": ["marca_favorito"],
            "area_favorito": ["area_favorita"],
            "area_favorita": ["area_favorito"],
        }

        return compat.get(chave, [])

    def _limpar_prefixo_memoria(self, texto):

        texto = str(texto or "").strip()
        texto = re.sub(r"^\s*/?lembrar\s+", "", texto, flags=re.IGNORECASE).strip()
        texto = re.sub(r"^\s*guarda(?: isso)?:?\s+", "", texto, flags=re.IGNORECASE).strip()
        return texto

    def _salvar_preferencia(self, prefs, chave, valor):

        valor = self._normalizar_valor_preferencia(chave, valor)
        if not chave or not valor:
            return

        prefs[chave] = valor
        for chave_compat in self._chaves_compat_preferencia(chave):
            prefs.setdefault(chave_compat, valor)

    def _capturar_update_preferencia(self, texto, prefs):

        # Operações de substituição explícita e correções naturais:
        # - "meu X favorito não é A, é B"
        # - "troca/muda/atualiza/corrige meu X favorito para B"
        # - "atualiza aí: meu X favorito agora é B"
        # - "na real o X favorito é B"
        update_patterns = [
            r"\b(?:o\s+)?meu\s+([a-z0-9_ %+-]{2,60})\s+favorit[oa]s?\s+nao\s+e\s+.+?\s*,?\s+e\s+(.+)$",
            r"\b(?:a\s+)?minha\s+([a-z0-9_ %+-]{2,60})\s+favorit[oa]s?\s+nao\s+e\s+.+?\s*,?\s+e\s+(.+)$",
            r"\b(?:troca|muda|atualiza|corrige)(?:\s+ai)?\s*:?\s+(?:o\s+)?meu\s+([a-z0-9_ %+-]{2,60})\s+favorit[oa]s?\s+(?:para|pra)\s+(.+)$",
            r"\b(?:troca|muda|atualiza|corrige)(?:\s+ai)?\s*:?\s+(?:a\s+)?minha\s+([a-z0-9_ %+-]{2,60})\s+favorit[oa]s?\s+(?:para|pra)\s+(.+)$",
            r"\b(?:atualiza|muda|corrige)(?:\s+ai)?\s*:?\s+(?:o\s+)?meu\s+([a-z0-9_ %+-]{2,60})\s+favorit[oa]s?\s+agora\s+(?:e|eh)\s+(.+)$",
            r"\b(?:atualiza|muda|corrige)(?:\s+ai)?\s*:?\s+(?:a\s+)?minha\s+([a-z0-9_ %+-]{2,60})\s+favorit[oa]s?\s+agora\s+(?:e|eh)\s+(.+)$",
            r"\bna\s+real\s+(?:o\s+)?([a-z0-9_ %+-]{2,60})\s+favorit[oa]s?\s+(?:e|eh)\s+(.+)$",
            r"\bna\s+real\s+(?:a\s+)?([a-z0-9_ %+-]{2,60})\s+favorit[oa]s?\s+(?:e|eh)\s+(.+)$",
        ]

        for padrao in update_patterns:
            match = re.search(padrao, texto)
            if not match:
                continue
            categoria = match.group(1).strip()
            valor = self._valor_preferencia_limpo(match.group(2))
            chave_generica = self._chave_generica_favorito(categoria)
            if chave_generica and valor:
                self._salvar_preferencia(prefs, chave_generica, valor)
                return True

        return False

    def _limpar_valor_lista_gosto(self, valor):

        valor = self._valor_preferencia_limpo(valor)
        valor = re.sub(r"^(muito|bastante|demais)\s+", "", valor).strip()
        valor = re.sub(r"\s+(demais)$", "", valor).strip()
        return valor

    def capturar_preferencias_leves(self, user_text):

        texto = self.normalize(self._limpar_prefixo_memoria(user_text))
        prefs = self.current.get("owner_session_preferences", {})

        # Updates explícitos têm prioridade sobre captura genérica.
        self._capturar_update_preferencia(texto, prefs)

        padroes = [
            (r"\b(?:o )?meu filme alien favorito (?:e|eh)\s+(.+)$", "filme_alien_favorito"),
            (r"\bmeu filme favorito (?:e|eh)\s+(.+)$", "filme_favorito"),
            (r"\bminha comida favorita (?:e|eh)\s+(.+)$", "comida_favorita"),
            (r"\bmeu jogo favorito (?:e|eh)\s+(.+)$", "jogo_favorito"),
            (r"\b(?:eu\s+)?gosto\s+muito\s+de\s+(.+)$", "gosta_de"),
            (r"\b(?:eu\s+)?gosto\s+bastante\s+de\s+(.+)$", "gosta_de"),
            (r"\b(?:eu\s+)?gosto\s+de\s+(.+)$", "gosta_de"),
            (r"\b(?:eu\s+)?curto\s+muito\s+(.+)$", "gosta_de"),
            (r"\b(?:eu\s+)?curto\s+demais\s+(.+)$", "gosta_de"),
            (r"\b(?:eu\s+)?curto\s+(.+)$", "gosta_de"),
            (r"\btambem\s+gosto\s+de\s+(.+)$", "gosta_de"),
            (r"\btambem\s+curto\s+(.+)$", "gosta_de"),
        ]

        # Formas naturais de favorito:
        # - "Pra navegador, meu favorito é Brave"
        # - "Minha câmera favorita continua sendo Fuji X-S10"
        # - "Meu codec favorito pra live é AV1"
        # - "Meu movimento favorito em Super Metroid é wall jump"
        favor_verb = r"(?:e|eh|continua\s+sendo|segue\s+sendo|agora\s+e|agora\s+eh)"
        contexto = r"(?:\s+(?:de|do|da|dos|das|em|no|na|nos|nas|pra|para|pro|nessa|nesse)\s+[a-z0-9_ %+.\-]{2,80})?"
        favorite_patterns = [
            r"\b(?:pra|para|pro)\s+([a-z0-9_ %+.\-]{2,60})\s*,?\s+(?:o\s+)?meu\s+favorit[oa]s?\s+" + favor_verb + r"\s+(.+)$",
            r"\b(?:pra|para|pro)\s+([a-z0-9_ %+.\-]{2,60})\s*,?\s+(?:a\s+)?minha\s+favorit[oa]s?\s+" + favor_verb + r"\s+(.+)$",
            r"\b(?:o\s+)?meu\s+([a-z0-9_ %+.\-]{2,60})\s+favorit[oa]s?" + contexto + r"\s+" + favor_verb + r"\s+(.+)$",
            r"\b(?:a\s+)?minha\s+([a-z0-9_ %+.\-]{2,60})\s+favorit[oa]s?" + contexto + r"\s+" + favor_verb + r"\s+(.+)$",
        ]

        for padrao in favorite_patterns:
            match = re.search(padrao, texto)
            if not match:
                continue
            categoria = match.group(1).strip()
            valor = self._valor_preferencia_limpo(match.group(2))
            chave_generica = self._chave_generica_favorito(categoria)
            if chave_generica and valor:
                self._salvar_preferencia(prefs, chave_generica, valor)

        for padrao, chave in padroes:

            match = re.search(padrao, texto)

            if not match:
                continue

            if chave == "gosta_de":
                valor = self._limpar_valor_lista_gosto(match.group(1))
            else:
                valor = self._valor_preferencia_limpo(match.group(1))
                valor = self._normalizar_valor_preferencia(chave, valor)

            if not valor:
                continue

            if chave == "gosta_de":

                lista = prefs.get("gosta_de", [])

                if not isinstance(lista, list):
                    lista = []

                if valor not in lista:
                    lista.append(valor)

                prefs["gosta_de"] = lista[-20:]

            else:
                self._salvar_preferencia(prefs, chave, valor)

        self.current["owner_session_preferences"] = prefs
