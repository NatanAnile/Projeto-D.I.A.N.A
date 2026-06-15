# -*- coding: utf-8 -*-

# =========================
# 🎲 ACTIVITY CONTEXT PROVIDER
# =========================

import json
import re
import unicodedata
from pathlib import Path


class ActivityContextProvider:

    def __init__(self, path="data/context/active_activity.json"):

        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.state = self._load()

    # =========================
    # 📦 ESTADO
    # =========================

    def default_state(self):

        return {
            "active": False,
            "kind": "",
            "domain": "",
            "participants": ["Neitan", "Diana"],
            "roles": {},
            "rules": [],
            "score": {"Neitan": 0, "Diana": 0},
            "round": 1,
            "turn": "",
            "last_action": "",
            "expected_next_action": ""
        }

    def _load(self):

        if not self.path.exists():
            state = self.default_state()
            self._save_state(state)
            return state

        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                base = self.default_state()
                base.update(data)
                return base
        except Exception:
            pass

        state = self.default_state()
        self._save_state(state)
        return state

    def _save_state(self, state=None):

        if state is not None:
            self.state = state

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.state, ensure_ascii=False, indent=4), encoding="utf-8")

    def clear(self):

        self.state = self.default_state()
        self._save_state()

    # =========================
    # 🧼 UTIL
    # =========================

    def normalize(self, text):

        text = str(text or "").lower().strip()
        text = unicodedata.normalize("NFD", text)
        text = "".join(char for char in text if unicodedata.category(char) != "Mn")
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _add_rule(self, rule):

        rule = str(rule or "").strip()
        if not rule:
            return

        rules = self.state.setdefault("rules", [])
        if rule not in rules:
            rules.append(rule)
        self.state["rules"] = rules[-8:]

    def _score_text(self):

        score = self.state.get("score") or {}
        n = int(score.get("Neitan", 0) or 0)
        t = int(score.get("Diana", 0) or 0)
        return f"Neitan {n} x {t} Diana"

    # =========================
    # 🔎 DETECÇÃO DE ATIVIDADE
    # =========================

    def _detect_start(self, texto):

        if not re.search(r"\b(vamos|bora|vamo|come[cç]a|comecar|fazer|jogar|brincar)\b", texto):
            return None

        if re.search(r"\b(batalha|duelo|competicao|competição|desafio|jogo|minigame|brincadeira)\b", texto) or re.search(r"\bbrincar\s+de\b", texto) or re.search(r"\bchat\s+contra\b", texto):
            domain = self._detect_domain(texto)
            if domain:
                return {
                    "kind": "minigame",
                    "domain": domain
                }

        return None

    def _detect_domain(self, texto):

        if re.search(r"\bpiada|piadas|trocadilho|trocadilhos\b", texto):
            return "piadas"
        if re.search(r"\brima|rimas\b", texto):
            return "rimas"
        if re.search(r"\bcharada|charadas\b", texto):
            return "charadas"
        if re.search(r"\bpergunta|perguntas|quiz\b", texto):
            return "perguntas"
        if re.search(r"\bchat\b", texto):
            return "chat"

        match = re.search(r"\b(?:batalha|duelo|competicao|competição|desafio|jogo|minigame|brincadeira)\s+de\s+([a-z0-9_ ]{2,40})", texto)
        if match:
            return re.sub(r"\s+", "_", match.group(1).strip())

        return "geral"

    def _start_activity(self, info):

        self.state = self.default_state()
        self.state["active"] = True
        self.state["kind"] = info.get("kind", "minigame")
        self.state["domain"] = info.get("domain", "geral")
        self.state["turn"] = "definindo_regras"
        self.state["last_action"] = "Neitan propôs uma atividade."
        self.state["expected_next_action"] = "confirmar atividade e aguardar regras ou primeira jogada"
        self._save_state()

    def _is_end(self, texto):

        return bool(re.search(r"\b(acabou|encerra|encerrar|termina|terminar|fim|para o jogo|parar o jogo|fim do jogo|chega do jogo|cancela o jogo|termina a brincadeira)\b", texto))

    def _is_score_query(self, texto):

        return bool(re.search(r"\b(placar|quanto ta|quanto está|quem ta ganhando|quem está ganhando|quem ganhou|pontuacao|pontuação)\b", texto))

    def _is_rule_text(self, texto):

        if re.search(r"\b(regra|regras|eu julgo|eu sou juiz|voce cuida|você cuida|voce marca|você marca|quem ganha)\b", texto):
            return True

        if re.search(r"\b(cuida|marca|controla|anota)\b.*\bplacar\b", texto):
            return True

        return False

    def _is_assistant_turn_request(self, texto):

        return bool(re.search(r"\b(sua vez|agora voce|agora você|manda a sua|vai voce|vai você|tua vez|turno da diana)\b", texto))

    def _is_user_play(self, texto):

        if re.search(r"\b(eu comeco|eu começo|minha vez|eu vou|eu mando)\b", texto):
            return True

        domain = self.state.get("domain", "")
        if domain == "piadas":
            return bool(re.search(r"\b(por que|porque|pra que|para que|piada|trocadilho)\b", texto))

        return False

    def _apply_rules(self, user_text, texto):

        self._add_rule(user_text)
        roles = self.state.setdefault("roles", {})

        if "eu julgo" in texto or "eu sou juiz" in texto or "quem ganha" in texto:
            roles["Neitan"] = "juiz da atividade"

        if "voce cuida" in texto or "você cuida" in texto or "voce marca" in texto or "você marca" in texto or "placar" in texto:
            roles["Diana"] = "competidora e responsável pelo placar"

        if "Diana" not in roles:
            roles["Diana"] = "participante da atividade"
        if "Neitan" not in roles:
            roles["Neitan"] = "participante da atividade"

        self.state["roles"] = roles
        self.state["last_action"] = "Regras atualizadas por Neitan."
        self.state["expected_next_action"] = "manter a atividade ativa e obedecer às regras combinadas"
        self._save_state()

    def _apply_score(self, texto):

        score = self.state.setdefault("score", {"Neitan": 0, "Diana": 0})

        if re.search(r"\bponto\s+(pra|para)\s+(mim|eu|neitan|natan)\b", texto):
            score["Neitan"] = int(score.get("Neitan", 0) or 0) + 1
            self.state["score"] = score
            self.state["round"] = int(self.state.get("round", 1) or 1) + 1
            self.state["turn"] = "Diana"
            self.state["last_action"] = "Neitan julgou ponto para ele."
            self.state["expected_next_action"] = "Diana deve aceitar o placar e continuar a atividade"
            self._save_state()
            return f"Ponto pro Neitan. Placar: {self._score_text()}."

        if re.search(r"\bponto\s+(pra|para)\s+(voce|você|diana|ti)\b", texto):
            score["Diana"] = int(score.get("Diana", 0) or 0) + 1
            self.state["score"] = score
            self.state["round"] = int(self.state.get("round", 1) or 1) + 1
            self.state["turn"] = "Neitan"
            self.state["last_action"] = "Neitan julgou ponto para Diana."
            self.state["expected_next_action"] = "Diana deve aceitar o placar e aguardar a próxima jogada"
            self._save_state()
            return f"Ponto pra mim. Placar: {self._score_text()}."

        if re.search(r"\b(empate|ninguem pontua|ninguém pontua|sem ponto)\b", texto):
            self.state["round"] = int(self.state.get("round", 1) or 1) + 1
            self.state["last_action"] = "Rodada sem ponto."
            self.state["expected_next_action"] = "continuar a atividade sem alterar placar"
            self._save_state()
            return f"Sem ponto nessa rodada. Placar continua: {self._score_text()}."

        return ""

    # =========================
    # 🔁 TURNO
    # =========================

    def process_user_turn(self, user_text):

        user_text = str(user_text or "").strip()
        texto = self.normalize(user_text)
        direct_response = ""
        task = ""
        event = "none"

        start_info = self._detect_start(texto)
        if start_info and not self.state.get("active"):
            self._start_activity(start_info)
            event = "activity_started"
            task = (
                "Neitan propôs uma atividade/minigame. Confirme de forma curta que entrou no jogo, "
                "não invente placar ainda e peça ou aguarde as regras/primeira jogada."
            )
            return self._result(event=event, task=task, direct_response=direct_response)

        if not self.state.get("active"):
            return self._result(event=event, task=task, direct_response=direct_response)

        if self._is_end(texto):
            placar = self._score_text()
            domain = self.state.get("domain", "atividade")
            self.clear()
            return self._result(
                event="activity_ended",
                task="",
                direct_response=f"Atividade encerrada. Placar final: {placar}."
            )

        score_response = self._apply_score(texto)
        if score_response:
            return self._result(event="score_updated", task="", direct_response=score_response)

        # Regra com a palavra "placar" precisa ser interpretada como regra,
        # não como pergunta de placar.
        if self._is_rule_text(texto):
            self._apply_rules(user_text, texto)
            task = (
                "Neitan definiu ou ajustou as regras da atividade ativa. Confirme o combinado em uma frase curta. "
                "Não abandone a atividade e não comece outra pauta."
            )
            return self._result(event="rules_updated", task=task, direct_response="")

        if self._is_score_query(texto):
            return self._result(event="score_query", task="", direct_response=f"Placar atual: {self._score_text()}.")

        if self._is_user_play(texto):
            self.state["last_action"] = "Neitan executou a jogada dele."
            self.state["turn"] = "Diana"
            self.state["expected_next_action"] = "aguardar chamada da vez da Diana ou preparar resposta da atividade"
            self._save_state()
            task = (
                "Neitan executou a jogada dele dentro da atividade. Reaja curto, mantenha o jogo ativo, "
                "não dê ponto porque Neitan é o juiz se essa regra foi definida."
            )
            return self._result(event="user_played", task=task, direct_response="")

        if self._is_assistant_turn_request(texto):
            self.state["turn"] = "Diana"
            self.state["expected_next_action"] = "diana_turn_now"
            self._save_state()
            task = self._assistant_turn_task()
            return self._result(event="assistant_turn", task=task, direct_response="")

        task = (
            "Há uma atividade ativa na sessão. Responda mantendo as regras, papéis, turno e placar em mente. "
            "Se a mensagem for ambígua, interprete como parte da atividade antes de trocar de assunto."
        )
        return self._result(event="activity_context", task=task, direct_response="")

    def record_assistant_response(self, assistant_text):

        if not self.state.get("active"):
            return

        if self.state.get("expected_next_action") == "diana_turn_now":
            self.state["last_action"] = "Diana executou a jogada dela."
            self.state["turn"] = "Neitan"
            self.state["expected_next_action"] = "aguardar julgamento do Neitan ou próxima jogada"
            self._save_state()

    def _assistant_turn_task(self):

        domain = self.state.get("domain", "geral")
        score_text = self._score_text()

        if domain == "piadas":
            return (
                "É a vez da Diana na atividade ativa de piadas. "
                "Obrigação deste turno: conte UMA piada curta agora, com graça/punchline completa. "
                "Não diga que vai contar; conte. Não peça regra de novo. "
                f"Depois da piada, aguarde o julgamento do Neitan. Placar atual: {score_text}."
            )

        if domain == "rimas":
            return (
                "É a vez da Diana na atividade ativa de rimas. "
                "Obrigação deste turno: mande UMA rima curta agora. Não prepare palco e não peça regra de novo. "
                f"Depois, aguarde o julgamento do Neitan. Placar atual: {score_text}."
            )

        if domain == "perguntas":
            return (
                "É a vez da Diana na atividade ativa de perguntas. "
                "Obrigação deste turno: faça UMA pergunta curta agora. Não prepare palco. "
                f"Placar atual: {score_text}."
            )

        if domain == "charadas":
            return (
                "É a vez da Diana na atividade ativa de charadas. "
                "Execute a ação esperada desse jogo: faça UMA charada curta agora. Não prepare palco. "
                f"Placar atual: {score_text}."
            )

        return (
            "É a vez da Diana na atividade ativa. Execute a ação esperada desse jogo agora, "
            "sem preparar palco e sem pedir regra de novo. "
            f"Placar atual: {score_text}."
        )

    def get_prompt_context(self):

        if not self.state.get("active"):
            return ""

        roles = self.state.get("roles") or {}
        rules = self.state.get("rules") or []

        lines = [
            f"kind: {self.state.get('kind', '')}",
            f"domain: {self.state.get('domain', '')}",
            "participants: " + ", ".join(str(x) for x in self.state.get("participants", [])),
            f"turn: {self.state.get('turn', '')}",
            f"round: {self.state.get('round', 1)}",
            f"score: {self._score_text()}",
            f"last_action: {self.state.get('last_action', '')}",
            f"expected_next_action: {self.state.get('expected_next_action', '')}",
        ]

        if roles:
            lines.append("roles:")
            for name, role in roles.items():
                lines.append(f"- {name}: {role}")

        if rules:
            lines.append("rules:")
            for rule in rules:
                lines.append(f"- {rule}")

        return "\n".join(lines)

    def _result(self, event, task="", direct_response=""):

        return {
            "event": event,
            "task": task,
            "direct_response": direct_response,
            "prompt_context": self.get_prompt_context(),
            "state": dict(self.state)
        }
