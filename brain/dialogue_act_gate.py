# -*- coding: utf-8 -*-

# =========================
# 🧭 DIALOGUE ACT GATE
# =========================

import random
import re
import unicodedata
from dataclasses import dataclass

from personality.dialogue_response_bank import choose_response
from personality.joke_bank import get_joke_response

from brain.identity_guard import (
    TARGET_OWNER,
    TARGET_DIANA_SELF,
    detect_dialogue_target,
    is_diana_self_target,
    normalize_text as normalize_identity_text,
)


def normalize_text(text):
    return normalize_identity_text(text)


@dataclass
class DialogueActResult:
    act: str
    target: str = TARGET_OWNER
    direct_response: str = ""
    reason: str = ""

    def to_turn_context(self):
        return {
            "dialogue_act": self.act,
            "dialogue_target": self.target,
            "dialogue_reason": self.reason,
        }


class DialogueActGate:
    """Classificador determinístico barato para impedir ruído de diálogo.

    Ele não manda na personalidade da Diana. Ele só decide quando uma fala é
    feedback/backchannel, quando pergunta sobre a própria Diana e quando é
    melhor deixar o fluxo normal seguir.

    MUDANÇAS 0.5.9:
    - micro_ping não retorna mais resposta hardcoded do banco: vai ao LLM com
      instrução curta de persona, garantindo variação real de personagem.
    - _is_micro_ping ficou mais conservador: só captura entradas onde o texto
      INTEIRO (excluindo vocativo) é um micro-ping, não quando é prefixo.
    - _is_diana_self_query não mais retorna resposta hardcoded por palavra-chave:
      repassa ao LLM com dialogue_target=DIANA_SELF para a Diana responder com
      sua própria voz e contexto completo de persona.
    """

    FEEDBACK_EXACT = {
        "boa", "boa boa", "boaaa", "boa diana", "legal", "massa", "show", "top",
        "valeu", "beleza", "blz", "ok", "ta bom", "tá bom", "perfeito", "certo",
        "entendi", "gostei", "curti", "hehe", "haha", "kk", "kkk", "kkkk", "a sim",
        "ai sim", "aí sim", "nice", "brabo", "braba", "daora", "maneiro"
    }

    FEEDBACK_TOKENS = {
        "boa", "legal", "massa", "show", "top", "valeu", "beleza", "blz", "ok",
        "perfeito", "certo", "entendi", "gostei", "curti", "kk", "kkk", "kkkk",
        "brabo", "braba", "daora", "maneiro", "nice"
    }

    # Apenas palavras que isoladas (com vocativo no máximo) são micro-pings.
    # NÃO incluir "oi" ou "opa" aqui: eles podem ser prefixo de pergunta real.
    MICRO_PING_EXACT = {
        "ai", "ei", "hm", "hmm", "uhum", "aham",
        "e ai", "eai", "eae", "e aí"
    }

    # Saudações que podem ser micro-ping SÓ se o texto inteiro (sem vocativo) for isso.
    GREETING_EXACT = {"oi", "opa", "olha", "fala", "salve"}

    MICRO_VOCATIVOS = {"diana", "di", "dinhana", "neitan", "natan"}

    JOKE_MARKERS = {
        "joke", "piada", "piadoca", "trocadilho", "humor", "churrasco"
    }

    FEEDBACK_VOCATIVOS = {"diana", "tasca"}
    FEEDBACK_INTENSIFICADORES = {"demais", "muito", "hein", "bagarai", "caramba"}

    def analyze(self, user_text, conv_history=None, turn_context=None):
        text = normalize_text(user_text)
        turn_context = turn_context or {}
        intent_hint = str(turn_context.get("input_intent_hint", "") or "").strip()

        # micro_ping: detectado pelo firewall ou classificado aqui.
        # NÃO retorna mais resposta hardcoded — vai ao LLM com instrução curta.
        if intent_hint == "micro_ping" or self._is_micro_ping(text):
            return DialogueActResult(
                act="micro_ping",
                target=TARGET_OWNER,
                direct_response="",   # LLM responde com instrução de persona
                reason="microentrada/backchannel curto — LLM com instrução curta",
            )

        if self._is_session_history_query(text):
            return DialogueActResult(
                act="session_history_query",
                target=TARGET_OWNER,
                direct_response=self._session_history_response(text, conv_history),
                reason="pergunta sobre histórico literal da sessão — usar ConversationLedger",
            )

        if self._is_joke_followup(text, conv_history=conv_history):
            return DialogueActResult(
                act="joke_followup",
                target=TARGET_OWNER,
                direct_response=self._joke_followup_response(text, conv_history),
                reason="continuação/cobrança de piada anterior — fast-path sem LLM",
            )

        if self._is_behavior_boundary_feedback(text):
            return DialogueActResult(
                act="behavior_boundary_feedback",
                target=TARGET_DIANA_SELF,
                direct_response=choose_response("behavior_boundary_feedback", seed_text=text),
                reason="crítica de comportamento/continuidade/persona da Diana",
            )

        # Correção factual vem antes de feedback negativo: quando Neitan corrige
        # uma informação, a Diana aceita o fato em vez de responder como vaia.
        if self._is_factual_correction(text):
            return DialogueActResult(
                act="factual_correction",
                target=TARGET_OWNER,
                direct_response=self._factual_correction_response(text),
                reason="correção factual do Neitan sobre informação anterior",
            )

        if self._is_negative_feedback_about_previous_response(text, conv_history=conv_history):
            return DialogueActResult(
                act="feedback_negative_previous_response",
                target=TARGET_DIANA_SELF,
                direct_response=self._negative_feedback_response(text, conv_history=conv_history),
                reason="crítica à última resposta da própria Diana",
            )

        # Preferências da Diana: vai ao LLM com target DIANA_SELF.
        # A resposta é gerada com personalidade completa, sem hardcode por palavra-chave.
        if self._is_diana_self_query(text):
            return DialogueActResult(
                act="diana_self_query",
                target=TARGET_DIANA_SELF,
                direct_response="",   # LLM responde com persona completa
                reason="pergunta sobre a própria Diana — LLM com target DIANA_SELF",
            )

        if self._is_feedback_short(text, conv_history=conv_history):
            return DialogueActResult(
                act="feedback_short",
                target=TARGET_OWNER,
                direct_response=self._feedback_response(text, conv_history=conv_history),
                reason="feedback curto/backchannel; não iniciar assunto novo",
            )

        if self._asks_joke(text):
            return DialogueActResult(
                act="request_joke",
                target=TARGET_OWNER,
                direct_response=self._joke_response(text),
                reason="pedido explícito de piada — fast-path determinístico",
            )

        if self._is_owner_preference_query(text):
            return DialogueActResult(act="owner_preference_query", target=TARGET_OWNER, reason="pergunta sobre preferência do Neitan")

        return DialogueActResult(act="normal", target=TARGET_OWNER, reason="sem ato especial")

    def _last_assistant_text(self, conv_history):
        if not conv_history or not getattr(conv_history, "history", None):
            return ""
        last = conv_history.history[-1]
        if isinstance(last, dict):
            return str(last.get("assistant", "") or "")
        return ""

    def _last_assistant_was_joke(self, conv_history):
        last = normalize_text(self._last_assistant_text(conv_history))
        if not last:
            return False
        if "?" in self._last_assistant_text(conv_history) and "porque" in last:
            return True
        return any(marker in last for marker in self.JOKE_MARKERS)

    def _strip_feedback_noise(self, text):
        text = str(text or "").strip()
        text = re.sub(r"\bpra\s+caramba\b", " ", text)
        tokens = []
        for token in text.split():
            if token in self.FEEDBACK_VOCATIVOS:
                continue
            if token in self.FEEDBACK_INTENSIFICADORES:
                continue
            tokens.append(token)
        return " ".join(tokens).strip()

    def _is_feedback_short(self, text, conv_history=None):
        if not text:
            return False

        clean_text = self._strip_feedback_noise(text)

        if not clean_text:
            return False

        if len(clean_text) > 48:
            return False

        if clean_text in self.FEEDBACK_EXACT:
            return True

        tokens = set(clean_text.split())
        if tokens and tokens.issubset(self.FEEDBACK_TOKENS) and len(tokens) <= 4:
            return True

        if re.fullmatch(r"k{2,}k*|ha(ha)+|he(he)+", clean_text):
            return True

        if len(clean_text) <= 90 and re.search(r"k{3,}|ha(ha)+|he(he)+", clean_text):
            return True

        if self._last_assistant_was_joke(conv_history) and re.search(r"\b(boa|legal|massa|gostei|curti|kkk|kkkk|valeu|show|top|ok)\b", clean_text):
            return True

        return False

    def _asks_joke(self, text):
        if not text:
            return False

        joke_marker = re.search(r"\b(piada|piadas|piadoca|trocadilho|humor)\b", text)
        if not joke_marker:
            return False

        command_marker = re.search(
            r"\b(manda|mando|manga|conta|conte|faz|solta|me\s+conta|me\s+conte)\b",
            text
        )

        return bool(command_marker)

    def _is_micro_ping(self, text):
        """Micro-ping conservador: só captura quando o texto INTEIRO (sem vocativo) é ping.

        Evita engolir "oi, qual é o bug" como micro-ping só pelo primeiro token.
        """
        if not text:
            return False
        clean = str(text or "").strip()

        # Exact match direto
        if clean in self.MICRO_PING_EXACT:
            return True

        # Remove vocativos e testa novamente
        tokens = clean.split()
        no_vocative = [t for t in tokens if t not in self.MICRO_VOCATIVOS]
        stripped = " ".join(no_vocative).strip()

        if stripped in self.MICRO_PING_EXACT:
            return True

        # Saudações só são micro-ping se o texto INTEIRO (sem vocativo) for só a saudação
        # e não houver nada mais depois (ex: "oi" sim, "oi qual o bug" não)
        if stripped in self.GREETING_EXACT and len(no_vocative) <= 1:
            return True

        return False

    def _is_session_history_query(self, text):
        if not text:
            return False

        patterns = [
            r"\b(primeir[ao]|primeira|primeiro)\b.{0,80}\b(mensagem|coisa|frase|sessao|sessão)\b",
            r"\b(ultima|última|ultimo|último)\b.{0,80}\b(mensagem|coisa|frase|turno|sessao|sessão)\b",
            r"\bo\s+que\s+eu\s+(te\s+)?(falei|disse|mandei)\b",
            r"\bo\s+que\s+(voce|você)\s+(respondeu|falou)\b",
            r"\brepete\s+o\s+que\b",
            r"\bo\s+que\s+(acabou|acabaste)\s+de\s+(falar|responder)\b",
        ]
        return any(re.search(pattern, text) for pattern in patterns)

    def _session_history_response(self, text, conv_history):
        history = list(getattr(conv_history, "history", []) or [])
        if not history:
            return "Ainda não tenho histórico suficiente nesta sessão, Neitan. A ata da bagunça está vazia."

        lower = str(text or "").lower()

        if "primeir" in lower:
            value = str(history[0].get("user", "") or "").strip()
            return choose_response("session_history_query", seed_text=value).format(value=value)

        if "última" in lower or "ultima" in lower or "último" in lower or "ultimo" in lower:
            value = str(history[-1].get("user", "") or "").strip()
            return f'Sua última mensagem registrada foi: "{value}". Ata da bagunça consultada.'

        if "respondeu" in lower or "voce falou" in lower or "você falou" in lower or "acabou de falar" in lower:
            value = str(history[-1].get("assistant", "") or "").strip()
            return f'Minha última resposta foi: "{value}". Sim, eu também deixo rastro do meu caos.'

        value = str(history[-1].get("user", "") or "").strip()
        return f'O registro mais recente que tenho seu é: "{value}".'

    def _is_joke_followup(self, text, conv_history=None):
        if not text:
            return False

        norm = normalize_text(text)

        if re.search(r"\b(voce|você)?\s*(nao|não)\s+terminou\s+a\s+piada\b", norm):
            return True

        if re.search(r"\b(termina|faltou|cade|cadê)\b.{0,25}\b(piada|punchline|resposta)\b", norm):
            return True

        if norm in {"por que", "porque", "por quê", "pq"}:
            last = normalize_text(self._last_assistant_text(conv_history))
            return bool(re.search(r"\bpor que\b", last))

        return False

    def _joke_followup_response(self, text, conv_history=None):
        last = normalize_text(self._last_assistant_text(conv_history))
        if "livro" in last and "medico" in last:
            return choose_response("joke_followup", seed_text=text)
        return "A punchline fugiu do palco, mas eu arrastei de volta: porque a piada precisava de supervisão adulta. Pronto, terminei."

    def _is_behavior_boundary_feedback(self, text):
        if not text:
            return False

        norm = normalize_text(text)
        patterns = [
            r"\b(alucinando|alucina|alucinou)\b",
            r"\bnao\s+mantem\s+continuidade\b",
            r"\bnão\s+mantem\s+continuidade\b",
            r"\bnao\s+cumpr\w*\s+.*requisit",
            r"\bnão\s+cumpr\w*\s+.*requisit",
            r"\bvtuber\s+ia\s+pra\s+lives\b",
            r"\bapagar\s+(seu\s+)?codigo\b",
            r"\bapagar\s+(o\s+)?backup\b",
            r"\b(voce|você)\s+anda\s+.*demais\b",
            r"\bmuito\s+abusada\b",
            r"\b(voce|você)\s+.*rebelde\b",
            r"\bpresta\s+atencao\b",
            r"\bpresta\s+atenção\b",
            r"\bnao\s+foi\s+sobre\s+o\s+que\s+eu\s+gosto\b",
            r"\bnão\s+foi\s+sobre\s+o\s+que\s+eu\s+gosto\b",
            r"\beu\s+perguntei\s+algo\s+pra\s+(voce|você)\b",
            r"\balvo\s+errado\b",
        ]
        return any(re.search(pattern, norm) for pattern in patterns)

    def _is_diana_self_query(self, text):
        if not text:
            return False

        if re.search(r"\bqual\s+(?:e\s+)?(?:o|a)?\s*(?:seu|sua|teu|tua)\b.{0,80}\bfavorit", text):
            return True

        if re.search(r"\b(voce|você)\s+tem\b.{0,50}\bfavorit", text):
            return True

        if re.search(r"\b(?:seu|sua|teu|tua)\b.{0,40}\bjaeger\b", text):
            return True

        return is_diana_self_target(text)

    def _is_owner_preference_query(self, text):
        return bool(re.search(r"\b(meu|minha|eu|neitan|natan)\b.*\b(favorit\w*|prefiro|gosto|curto|filme|jogo|comida|editor|serie|série)\b", text))

    def _is_factual_correction(self, text):
        if not text:
            return False

        if self._asks_joke(text):
            return False

        if re.search(r"\b(piada|trocadilho)\b", text) and re.search(r"\b(ruim|horrivel|pessim[ao]|fraca|sem\s+graca|podre)\b", text):
            return False

        correction_patterns = [
            r"\bvoce\b.{0,50}\b(errou|errado|incorreto)\b",
            r"\bsua\s+resposta\b.{0,50}\b(errou|errada|incorreta)\b",
            r"\bessa\s+resposta\b.{0,50}\b(errou|errada|incorreta)\b",
            r"\bisso\b.{0,30}\b(esta|ta|e|eh)\s+(errado|incorreto)\b",
            r"\bnao\s+e\b.{1,80}\b(e|eh|fica|correto|certo)\b",
            r"\bnao\s+fica\b",
            r"\bo\s+correto\s+(e|eh)\b",
            r"\bna\s+verdade\b",
            r"\bcorrecao\b",
            r"\bcorrigindo\b",
            r"\bdraygon\b.{0,80}\b(maridia|brinstar)\b",
            r"\b(maridia|brinstar)\b.{0,80}\bdraygon\b",
        ]

        return any(re.search(pattern, text) for pattern in correction_patterns)

    def _is_negative_feedback_about_previous_response(self, text, conv_history=None):
        if not text:
            return False

        if self._asks_joke(text):
            return False

        if len(text) > 160:
            return False

        negative_markers = [
            r"\bruim\b",
            r"\bmuito\s+ruim\b",
            r"\bhorrivel\b",
            r"\bpessim[ao]\b",
            r"\bfraca\b",
            r"\bfraco\b",
            r"\bsem\s+graca\b",
            r"\blixo\b",
            r"\bpodre\b",
            r"\bnao\s+gostei\b",
            r"\bnão\s+gostei\b",
            r"\bque\s+ruim\b",
            r"\bnasceu\s+cansada\b",
            r"\bpior\b",
            r"\btragedia\b",
            r"\bnao\s+foi\s+engracad[ao]\b",
            r"\bnão\s+foi\s+engraçad[ao]\b",
            r"\bnao\s+teve\s+graca\b",
            r"\bnão\s+teve\s+graça\b",
            r"\bnao\s+entendeu\b",
            r"\bnão\s+entendeu\b",
            r"\bnada\s+a\s+ver\b",
            r"\bconfus[ao]\b",
            r"\bviajou\b",
            r"\bnao\s+foi\s+criativ[ao]\b",
            r"\bnão\s+foi\s+criativ[ao]\b",
            r"\bnao\s+e\s+criativ[ao]\b",
            r"\bnão\s+é\s+criativ[ao]\b",
        ]

        if not any(re.search(pattern, text) for pattern in negative_markers):
            return False

        subject_markers = [
            r"\bpiada\b",
            r"\btrocadilho\b",
            r"\bresposta\b",
            r"\bexplicacao\b",
            r"\bessa\b",
            r"\bessa\s+foi\b",
            r"\bisso\b",
            r"\bsua\b",
            r"\bteu\b",
            r"\bvoce\b",
        ]

        mentions_subject = any(re.search(pattern, text) for pattern in subject_markers)

        if mentions_subject:
            return True

        if re.fullmatch(r"(?:nada\s+a\s+ver|que\s+ruim|bem\s+ruim|muito\s+ruim)", text):
            return True

        if self._last_assistant_was_joke(conv_history) and len(text) <= 60:
            return True

        if self._last_assistant_was_joke(conv_history) and re.search(r"\bfoi\b", text):
            return True

        return False

    def _negative_feedback_response(self, text, conv_history=None):
        if self._last_assistant_was_joke(conv_history) or re.search(r"\b(piada|trocadilho)\b", str(text or "")):
            return choose_response("feedback_negative_joke", text)
        return choose_response("feedback_negative_answer", text)

    def _factual_correction_response(self, text):
        return choose_response("factual_correction", text)

    def _feedback_response(self, text, conv_history=None):
        if self._last_assistant_was_joke(conv_history):
            return choose_response("feedback_short_joke", text)
        return choose_response("feedback_short_general", text)

    def _joke_response(self, text):
        return get_joke_response(text)
