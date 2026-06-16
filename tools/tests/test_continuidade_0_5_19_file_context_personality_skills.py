# -*- coding: utf-8 -*-

# =========================
# ✅ TESTE 0.5.19 — FILE CONTEXT + PERSONALITY SKILLS
# =========================

import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import PROJECT_VERSION
from runtime.intent_router import detect_capability
from runtime.input_firewall import InputFirewall
from skills.read_file_skill import ReadFileSkill
from skills.comment_skill import CommentSkill
from utils.response_cleaner import ResponseCleaner


checks = []


def check(name, condition):
    checks.append((name, bool(condition)))


# Versão
check("versao_0_5_19", PROJECT_VERSION == "0.5.19")

# IntentRouter: typos, listagem, escolha e follow-up de arquivo
intent_cases = {
    "resume o arrtigo cientifico pra mim": "read_file",
    "resume o arquivo do artigo cientifico pra mim": "read_file",
    "mas e arquivos? quais tem?": "read_file",
    "ecolhe um arquivo pra ler, criatura!": "read_file",
    "me fala uma rquivo que você tem na pasta read_files": "read_file",
    "Agora me diga o que você entendeu desse arquivo": "read_file",
}

for text, expected in intent_cases.items():
    check("intent_" + text[:30], detect_capability(text) == expected)

# InputFirewall: typo de arquivo vira hint operacional
firewall = InputFirewall()
packet = firewall.analyze("me fala uma rquivo que você tem na pasta read_files")
check("firewall_corrige_rquivo", " arquivo " in (" " + packet.text + " "))
check("firewall_hint_read_file", packet.intent_hint == "read_file")

packet2 = firewall.analyze("ecolhe um arquivo pra ler, criatura!")
check("firewall_corrige_ecolhe", "escolhe" in packet2.text)
check("firewall_hint_ecolhe_read_file", packet2.intent_hint == "read_file")

# ReadFileSkill: listagem real, escolha real e follow-up do último arquivo
read_file = ReadFileSkill()
lista = read_file.get_direct_response("mas e arquivos? quais tem?", force=True)
check("read_file_lista_reais", "Arquivos disponíveis" in lista and "piada.txt" in lista)
check("read_file_lista_nao_inventa", "Diário do Desespero" not in lista and "Notas Intrusivas" not in lista)

escolha = read_file.get_direct_response("ecolhe um arquivo pra ler, criatura!", force=True)
check("read_file_escolhe_e_le", escolha.startswith("Li o arquivo ") and ".txt" in escolha)
check("read_file_escolhe_nao_inventa", "Notas Intrusivas" not in escolha and "Diário do Desespero" not in escolha)

piada = read_file.get_direct_response("le oa rquivo piada", force=True)
check("read_file_piada", piada.startswith("Li o arquivo piada.txt:"))

contexto = read_file.get_context("Agora me diga o que você entendeu desse arquivo", force=True)
check("read_file_followup_usa_ultimo", contexto is not None and "Arquivo em contexto: piada.txt" in contexto)

# Cleaner: não mutila extensão .txt em modo operacional
cleaner = ResponseCleaner()
limpo = cleaner.clean(
    "Ainda não encontrei mensagens recentes do chat. Arquivo lido: live_chat.txt.",
    user_text="ve se tem mensagem no chat",
    capability="read_chat"
)
check("cleaner_preserva_txt", "live_chat.txt" in limpo)
check("cleaner_nao_live_chat_sem_extensao", "live_chat." not in limpo.replace("live_chat.txt.", ""))

# CommentSkill: carrega skill_actions.json, log correto e sem entrar em operacional ambíguo
comment = CommentSkill()
check("comment_actions_json_amplo", len(comment.all_actions) >= 10 and "improvisar_caos" in comment.all_actions)

buf = io.StringIO()
with redirect_stdout(buf):
    comment_context = comment.get_context(
        "coisa que voce ta precisando!",
        turn_context={
            "requested_capability": "none",
            "confidence": 1.0,
            "source": "OWNER",
            "personality_explicit": True,
            "personality_action": "improvisar_caos"
        }
    )
log = buf.getvalue()
check("comment_log_correto", "Skill de personalidade executada ->" in log and "CommentSkill ->" not in log)
check("comment_context_sem_nome_errado", comment_context is not None and "Ação de personalidade executada:" in comment_context)
check(
    "comment_nao_engole_operacional_ambiguo",
    comment.get_context(
        "resume o arrtigo cientifico pra mim",
        turn_context={"requested_capability": "none", "confidence": 0.0, "source": "OWNER"}
    ) is None
)

# Skills obsoletas removidas
check("game_context_skill_removido", not (ROOT / "skills" / "game_context_skill.py").exists())
check("style_skill_removido", not (ROOT / "skills" / "style_skill.py").exists())

failed = [name for name, ok in checks if not ok]

if failed:
    print("FALHOU:")
    for name in failed:
        print("-", name)
    raise SystemExit(1)

print(f"OK — {len(checks)}/{len(checks)} checks passaram.")
