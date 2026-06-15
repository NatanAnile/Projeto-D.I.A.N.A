# -*- coding: utf-8 -*-

# =========================
# 🧪 DIANA 0.5.7 — OPERATIONAL SKILL EXECUTION FIX
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
from runtime.intent_router import detect_capability
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
        print("\nTudo certo na 0.5.7.")


def main():
    report = TestReport()
    report.check("versão 0.5.7", PROJECT_VERSION == "0.5.7", PROJECT_VERSION)

    skill = ReadFileSkill()

    direct_phrases = [
        "le o arquivo aqui pra mim",
        "leia o arquivo aqui!.txt",
        "lê o primeiro arquivo pra mim",
        "ve o arquivo aqui! pra mim",
    ]

    for phrase in direct_phrases:
        report.check(f"detect_capability read_file: {phrase}", detect_capability(phrase) == "read_file", detect_capability(phrase))
        report.check(f"pedido_de_leitura_direta: {phrase}", skill.pedido_de_leitura_direta(phrase), phrase)
        response = skill.get_direct_response(phrase, force=True) or ""
        report.check(f"ReadFileSkill lê no mesmo turno: {phrase}", response.startswith("Li o arquivo") and "Daqui a pouco eu levanto" in response, response[:160])

    transform_phrases = [
        "resume o arquivo aqui!.txt",
        "analisa o arquivo aqui!.txt",
        "me explica esse arquivo aqui!.txt",
    ]

    for phrase in transform_phrases:
        report.check(f"pedido_de_transformacao: {phrase}", skill.pedido_de_transformacao(phrase), phrase)
        report.check(f"leitura direta bloqueada em transformação: {phrase}", not skill.pedido_de_leitura_direta(phrase), phrase)
        direct = skill.get_direct_response(phrase, force=True)
        report.check(f"transformação não retorna direct read: {phrase}", direct is None, str(direct)[:160])
        context = skill.get_context(phrase, force=True) or ""
        report.check(f"transformação gera contexto para LLM: {phrase}", "CAPACIDADE ATIVADA: ReadFileSkill" in context and "Arquivo em contexto: aqui!.txt" in context, context[:160])

    manager = SkillManager()
    turn_context = {"requested_capability": "read_file", "confidence": 1.0}
    manager_response = manager.verificar_resposta_direta(
        user_text="le o arquivo aqui pra mim",
        conversation=None,
        turn_context=turn_context,
    ) or ""
    report.check("SkillManager entrega leitura direta", manager_response.startswith("Li o arquivo") and "Daqui a pouco eu levanto" in manager_response, manager_response[:160])

    manager_context = manager.verificar_skills(
        user_text="resume o arquivo aqui!.txt",
        conversation=None,
        turn_context=turn_context,
    ) or ""
    report.check("SkillManager entrega contexto para resumo", "CAPACIDADE ATIVADA: ReadFileSkill" in manager_context and "Arquivo em contexto: aqui!.txt" in manager_context, manager_context[:160])

    with open("Diana.py", "r", encoding="utf-8") as f:
        line_count = sum(1 for _ in f)
    report.check("Diana.py abaixo de 1040 linhas", line_count < 1040, str(line_count))

    report.finish()


if __name__ == "__main__":
    main()
