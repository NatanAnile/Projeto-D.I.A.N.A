# -*- coding: utf-8 -*-

# =========================
# 🧪 DIANA 0.5.10 — REPO HYGIENE / CI TEST FIX
# =========================

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from config import PROJECT_VERSION
from runtime.input_firewall import InputFirewall
from runtime.intent_router import detect_capability
from brain.dialogue_act_gate import DialogueActGate
from skills.read_file_skill import ReadFileSkill


class TestReport:
    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = []

    def check(self, name, condition, detail=""):
        self.total += 1
        if condition:
            self.passed += 1
            print(f"✅ {name}")
        else:
            self.failed.append((name, detail))
            print(f"❌ {name} :: {detail}")

    def finish(self):
        print("\n" + "=" * 60)
        print(f"Total: {self.total}")
        print(f"Passou: {self.passed}")
        print(f"Falhou: {len(self.failed)}")
        if self.failed:
            print("\nFalhas:")
            for name, detail in self.failed:
                print(f"- {name}: {detail}")
            raise SystemExit(1)
        print("\nTudo certo na 0.5.10.")


def main():
    report = TestReport()

    report.check("versão 0.5.10", PROJECT_VERSION == "0.5.10", PROJECT_VERSION)

    firewall = InputFirewall()
    packet = firewall.analyze("e ai diana")
    report.check(
        "micro_ping usa LLM com memória/retrieval desligados",
        packet.quality == "MICRO" and packet.intent_hint == "micro_ping" and packet.allow_llm is True and packet.allow_memory is False and packet.allow_retrieval is False,
        f"quality={packet.quality} intent={packet.intent_hint} llm={packet.allow_llm} mem={packet.allow_memory} retrieval={packet.allow_retrieval}",
    )

    gate = DialogueActGate()
    result = gate.analyze(packet.text, turn_context=packet.to_turn_context())
    report.check(
        "DialogueAct micro_ping não usa frase pronta",
        result.act == "micro_ping" and result.direct_response == "" and "LLM" in result.reason,
        f"act={result.act} direct={result.direct_response!r} reason={result.reason}",
    )

    prompt_source = (PROJECT_ROOT / "brain" / "prompt_builder.py").read_text(encoding="utf-8")
    report.check(
        "PromptBuilder tem task curta de persona para micro_ping",
        "dialogue_act == \"micro_ping\"" in prompt_source and "backchannel" in prompt_source and "sem frase de boas-vindas" in prompt_source,
        "task micro_ping não encontrada",
    )

    skill_system_source = (PROJECT_ROOT / "skills" / "skill_system.py").read_text(encoding="utf-8")
    report.check(
        "SkillManager não bloqueia CommentSkill em micro_ping/diana_self_query",
        'dialogue_act in {"micro_ping", "diana_self_query"}' not in skill_system_source,
        "guarda indevida encontrada",
    )

    response_bank_source = (PROJECT_ROOT / "personality" / "dialogue_response_bank.py").read_text(encoding="utf-8")
    report.check("micro_ping removido do banco de respostas", '"micro_ping"' not in response_bank_source, "micro_ping ainda existe no banco")

    report.check("detect_capability mantém read_file typo", detect_capability("ve oa rquivo aqui pra mim") == "read_file", detect_capability("ve oa rquivo aqui pra mim"))
    report.check("detect_capability mantém follow-up ele", detect_capability("Resume ele agora") == "read_file", detect_capability("Resume ele agora"))

    read_file = ReadFileSkill()
    direct = read_file.get_direct_response("ve oa rquivo aqui pra mim", force=True) or ""
    report.check(
        "ReadFile typo lê no mesmo turno",
        direct.startswith("Li o arquivo aqui!.txt:") and "Daqui a pouco eu levanto" in direct and len(direct) > 500,
        direct[:220],
    )

    context = read_file.get_context("Resume ele agora", force=True) or ""
    report.check(
        "ReadFile follow-up usa último arquivo",
        "CAPACIDADE ATIVADA: ReadFileSkill" in context and "Arquivo em contexto: aqui!.txt" in context,
        context[:220],
    )

    root_changelogs = list(PROJECT_ROOT.glob("CHANGELOG_*.txt"))
    logs_changelogs = list((PROJECT_ROOT / "Logs").glob("CHANGELOG_*.txt"))
    report.check("changelogs fora da raiz", not root_changelogs and bool(logs_changelogs), f"root={root_changelogs} logs={len(logs_changelogs)}")

    root_tests = list(PROJECT_ROOT.glob("test_continuidade_*.py"))
    tools_tests = list((PROJECT_ROOT / "tools" / "tests").glob("test_continuidade_*.py"))
    report.check("testes fora da raiz", not root_tests and bool(tools_tests), f"root={root_tests} tools={len(tools_tests)}")

    report.finish()


if __name__ == "__main__":
    main()
