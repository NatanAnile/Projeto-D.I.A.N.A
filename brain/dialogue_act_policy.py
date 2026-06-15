# -*- coding: utf-8 -*-

# =========================
# 🧭 POLÍTICA DOS ATOS DE DIÁLOGO
# =========================

"""Inventário explícito do que cada DialogueAct pode fazer.

A regra principal da Diana 0.5 é simples: ato classificado não pode ficar no
limbo. Ou ele tem resposta direta determinística, ou está explicitamente
liberado para recuperação/LLM.
"""

DIRECT = "DIRECT"
RETRIEVAL_ALLOWED = "RETRIEVAL_ALLOWED"
LLM_ALLOWED = "LLM_ALLOWED"

DIALOGUE_ACT_POLICY = {
    "micro_ping": DIRECT,
    "feedback_short": DIRECT,
    "feedback_negative_previous_response": DIRECT,
    "factual_correction": DIRECT,
    "diana_self_query": DIRECT,
    "request_joke": DIRECT,
    "owner_preference_query": RETRIEVAL_ALLOWED,
    "normal": LLM_ALLOWED,
}

INTENTIONAL_NON_DIRECT_ACTS = {
    "owner_preference_query",
    "normal",
}


def policy_for(act):
    return DIALOGUE_ACT_POLICY.get(str(act or ""), LLM_ALLOWED)


def requires_direct_response(act):
    return policy_for(act) == DIRECT


def is_intentional_non_direct(act):
    return str(act or "") in INTENTIONAL_NON_DIRECT_ACTS
