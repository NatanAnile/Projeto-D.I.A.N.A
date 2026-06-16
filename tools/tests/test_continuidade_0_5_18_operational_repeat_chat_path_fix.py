# -*- coding: utf-8 -*-

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


class DummyLLM:
    def chat(self, prompt):
        return "ACAO: responder\nINDICE: 0\nMOTIVO: score\nRESPOSTA: Acho que ele desiste antes de tentar."


def item(user, message, role="CHAT_USER", risk="NORMAL", timestamp="00:00:00"):
    return {
        "timestamp": timestamp,
        "user": user,
        "role": role,
        "risk": risk,
        "message": message,
        "raw": f"[{timestamp}] {user}: {message}",
    }


def main():
    checks = []

    config = read("config.py")
    checks.append(("versao_0_5_18_ou_superior", 'PROJECT_VERSION = "0.5.18"' in config or 'PROJECT_VERSION = "0.5.19"' in config))

    # Router: perguntas equivalentes sobre chat precisam virar skill operacional.
    from runtime.intent_router import detect_capability

    chat_inputs = [
        "Consegue ver o chat?",
        "ve o chat pra mim",
        "vê o chat pra mim",
        "tem mensagem no chat?",
        "confere se tem mensagem no chat",
    ]
    for text in chat_inputs:
        checks.append(("router_read_chat_" + text, detect_capability(text) == "read_chat"))

    repeat_inputs = [
        "tenta de novo",
        "faz de novo",
        "repete",
        "mais uma vez",
    ]
    for text in repeat_inputs:
        checks.append(("router_repeat_" + text, detect_capability(text) == "repeat_last_operational_task"))

    # OutputFirewall: diretório completo nunca deve aparecer na fala final.
    from runtime.output_firewall import OutputFirewall

    firewall = OutputFirewall()
    leaked = r"Arquivo lido: C:\Users\natan\Projeto DIANA\Projeto D.I.A.N.A\data\chat\live_chat.txt."
    cleaned = firewall.clean(leaked)
    checks.append(("firewall_remove_windows_path", "C:\\Users" not in cleaned and "Projeto DIANA" not in cleaned))
    checks.append(("firewall_keep_filename", "live_chat.txt" in cleaned))

    # ReadChatSkill: fallback sem linhas só pode citar o nome do arquivo.
    from skills.read_chat_skill import ReadChatSkill

    read_chat = ReadChatSkill()
    checks.append(("read_chat_detecta_consegue_ver", read_chat.detectar_pedido("Consegue ver o chat?") is True))
    response = read_chat.get_direct_response(user_text="le o chat pra mim", force=True)
    checks.append(("read_chat_response_sem_path_absoluto", str(read_chat.chat_log_path) not in response))
    checks.append(("read_chat_response_com_nome_arquivo", read_chat.chat_log_path.name in response or "chat" in response.lower()))

    # SessionContext: armazena e recupera a última tarefa operacional para o replay.
    from brain.session_context import SessionContext

    ctx = SessionContext()
    original_last_task = ctx.current.get("last_operational_task")
    try:
        ctx.set_last_operational_task("read_chat", "le o chat pra mim", {"source": "test"})
        task = ctx.get_last_operational_task()
        checks.append(("session_last_task_capability", task and task.get("capability") == "read_chat"))
        checks.append(("session_last_task_user_text", task and task.get("user_text") == "le o chat pra mim"))
    finally:
        ctx.current["last_operational_task"] = original_last_task
        ctx.save_current_session()

    # Host Mode 0.5.17 precisa continuar intacto.
    from integrations.chat_host_mode import ChatHostMode

    host = ChatHostMode(DummyLLM())
    host.enabled = True
    host.mode = "read_response"
    host.last_tick_time = 0

    calls = {"process": 0, "idle": 0}
    host.get_new_messages = lambda: [item("stelyn", "Diana, ele vai continuar?", timestamp="1")]
    host.processar_mensagens = lambda messages: calls.__setitem__("process", calls["process"] + 1) or True
    host.processar_idle = lambda: calls.__setitem__("idle", calls["idle"] + 1) or True
    host.tick()

    checks.append(("read_response_tick_processa_mensagens", calls["process"] == 1))
    checks.append(("read_response_nao_usa_idle", calls["idle"] == 0))

    workflow = read(".github/workflows/tests.yml")
    checks.append(("workflow_teste_atual", "test_continuidade_0_5_19_file_context_personality_skills.py" in workflow))

    failed = [name for name, ok in checks if not ok]
    if failed:
        for name in failed:
            print("FAIL", name)
        raise AssertionError(f"Falhas: {failed}")

    print(f"OK — {len(checks)}/{len(checks)} checks passaram.")


if __name__ == "__main__":
    main()
