# -*- coding: utf-8 -*-

# =========================
# 🧠 RESUMIDOR EPISÓDICO AUXILIAR
# =========================

import json
import threading
from pathlib import Path

from config import (
    SESSION_SUMMARIZER_ENABLED,
    SESSION_SUMMARIZER_TRIGGER_TURNS,
    SESSION_SUMMARIZER_BATCH_TURNS,
    SESSION_SUMMARIZER_MAX_TOKENS,
    SESSION_SUMMARIZER_STATE_PATH,
    SESSION_SUMMARIZER_TEXT_PATH
)
from llm.auxiliary_ollama_llm import AuxiliaryOllamaLLM


class SessionSummarizer:

    def __init__(self, enabled=None, llm=None):
        self.enabled = SESSION_SUMMARIZER_ENABLED if enabled is None else bool(enabled)
        self.llm = llm or AuxiliaryOllamaLLM(enabled=self.enabled)
        self.state_path = Path(SESSION_SUMMARIZER_STATE_PATH)
        self.text_path = Path(SESSION_SUMMARIZER_TEXT_PATH)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.text_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self.worker = None
        self.state = self._load_state()
        self._write_readable_summary()

    def _default_state(self):
        return {
            "summary": "",
            "pending_turns": [],
            "summarized_turns": 0
        }

    def _load_state(self):
        if not self.state_path.exists():
            state = self._default_state()
            self._save_state(state)
            return state

        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                base = self._default_state()
                base.update(data)
                return base
        except Exception:
            pass

        state = self._default_state()
        self._save_state(state)
        return state

    def _save_state(self, state=None):
        data = state if state is not None else self.state
        self.state_path.write_text(json.dumps(data, ensure_ascii=False, indent=4), encoding="utf-8")

    def record_turn(self, user_text, assistant_text, source_role="OWNER", source_name="Natan"):
        if not self.enabled:
            return

        with self.lock:
            self.state["pending_turns"].append({
                "source_role": str(source_role),
                "source_name": str(source_name),
                "user": str(user_text),
                "assistant": str(assistant_text)
            })
            self._save_state()

            should_run = len(self.state["pending_turns"]) >= SESSION_SUMMARIZER_TRIGGER_TURNS
            worker_running = self.worker is not None and self.worker.is_alive()

            if should_run and not worker_running:
                self.worker = threading.Thread(target=self._summarize_batch, daemon=True)
                self.worker.start()

    def _summarize_batch(self):
        with self.lock:
            batch = self.state["pending_turns"][:SESSION_SUMMARIZER_BATCH_TURNS]
            previous_summary = str(self.state.get("summary", "")).strip()

        if not batch:
            return

        turns_text = []
        for turn in batch:
            turns_text.append(
                f"Fonte: {turn['source_role']} | Nome: {turn['source_name']}\n"
                f"{turn['source_name']}: {turn['user']}\n"
                f"Diana: {turn['assistant']}"
            )

        prompt = f"""
Você é um resumidor de memória de curto prazo.
Resuma somente fatos e contexto realmente presentes. Não invente.
Não transforme exemplos, piadas ou hipóteses em fatos pessoais.
Preserve correções feitas pelo Neitan, tópicos ativos, decisões e referências necessárias para continuidade.
Descarte floreios e repetições.

Resumo anterior:
{previous_summary or '(vazio)'}

Novos turnos reais:
{chr(10).join(turns_text)}

Retorne APENAS JSON:
{{
  "summary": "resumo episódico atualizado em português do Brasil"
}}
""".strip()

        data = self.llm.generate_json(prompt, temperature=0.0, num_predict=SESSION_SUMMARIZER_MAX_TOKENS)
        new_summary = str((data or {}).get("summary", "")).strip()

        if not new_summary:
            print("⚠️ Resumidor auxiliar não produziu resumo válido.")
            return

        with self.lock:
            current_pending = self.state["pending_turns"]
            self.state["pending_turns"] = current_pending[len(batch):]
            self.state["summary"] = new_summary
            self.state["summarized_turns"] = int(self.state.get("summarized_turns", 0)) + len(batch)
            self._save_state()
            self._write_readable_summary()

        print(f"🧠 Resumo episódico atualizado: {len(batch)} turno(s) compactado(s).")

    def get_summary(self):
        with self.lock:
            return str(self.state.get("summary", "")).strip()

    def get_prompt_context(self):
        summary = self.get_summary()
        if not summary:
            return ""
        return (
            "# RESUMO EPISÓDICO GERADO — MEMÓRIA COMPACTA\n"
            "Este resumo veio apenas de turnos reais anteriores. Use para continuidade distante.\n"
            "As últimas interações completas têm prioridade quando houver conflito.\n"
            "Não trate ausências no resumo como fatos.\n\n"
            + summary
        )

    def _write_readable_summary(self):
        summary = str(self.state.get("summary", "")).strip()
        pending = len(self.state.get("pending_turns", []))
        summarized = int(self.state.get("summarized_turns", 0))
        text = (
            "# RESUMO EPISÓDICO AUXILIAR — DIANA 0.4\n\n"
            f"Turnos resumidos: {summarized}\n"
            f"Turnos aguardando resumo: {pending}\n\n"
            "## RESUMO\n"
            + (summary or "Nenhum resumo gerado ainda.")
            + "\n"
        )
        self.text_path.write_text(text, encoding="utf-8")
