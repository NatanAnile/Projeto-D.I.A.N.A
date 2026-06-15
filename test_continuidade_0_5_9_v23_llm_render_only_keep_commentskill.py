# -*- coding: utf-8 -*-

# =========================
# 🧪 DIANA 0.5.9 — LLM RENDER ONLY / KEEP COMMENTSKILL
# =========================

import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if "mss" not in sys.modules:
    fake_mss = types.ModuleType("mss")
    fake_mss.mss = lambda *args, **kwargs: None
    sys.modules["mss"] = fake_mss

from config import PROJECT_VERSION
from runtime.input_firewall import InputFirewall
from runtime.intent_router import detect_capability
from brain.dialogue_act_gate import DialogueActGate
from brain.prompt_builder import PromptBuilder
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
        print("\nTudo certo na 0.5.9 keep CommentSkill.")


def main():
    report = TestReport()
    report.check("versão 0.5.9", PROJECT_VERSION == "0.5.9", PROJECT_VERSION)

    firewall = InputFirewall()
    packet = firewall.analyze("e ai diana")
    report.check(
        "micro_ping sai do firewall com LLM ligado e fontes desligadas",
        packet.quality == "MICRO" and packet.intent_hint == "micro_ping" and packet.allow_llm is True and packet.allow_memory is False and packet.allow_retrieval is False,
        f"quality={packet.quality} intent={packet.intent_hint} llm={packet.allow_llm} mem={packet.allow_memory} retrieval={packet.allow_retrieval}",
    )

    gate = DialogueActGate()
    result = gate.analyze(packet.text, turn_context=packet.to_turn_context())
    report.check(
        "DialogueAct micro_ping vai para LLM, sem frase pronta",
        result.act == "micro_ping" and result.direct_response == "" and "LLM" in result.reason,
        f"act={result.act} direct={result.direct_response!r} reason={result.reason}",
    )

    builder = PromptBuilder()
    task = builder._derive_task("e ai", "none", {}, turn_context={"dialogue_act": "micro_ping"})
    report.check(
        "PromptBuilder injeta task curta de persona para micro_ping",
        "backchannel" in task and "uma linha" in task and "sem frase" in task,
        task,
    )

    with open("skills/skill_system.py", "r", encoding="utf-8") as f:
        skill_system_source = f.read()
    report.check(
        "SkillManager NÃO bloqueia CommentSkill por micro_ping/diana_self_query",
        'dialogue_act in {"micro_ping", "diana_self_query"}' not in skill_system_source,
        "guarda indevida ainda existe",
    )

    with open("personality/dialogue_response_bank.py", "r", encoding="utf-8") as f:
        response_bank_source = f.read()
    report.check("micro_ping removido do banco de respostas", '"micro_ping"' not in response_bank_source, "micro_ping ainda existe no banco")

    self_query = gate.analyze("qual seu nome?", turn_context={})
    report.check(
        "diana_self_query também vai ao LLM sem hardcode",
        self_query.act == "diana_self_query" and self_query.direct_response == "",
        f"act={self_query.act} direct={self_query.direct_response!r}",
    )

    # Regressão 0.5.8: ReadFile fuzzy/follow-up continua funcionando.
    report.check("detect_capability mantém read_file typo", detect_capability("ve oa rquivo aqui pra mim") == "read_file", detect_capability("ve oa rquivo aqui pra mim"))
    report.check("detect_capability mantém follow-up ele", detect_capability("Resume ele agora") == "read_file", detect_capability("Resume ele agora"))

    read_file = ReadFileSkill()
    direct = read_file.get_direct_response("ve oa rquivo aqui pra mim", force=True) or ""
    report.check(
        "ReadFile typo ainda lê no mesmo turno",
        direct.startswith("Li o arquivo aqui!.txt:") and "Daqui a pouco eu levanto" in direct and len(direct) > 500,
        direct[:220],
    )

    context = read_file.get_context("Resume ele agora", force=True) or ""
    report.check(
        "ReadFile follow-up ainda usa último arquivo",
        "CAPACIDADE ATIVADA: ReadFileSkill" in context and "Arquivo em contexto: aqui!.txt" in context,
        context[:220],
    )

    report.finish()


if __name__ == "__main__":
    main()
