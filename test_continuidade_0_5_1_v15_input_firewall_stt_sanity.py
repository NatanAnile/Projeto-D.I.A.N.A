# -*- coding: utf-8 -*-
"""Bateria automática — Diana 0.5.1 v15

Foco:
- InputFirewall bloqueia lixo óbvio de STT antes do LLM;
- variantes de STT recuperáveis viram comandos limpos;
- microentradas como "Aí." viram micro_ping direto;
- request_joke continua fast-path;
- inventário de DialogueActs inclui micro_ping.
"""

import json
from pathlib import Path

from config import PROJECT_VERSION, ELEVENLABS_VOICE_ID
from runtime.input_firewall import InputFirewall
from brain.dialogue_act_gate import DialogueActGate
from brain.dialogue_act_policy import (
    DIRECT,
    RETRIEVAL_ALLOWED,
    LLM_ALLOWED,
    DIALOGUE_ACT_POLICY,
    INTENTIONAL_NON_DIRECT_ACTS,
    requires_direct_response,
)
from personality.dialogue_response_bank import response_count

ROOT = Path(__file__).resolve().parent


class FakeHistory:
    def __init__(self, assistant_text=""):
        self.history = []
        if assistant_text:
            self.history.append({"user": "teste", "assistant": assistant_text})


firewall = InputFirewall()
gate = DialogueActGate()
results = []


def add(scenario, text, kind, expected=None, observed=None, notes=None):
    status = "PASS" if not notes else "FAIL"
    results.append({
        "id": len(results) + 1,
        "scenario": scenario,
        "status": status,
        "input": text,
        "kind": kind,
        "expected": expected,
        "observed": observed,
        "notes": notes or [],
    })


def expect_equal(scenario, text, kind, observed, expected):
    notes = []
    if observed != expected:
        notes.append(f"esperado {expected!r}, veio {observed!r}")
    add(scenario, text, kind, expected=expected, observed=observed, notes=notes)


def expect_true(scenario, text, kind, condition, observed=""):
    add(scenario, text, kind, expected=True, observed=observed, notes=[] if condition else ["condição esperada não foi satisfeita"])


# =========================
# CONFIG / REPO
# =========================

expect_equal("config_v15", "PROJECT_VERSION", "config", PROJECT_VERSION, "0.5.1")
expect_equal("config_v15", "ELEVENLABS_VOICE_ID empty", "config", ELEVENLABS_VOICE_ID, "")

for rel in [
    ".gitattributes",
    ".gitignore",
    "README.md",
    "requirements.txt",
    ".env.example",
    ".github/workflows/tests.yml",
    "Diana.py",
    "runtime/__init__.py",
    "runtime/runtime_types.py",
    "runtime/input_firewall.py",
    "brain/dialogue_act_policy.py",
    "brain/dialogue_act_gate.py",
    "personality/dialogue_response_bank.py",
    "personality/joke_bank.py",
    "stt/stt_custom_variants.json",
    "test_continuidade_0_5_1_v15_input_firewall_stt_sanity.py",
    "Logs/CHANGELOG_0_5_1.txt",
]:
    expect_true("repo_files_v15", rel, "file_exists", (ROOT / rel).exists(), observed=str((ROOT / rel).exists()))

readme = (ROOT / "README.md").read_text(encoding="utf-8")
expect_true("readme_v15", "README versão 0.5.1", "file_contains", "0.5.1_INPUT_FIREWALL_STT_SANITY" in readme, observed=readme[:800])
expect_true("readme_v15", "README teste atual", "file_contains", "test_continuidade_0_5_1_v15_input_firewall_stt_sanity.py" in readme, observed=readme[:1400])

workflow = (ROOT / ".github/workflows/tests.yml").read_text(encoding="utf-8")
expect_true("ci_v15", "workflow roda teste v15", "file_contains", "test_continuidade_0_5_1_v15_input_firewall_stt_sanity.py" in workflow, observed=workflow)
expect_true("ci_v15", "workflow compila input_firewall", "file_contains", "runtime/input_firewall.py" in workflow, observed=workflow)

# =========================
# INPUT FIREWALL — MICROENTRADAS
# =========================

for text in ["Aí.", "ai", "opa", "hm", "hmm", "uhum", "aham", "e aí"]:
    packet = firewall.analyze(text, source="OWNER_TEXT")
    notes = []
    if packet.intent_hint != "micro_ping":
        notes.append(f"intent esperado micro_ping, veio {packet.intent_hint}")
    if packet.allow_llm:
        notes.append("micro_ping não pode liberar LLM")
    if packet.allow_memory:
        notes.append("micro_ping não pode liberar memória")
    if packet.allow_retrieval:
        notes.append("micro_ping não pode liberar retrieval")
    add(
        "input_firewall_micro_v15",
        text,
        "input_packet",
        expected="micro_ping + allow_llm=False",
        observed=str(packet),
        notes=notes,
    )

# =========================
# INPUT FIREWALL — STT RECUPERÁVEL
# =========================

for text, corrected in [
    ("Manga um piada.", "manda uma piada"),
    ("manga uma piada", "manda uma piada"),
    ("Manga piada", "manda piada"),
    ("Mando uma piada", "manda uma piada"),
    ("manda um piada", "manda uma piada"),
    ("conta um piada", "conta uma piada"),
]:
    packet = firewall.analyze(text, source="OWNER_STT")
    notes = []
    if packet.text != corrected:
        notes.append(f"texto corrigido esperado {corrected!r}, veio {packet.text!r}")
    if packet.intent_hint != "request_joke":
        notes.append(f"intent esperado request_joke, veio {packet.intent_hint!r}")
    if packet.allow_llm:
        notes.append("comando recuperado de STT não pode liberar LLM")
    if packet.allow_memory:
        notes.append("comando recuperado de STT não pode liberar memória")
    if packet.allow_retrieval:
        notes.append("comando recuperado de STT não pode liberar retrieval")
    add(
        "input_firewall_stt_recovered_v15",
        text,
        "input_packet",
        expected=f"{corrected} / request_joke",
        observed=str(packet),
        notes=notes,
    )

# =========================
# INPUT FIREWALL — BLOQUEIO DE ALUCINAÇÃO STT
# =========================

for text in [
    "Muito obrigado pra gente",
    "Muito obrigado para assistir",
    "Legendas pela comunidade",
    "Inscreva se no canal",
]:
    packet = firewall.analyze(text, source="OWNER_STT")
    notes = []
    if packet.quality != "BLOCKED":
        notes.append(f"quality esperada BLOCKED, veio {packet.quality}")
    if packet.allow_llm or packet.allow_memory or packet.allow_retrieval:
        notes.append("entrada bloqueada não pode liberar LLM/memória/retrieval")
    if not packet.direct_response:
        notes.append("entrada bloqueada precisa de resposta direta pedindo repetição")
    add("input_firewall_stt_block_v15", text, "input_packet", expected="BLOCKED", observed=str(packet), notes=notes)

packet_text = firewall.analyze("muito obrigado", source="OWNER_TEXT")
expect_equal("input_firewall_text_not_blocked_v15", "muito obrigado", "quality", packet_text.quality, "OK")
expect_true("input_firewall_text_not_blocked_v15", "muito obrigado", "allow_llm", packet_text.allow_llm, observed=str(packet_text))

# =========================
# DIALOGUE ACT — MICRO E JOKE COM FIREWALL
# =========================

for text in ["Aí.", "opa", "uhum"]:
    packet = firewall.analyze(text, source="OWNER_TEXT")
    r = gate.analyze(packet.text, conv_history=FakeHistory(), turn_context=packet.to_turn_context())
    notes = []
    if r.act != "micro_ping":
        notes.append(f"act esperado micro_ping, veio {r.act}")
    if not r.direct_response:
        notes.append("micro_ping precisa de direct_response")
    add("dialogue_micro_ping_v15", text, "dialogue_act", expected="micro_ping direct", observed=f"act={r.act}; response={r.direct_response}", notes=notes)

for text in ["Manga um piada.", "Mando uma piada", "manda um piada"]:
    packet = firewall.analyze(text, source="OWNER_STT")
    r = gate.analyze(packet.text, conv_history=FakeHistory(), turn_context=packet.to_turn_context())
    notes = []
    if r.act != "request_joke":
        notes.append(f"act esperado request_joke, veio {r.act}")
    if not r.direct_response:
        notes.append("request_joke precisa de direct_response")
    add("dialogue_stt_joke_v15", text, "dialogue_act", expected="request_joke direct", observed=f"text={packet.text}; act={r.act}; response={r.direct_response}", notes=notes)

# Fallback extra: mesmo sem firewall, gate já tolera manga/mando.
for text in ["manga um piada", "mando uma piada"]:
    r = gate.analyze(text, conv_history=FakeHistory(), turn_context={})
    expect_equal("dialogue_joke_tolerant_v15", text, "act", r.act, "request_joke")
    expect_true("dialogue_joke_tolerant_v15", text, "direct_response", bool(r.direct_response), observed=r.direct_response)

# =========================
# POLICY / RESPONSE BANK
# =========================

expected_policy = {
    "micro_ping": DIRECT,
    "feedback_short": DIRECT,
    "feedback_negative_previous_response": DIRECT,
    "factual_correction": DIRECT,
    "diana_self_query": DIRECT,
    "request_joke": DIRECT,
    "owner_preference_query": RETRIEVAL_ALLOWED,
    "normal": LLM_ALLOWED,
}

for act, policy in expected_policy.items():
    expect_equal("dialogue_policy_v15", act, "policy", DIALOGUE_ACT_POLICY.get(act), policy)

for act, policy in DIALOGUE_ACT_POLICY.items():
    if policy == DIRECT:
        expect_true("dialogue_policy_v15", act, "requires_direct", requires_direct_response(act), observed=str(policy))
    else:
        expect_true("dialogue_policy_v15", act, "intentional_non_direct", act in INTENTIONAL_NON_DIRECT_ACTS, observed=str(policy))

expect_true("response_bank_v15", "micro_ping count", "count", response_count("micro_ping") >= 8, observed=str(response_count("micro_ping")))

# =========================
# STT VARIANTS
# =========================

variants = json.loads((ROOT / "stt/stt_custom_variants.json").read_text(encoding="utf-8"))
replacements = variants.get("replacements", {})
for key in ["manga um piada", "manga uma piada", "mando uma piada", "manda um piada"]:
    expect_true("stt_variants_v15", key, "replacement_exists", key in replacements, observed=str(replacements.get(key)))

# =========================
# RELATÓRIOS
# =========================

failed = [r for r in results if r["status"] != "PASS"]
report_txt = [
    "# Relatório — Teste Continuidade 0.5.1 v15 — input firewall STT sanity",
    "",
    f"Total: {len(results)}",
    f"Passou: {len(results) - len(failed)}",
    f"Falhou: {len(failed)}",
    "",
]

if failed:
    for item in failed:
        report_txt += [
            f"## ❌ {item['id']} — {item['input']}",
            f"Cenário: {item['scenario']}",
            f"Kind: {item['kind']}",
            f"Esperado: {item.get('expected')}",
            f"Observado: {item.get('observed')}",
            "Notas: " + "; ".join(item.get("notes", [])),
            "",
        ]
else:
    report_txt.append("✅ Todos os casos passaram.")

(ROOT / "test_continuidade_0_5_1_v15_input_firewall_stt_sanity_report.txt").write_text("\n".join(report_txt), encoding="utf-8")
(ROOT / "test_continuidade_0_5_1_v15_input_firewall_stt_sanity_report.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

print("\n".join(report_txt[:8]))

if failed:
    raise SystemExit(1)
