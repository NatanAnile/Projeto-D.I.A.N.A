# -*- coding: utf-8 -*-

# =========================
# 🧩 OLLAMA AUXILIAR — CPU/OUTRA PORTA
# =========================

import json
import requests

from config import (
    AUXILIARY_LLM_ENABLED,
    AUXILIARY_LLM_URL,
    AUXILIARY_LLM_MODEL,
    AUXILIARY_LLM_KEEP_ALIVE,
    AUXILIARY_LLM_TIMEOUT,
    AUXILIARY_LLM_NUM_CTX
)


class AuxiliaryOllamaLLM:

    def __init__(self, enabled=None, url=None, model=None):
        self.enabled = AUXILIARY_LLM_ENABLED if enabled is None else bool(enabled)
        self.url = str(url or AUXILIARY_LLM_URL)
        self.model = str(model or AUXILIARY_LLM_MODEL)

    def generate(self, prompt, temperature=0.0, num_predict=400, json_mode=False):
        if not self.enabled:
            return ""

        payload = {
            "model": self.model,
            "prompt": str(prompt),
            "stream": False,
            "keep_alive": AUXILIARY_LLM_KEEP_ALIVE,
            "options": {
                "temperature": float(temperature),
                "top_p": 0.9,
                "num_predict": int(num_predict),
                "num_ctx": int(AUXILIARY_LLM_NUM_CTX)
            }
        }

        if json_mode:
            payload["format"] = "json"

        try:
            response = requests.post(self.url, json=payload, timeout=AUXILIARY_LLM_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            return str(data.get("response", "")).strip()
        except Exception as error:
            print(f"⚠️ Modelo auxiliar indisponível: {error}")
            return ""

    def generate_json(self, prompt, temperature=0.0, num_predict=400):
        raw = self.generate(prompt, temperature=temperature, num_predict=num_predict, json_mode=True)
        if not raw:
            return None

        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else None
        except Exception:
            return None
