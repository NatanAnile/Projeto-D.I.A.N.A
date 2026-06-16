# -*- coding: utf-8 -*-

from pathlib import Path
import sys
import time

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
    checks.append(("versao_0_5_17", 'PROJECT_VERSION = "0.5.17"' in config))

    from integrations.chat_host_mode import ChatHostMode

    # read_response agora processa mensagens novas automaticamente no tick.
    host = ChatHostMode(DummyLLM())
    host.enabled = True
    host.mode = "read_response"
    host.last_tick_time = 0

    calls = {"process": 0, "idle": 0}

    def fake_get_new_messages():
        return [item("stelyn", "Diana, ele vai continuar?", timestamp="1")]

    def fake_process(messages):
        calls["process"] += 1
        return True

    def fake_idle():
        calls["idle"] += 1
        return True

    host.get_new_messages = fake_get_new_messages
    host.processar_mensagens = fake_process
    host.processar_idle = fake_idle
    host.tick()

    checks.append(("read_response_tick_processa_mensagens", calls["process"] == 1))
    checks.append(("read_response_nao_usa_idle", calls["idle"] == 0))

    # autonomous continua processando idle quando não há mensagens.
    host2 = ChatHostMode(DummyLLM())
    host2.enabled = True
    host2.mode = "autonomous"
    host2.last_tick_time = 0

    calls2 = {"process": 0, "idle": 0}
    host2.get_new_messages = lambda: []
    host2.processar_mensagens = lambda messages: calls2.__setitem__("process", calls2["process"] + 1) or False
    host2.processar_idle = lambda: calls2.__setitem__("idle", calls2["idle"] + 1) or True
    host2.tick()

    checks.append(("autonomous_usa_idle_sem_mensagens", calls2["idle"] == 1))

    # Score/contexto da 0.5.16 preservado.
    host3 = ChatHostMode(DummyLLM())
    messages = [
        item("isaac", "O técnico vai continuar mesmo?", timestamp="1"),
        item("stelyn", "Ele vai continuar.", timestamp="2"),
    ]
    candidates = host3.filtrar_candidatas(messages)
    checks.append(("host_responde_contextual", any(c["user"] == "stelyn" and c["score"] >= 6 for c in candidates)))

    formatted = host3.formatar_resposta_com_leitura(item("stelyn", "Ele vai continuar."), "Acho que ele desiste antes.")
    checks.append(("host_formato_usuario_mensagem_pensamento", formatted.startswith("stelyn: Ele vai continuar. — ")))

    # README/workflow atualizados.
    workflow = read(".github/workflows/tests.yml")
    checks.append(("workflow_teste_atual", "test_continuidade_0_5_17_hostmode_read_response_auto.py" in workflow))

    failed = [name for name, ok in checks if not ok]
    if failed:
        for name in failed:
            print("FAIL", name)
        raise AssertionError(f"Falhas: {failed}")

    print(f"OK — {len(checks)}/{len(checks)} checks passaram.")


if __name__ == "__main__":
    main()
