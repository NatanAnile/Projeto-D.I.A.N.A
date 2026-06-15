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

    MICRO_PING_EXACT = {
        "ai", "ei", "opa", "oi", "hm", "hmm", "uhum", "aham",
        "fala", "e ai", "eai", "eae", "e aí"
    }

    JOKE_MARKERS = {
        "joke", "piada", "piadoca", "trocadilho", "humor", "churrasco"
    }

    FEEDBACK_VOCATIVOS = {"diana", "diana", "tasca"}
    FEEDBACK_INTENSIFICADORES = {"demais", "muito", "hein", "bagarai", "caramba"}

    def analyze(self, user_text, conv_history=None, turn_context=None):
        text = normalize_text(user_text)
        turn_context = turn_context or {}
        intent_hint = str(turn_context.get("input_intent_hint", "") or "").strip()

        if intent_hint == "micro_ping" or self._is_micro_ping(text):
            return DialogueActResult(
                act="micro_ping",
                target=TARGET_OWNER,
                direct_response=self._micro_ping_response(text),
                reason="microentrada/backchannel curto — fast-path sem LLM",
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

        if self._is_diana_self_query(text):
            return DialogueActResult(
                act="diana_self_query",
                target=TARGET_DIANA_SELF,
                direct_response=self._self_preference_response(text),
                reason="pergunta usa você/seu/sua e mira a própria Diana",
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
        if not text:
            return False
        return str(text or "").strip() in self.MICRO_PING_EXACT

    def _is_diana_self_query(self, text):
        return is_diana_self_target(text)

    def _is_owner_preference_query(self, text):
        return bool(re.search(r"\b(meu|minha|eu|neitan|natan)\b.*\b(favorit\w*|prefiro|gosto|curto|filme|jogo|comida|editor|serie|série)\b", text))

    def _is_factual_correction(self, text):
        if not text:
            return False

        # Pedido criativo continua sendo pedido criativo.
        if self._asks_joke(text):
            return False

        # Crítica de humor não é correção factual.
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

        # Pedido explícito de piada ruim continua sendo pedido criativo,
        # não crítica à resposta anterior.
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

        # Frases curtas de rejeição costumam ser avaliação direta da última fala.
        if re.fullmatch(r"(?:nada\s+a\s+ver|que\s+ruim|bem\s+ruim|muito\s+ruim)", text):
            return True

        # Quando a última fala foi uma piada, críticas curtas como "foi ruim",
        # "bem ruim" ou "nossa que ruim" também pertencem à resposta anterior.
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

    def _micro_ping_response(self, text):
        return choose_response("micro_ping", text)

    def _joke_response(self, text):
        return get_joke_response(text)

    def _self_preference_response(self, text):
        if "filme" in text:
            return "Eu curto terror espacial e ficção científica esquisita. Favorito cravado eu ainda não tenho, mas Alien fica rondando minha prateleira mental feito bicho folgado."
        if "jogo" in text:
            return "Eu gosto de jogo que dá margem pra caos controlado, rota torta e comentário atravessado. Favorito cravado meu ainda não está salvo."
        if "comida" in text:
            return "Eu não como, criatura. Mas se comesse, seria algo dramaticamente crocante só pra fazer barulho em momento inadequado."
        if "editor" in text or "ferramenta" in text:
            return "Eu ainda não tenho ferramenta favorita minha. Mas qualquer uma que não trave no export já começa com vantagem nessa rinha."
        if "serie" in text or "série" in text:
            return "Eu puxo mais pra ficção estranha, terror espacial e coisa com clima errado. Série favorita minha ainda não está cravada."
        return "Eu tenho preferências de Diana, sim: caos útil, deboche bem aplicado e nenhuma vontade de virar assistente corporativa de sapatinho liso."
