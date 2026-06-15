# -*- coding: utf-8 -*-

# =========================
# 🧪 DIANA 0.5.8 — READFILE FOLLOWUP FUZZY FIX
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
from runtime.intent_router import detect_capability, normalize_text
from skills.read_file_skill import ReadFileSkill
from skills.skill_system import SkillManager


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
        print("\nTudo certo na 0.5.8.")


def main():
    report = TestReport()

    report.check("versão 0.5.8", PROJECT_VERSION == "0.5.8", PROJECT_VERSION)

    firewall = InputFirewall()

    packet = firewall.analyze("ve oa rquivo aqui pra mim")
    report.check(
        "InputFirewall corrige oa rquivo",
        packet.text == "ve o arquivo aqui pra mim" and packet.changed and packet.intent_hint == "read_file",
        f"text={packet.text} changed={packet.changed} intent={packet.intent_hint}",
    )

    packet = firewall.analyze("resume oa rquivo aqui")
    report.check(
        "InputFirewall corrige resumo com oa rquivo",
        packet.text == "resume o arquivo aqui" and packet.changed and packet.intent_hint == "read_file",
        f"text={packet.text} changed={packet.changed} intent={packet.intent_hint}",
    )

    report.check("IntentRouter normaliza typo de arquivo", normalize_text("ve oa rquivo aqui pra mim") == "ve o arquivo aqui pra mim", normalize_text("ve oa rquivo aqui pra mim"))
    report.check("detect_capability typo read_file", detect_capability("ve oa rquivo aqui pra mim") == "read_file", detect_capability("ve oa rquivo aqui pra mim"))
    report.check("detect_capability resumo typo read_file", detect_capability("resume oa rquivo aqui") == "read_file", detect_capability("resume oa rquivo aqui"))
    report.check("detect_capability follow-up ele read_file", detect_capability("Resume ele agora") == "read_file", detect_capability("Resume ele agora"))

    skill = ReadFileSkill()

    report.check("ReadFileSkill detecta pedido com typo", skill.detectar_pedido("ve oa rquivo aqui pra mim"), "detectar_pedido=False")
    report.check("ReadFileSkill leitura direta com typo", skill.pedido_de_leitura_direta("ve oa rquivo aqui pra mim"), "pedido_de_leitura_direta=False")

    direct = skill.get_direct_response("ve oa rquivo aqui pra mim", force=True) or ""
    report.check(
        "ReadFileSkill lê arquivo com typo no mesmo turno",
        direct.startswith("Li o arquivo aqui!.txt:") and "Daqui a pouco eu levanto" in direct and len(direct) > 500,
        direct[:200],
    )

    report.check("ReadFileSkill registra último arquivo", skill.last_file_name == "aqui!.txt" and bool(skill.last_file_content), str(skill.last_file_name))
    report.check("ReadFileSkill reconhece Resume ele agora", skill.detectar_referencia_anterior("Resume ele agora"), "referência anterior não detectada")
    report.check("Resume ele agora é transformação", skill.pedido_de_transformacao("Resume ele agora"), "pedido_de_transformacao=False")

    direct_summary = skill.get_direct_response("Resume ele agora", force=True)
    report.check("Resumo de ele não vira resposta direta", direct_summary is None, str(direct_summary)[:200])

    context_summary = skill.get_context("Resume ele agora", force=True) or ""
    report.check(
        "Resumo de ele usa arquivo anterior como contexto",
        "CAPACIDADE ATIVADA: ReadFileSkill" in context_summary and "Arquivo em contexto: aqui!.txt" in context_summary and "Daqui a pouco eu levanto" in context_summary,
        context_summary[:220],
    )

    context_typo = skill.get_context("resume oa rquivo aqui", force=True) or ""
    report.check(
        "Resumo com typo carrega arquivo correto",
        "CAPACIDADE ATIVADA: ReadFileSkill" in context_typo and "Arquivo em contexto: aqui!.txt" in context_typo,
        context_typo[:220],
    )

    manager = SkillManager()
    turn_context = {"requested_capability": "read_file", "confidence": 1.0}

    manager_direct = manager.verificar_resposta_direta(
        user_text="ve oa rquivo aqui pra mim",
        conversation=None,
        turn_context=turn_context,
    ) or ""
    report.check(
        "SkillManager entrega leitura direta com typo",
        manager_direct.startswith("Li o arquivo aqui!.txt:") and "Daqui a pouco eu levanto" in manager_direct and len(manager_direct) > 500,
        manager_direct[:220],
    )

    manager_summary_direct = manager.verificar_resposta_direta(
        user_text="Resume ele agora",
        conversation=None,
        turn_context=turn_context,
    )
    report.check("SkillManager não responde resumo anterior direto", manager_summary_direct is None, str(manager_summary_direct)[:220])

    manager_context = manager.verificar_skills(
        user_text="Resume ele agora",
        conversation=None,
        turn_context=turn_context,
    ) or ""
    report.check(
        "SkillManager entrega contexto do arquivo anterior",
        "CAPACIDADE ATIVADA: ReadFileSkill" in manager_context and "Arquivo em contexto: aqui!.txt" in manager_context,
        manager_context[:220],
    )

    with open("Diana.py", "r", encoding="utf-8") as f:
        diana_source = f.read()

    report.check(
        "Diana bypassa ResponseCleaner em leitura direta de arquivo",
        'startswith("Li o arquivo ")' in diana_source and 'capability == "read_file"' in diana_source,
        "bypass não encontrado em Diana.py",
    )

    line_count = len(diana_source.splitlines())
    report.check("Diana.py abaixo de 1045 linhas", line_count < 1045, str(line_count))

    report.finish()


if __name__ == "__main__":
    main()
