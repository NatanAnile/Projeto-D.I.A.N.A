import requests

from config import LLM_MODEL, LLM_TEMPERATURE, LLM_TOP_P


class OllamaLLM:

    RESPONSE_BUDGETS = {
        "short": 120,
        "medium": 220,
        "long": 420
    }

    QWEN3_MIN_BUDGETS = {
        "short": 120,
        "medium": 220,
        "long": 420
    }

    def __init__(self):

        self.url = "http://localhost:11434/api/generate"
        self.model = LLM_MODEL

        print(f"🧠 LLM carregado: {self.model}")

    # =========================
    # 🧠 CHAT COM OLLAMA
    # =========================

    def chat(self, prompt, response_budget="medium"):

        budget_key = str(response_budget)
        num_predict = self.RESPONSE_BUDGETS.get(budget_key, self.RESPONSE_BUDGETS["medium"])

        # Qwen3 pode gastar tokens tentando pensar antes de responder.
        # A resposta final continua sendo cortada depois pelo ResponseCleaner,
        # então aqui deixamos folga para evitar saída vazia.
        if self.model.startswith("qwen3"):
            num_predict = max(num_predict, self.QWEN3_MIN_BUDGETS.get(budget_key, 320))

        temperature = 0.85 if self.model.startswith("qwen3") else LLM_TEMPERATURE
        top_p = 0.9 if self.model.startswith("qwen3") else LLM_TOP_P

        return self._generate(
            prompt=prompt,
            temperature=temperature,
            top_p=top_p,
            num_predict=num_predict,
            num_ctx=3072,
            json_mode=False
        )

    # =========================
    # 🧠 ANÁLISE ESTRUTURADA
    # =========================

    def chat_structured(self, prompt, num_predict=520):

        return self._generate(
            prompt=prompt,
            temperature=1.1,
            top_p=0.6,
            num_predict=num_predict,
            num_ctx=4096,
            json_mode=True
        )

    # =========================
    # 🔌 GERAÇÃO BASE
    # =========================

    def _generate(self, prompt, temperature, top_p, num_predict, num_ctx, json_mode=False):

        payload = self._montar_payload(
            prompt=prompt,
            temperature=temperature,
            top_p=top_p,
            num_predict=num_predict,
            num_ctx=num_ctx,
            json_mode=json_mode
        )

        try:

            response = requests.post(
                self.url,
                json=payload,
                timeout=180
            )

            data = response.json()

            if "response" not in data:
                print("Resposta inesperada do Ollama:", data)
                return ""

            raw_response = data.get("response", "")
            cleaned_response = self.limpar_resposta(raw_response)

            # Alguns Qwen3 pequenos ignoram /no_think e gastam a saída inteira em <think>.
            # Se isso acontecer em resposta normal, tenta uma segunda chamada mais direta.
            if not cleaned_response and self.model.startswith("qwen3") and not json_mode:

                retry_prompt = (
                    "/no_think\n"
                    "Responda somente a resposta final em português do Brasil.\n"
                    "Não use <think>, raciocínio, análise interna, listas de passos ou explicação do processo.\n"
                    "Seja curto e direto.\n\n"
                    + prompt
                )

                retry_payload = self._montar_payload(
                    prompt=retry_prompt,
                    temperature=0.85,
                    top_p=0.85,
                    num_predict=max(num_predict, 360),
                    num_ctx=num_ctx,
                    json_mode=False
                )

                retry_response = requests.post(
                    self.url,
                    json=retry_payload,
                    timeout=180
                )

                retry_data = retry_response.json()
                cleaned_response = self.limpar_resposta(retry_data.get("response", ""))

                if not cleaned_response:
                    print("⚠️ Qwen3 devolveu apenas raciocínio interno mesmo após retry.")

            return cleaned_response

        except Exception as e:

            print("Erro no Ollama:", e)
            return ""

    # =========================
    # 📦 PAYLOAD
    # =========================

    def _montar_payload(self, prompt, temperature, top_p, num_predict, num_ctx, json_mode=False):

        prompt_final = prompt

        if self.model.startswith("qwen3"):
            prompt_final = (
                "/no_think\n"
                "Modo direto: responda apenas a resposta final. Não escreva raciocínio interno.\n"
                + prompt_final
            )

        payload = {
            "model": self.model,
            "prompt": prompt_final,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
                "num_predict": num_predict,
                "num_ctx": num_ctx
            }
        }

        if json_mode:
            payload["format"] = "json"

        return payload

    # =========================
    # 🧼 LIMPEZA DE RESPOSTA
    # =========================

    def limpar_resposta(self, text):

        if not text:
            return ""

        text = str(text)

        # Remove blocos completos de thinking. Se sobrar resposta final, usa ela.
        if "<think>" in text.lower() and "</think>" in text.lower():
            text = self.remover_blocos_thinking(text)

        # Remove tags soltas caso o modelo tenha cuspido tags abertas/fechadas isoladas.
        text = text.replace("<think>", "")
        text = text.replace("</think>", "")
        text = text.replace("<thinking>", "")
        text = text.replace("</thinking>", "")

        return text.strip()

    def remover_blocos_thinking(self, text):

        lower = text.lower()
        resultado = text

        while "<think>" in lower and "</think>" in lower:

            inicio = lower.find("<think>")
            fim = lower.find("</think>", inicio) + len("</think>")

            resultado = resultado[:inicio] + resultado[fim:]
            lower = resultado.lower()

        return resultado.strip()
