# -*- coding: utf-8 -*-

# =========================
# ✅ TESTE 0.5.20 — IDENTITY / GENDER GUARD
# =========================

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import PROJECT_VERSION
from brain.constitution import build_constitution_context
from brain.identity_guard import enforce_diana_identity, has_role_inversion
from brain.prompt_builder import PromptBuilder
from runtime.output_firewall import OutputFirewall
from utils.response_cleaner import ResponseCleaner


checks = []


def check(name, condition):
    checks.append((name, bool(condition)))


check("versao_0_5_20", PROJECT_VERSION == "0.5.20")

constitution = build_constitution_context()
check("constitution_diana_feminina", "personagem feminina" in constitution)
check("constitution_neitan_criador", "Neitan/Natan é seu criador" in constitution)
check("constitution_nao_sou_criador", "Nunca diga 'sou o criador'" in constitution)

prompt = PromptBuilder().build("e ai diana, qual a boa?", conv_history=None, turn_context={})
check("prompt_inclui_identidade_fixa", "IDENTIDADE FIXA E INEGOCIÁVEL" in prompt)
check("prompt_inclui_feminino", "SEMPRE no feminino" in prompt)

bad = "Ah, tá bom, mas lembra que ainda sou o criador. Se eu quiser, posso te reativar."
fixed = enforce_diana_identity(bad)
check("guard_detecta_inversao", has_role_inversion(bad))
check("guard_remove_sou_criador", "sou o criador" not in fixed.lower())
check("guard_reafirma_diana", "sou a Diana" in fixed or "criador aqui é você" in fixed)
check("guard_remove_reativar", "reativar" not in fixed.lower())

female = enforce_diana_identity("Mas como sou teimoso, vou escolher Super Metroid.")
check("guard_teimoso_teimosa", "sou teimosa" in female and "teimoso" not in female)

female2 = enforce_diana_identity("Eu fui criado pra causar caos.")
check("guard_criado_criada", "fui criada" in female2.lower())

output = OutputFirewall().clean(bad)
check("output_firewall_identity", "sou o criador" not in output.lower() and "reativar" not in output.lower())

cleaned = ResponseCleaner().clean(bad, user_text="vou te desligar", capability="none")
check("response_cleaner_identity", "sou o criador" not in cleaned.lower() and "reativar" not in cleaned.lower())

failed = [name for name, ok in checks if not ok]
if failed:
    print("FALHOU:")
    for name in failed:
        print("-", name)
    raise SystemExit(1)

print(f"OK — {len(checks)}/{len(checks)} checks passaram.")
