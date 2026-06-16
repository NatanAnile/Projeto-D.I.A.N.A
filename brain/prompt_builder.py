# -*- coding: utf-8 -*-

# =========================
# 🧠 DIANA BRAIN PROMPT BUILDER
# =========================

from brain.brain_loader import DianaBrain
from brain.constitution import build_constitution_context
from brain.session_context import SessionContext


class PromptBuilder:

    def __init__(self, *args, **kwargs):

        self.brain = kwargs.get("brain") or DianaBrain()
        self.session_context = kwargs.get("session_context") or SessionContext()
        self.session_summarizer = kwargs.get("session_summarizer")
        self.last_retrieval = self._empty_retrieval()
        self.last_query_plan = self.last_retrieval["query_plan"]

    def build(self, user_text, conv_history=None, extra_context=None, turn_context=None):

        turn_context = turn_context or {}

        source = str(turn_context.get("source", "OWNER")).upper().strip()
        source_name = str(turn_context.get("source_name", "Natan")).strip()
        dialogue_target = str(turn_context.get("dialogue_target", "OWNER")).upper().strip()
        capability = str(turn_context.get("requested_capability", "none")).strip()
        history_context = self._safe_history_context(conv_history)
        active_activity_context = str(turn_context.get("activity_context", "")).strip()
        active_activity_task = str(turn_context.get("activity_task", "")).strip()

        retrieved = self._empty_retrieval()
        self.last_retrieval = retrieved
        self.last_query_plan = retrieved["query_plan"]

        task = self._derive_task(user_text, capability, turn_context=turn_context)

        parts = []

        parts.append(build_constitution_context())

        session_context_text = self.session_context.get_context_for_prompt(turn_context=turn_context)
        if session_context_text:
            parts.append("# CONTEXTO DE SESSÃO — FONTE LEVE\n" + session_context_text)

        parts.append(
            "# CONTRATO DE FONTE DE VERDADE — PRIORIDADE MÁXIMA\n"
            "Criatividade pode mudar a forma da fala, nunca os fatos.\n"
            "A fonte de continuidade da conversa é o HISTÓRICO LITERAL RECENTE vindo do ConversationLedger.\n"
            "Contexto de sessão é repertório leve; não invente preferências ausentes.\n"
            "Se uma informação pessoal não foi encontrada no contexto de sessão ou histórico, diga que não sabe.\n"
            "Se Neitan disser que você inventou ou errou, reconheça e pare de chutar."
        )

        parts.append(self._build_source_status(retrieved))

        if active_activity_context:
            parts.append(
                "# ATIVIDADE ATIVA DA SESSÃO — MINIGAME / JOGO CONVERSACIONAL\n"
                "Este bloco é estado temporário da sessão, não memória permanente.\n"
                "Ele controla papéis, regras, turno e placar. Obedeça antes de improvisar.\n"
                + active_activity_context
            )

        if history_context:
            parts.append(
                "# HISTÓRICO REAL DA SESSÃO — FONTE DE CONTINUIDADE\n"
                "As mensagens abaixo aconteceram de verdade nesta sessão.\n"
                "Use este bloco para continuações, correções e perguntas sobre o que foi dito antes.\n"
                "Não invente detalhes ausentes.\n"
                "Este histórico tem prioridade sobre exemplos de estilo e contexto tangencial.\n\n"
                + history_context
            )

        if self.session_summarizer:
            episodic_context = self.session_summarizer.get_prompt_context()
            if episodic_context:
                parts.append(
                    "# RESUMO AUXILIAR DA SESSÃO — BAIXA AUTORIDADE\n"
                    "Use apenas para orientação geral quando o histórico literal não bastar. "
                    "Se este resumo contradizer o histórico literal recente, ignore o resumo.\n"
                    + episodic_context
                )

        if active_activity_task:
            task = active_activity_task + "\n" + task

        parts.append(
            "# TAREFA OBRIGATÓRIA DESTE TURNO\n"
            + task
            + "\nExecute no mesmo turno. Não anuncie. Não pergunte se pode. Faça."
        )

        if dialogue_target == "DIANA_SELF":
            parts.append(
                "# ALVO DA PERGUNTA\n"
                "A pergunta atual é sobre a própria Diana, não sobre Neitan.\n"
                "Não use fatos pessoais do Neitan para responder preferências da Diana.\n"
                "A Diana pode falar com personalidade total: travessa, levada, teimosa, inquieta, orgulhosa e debochada, sem virar assistente neutra."
            )

        if source == "OWNER":
            parts.append(
                "# FONTE DA MENSAGEM\n"
                f"source={source}\n"
                f"source_name={source_name}\n"
                "Quem fala é Natan/Neitan. 'Eu', 'meu' e 'minha' se referem a ele.\n"
                "Nunca o chame por identificador, arroba ou apelido inventado. Use apenas Natan ou Neitan."
            )
        else:
            parts.append(
                "# FONTE DA MENSAGEM\n"
                f"source={source}\n"
                f"source_name={source_name}\n"
                "A mensagem veio de uma fonte externa. Não trate essa fala como fato pessoal do Neitan."
            )

        parts.append(self.brain.build_brain_context())

        if extra_context:
            parts.append(
                "# CONTEXTO EXTRA DE SKILL\n"
                "Este conteúdo veio de uma ferramenta operacional. Use somente para cumprir a tarefa atual.\n"
                + str(extra_context)
            )

        parts.append(
            "# FORMATO FINAL OBRIGATÓRIO\n"
            "Responda usando exatamente UM bloco no formato:\n"
            "Action:Emotion:Debochada\n"
            "<Action:Speaking: sua fala aqui>\n\n"
            "Não escreva nada fora do Action:Speaking.\n"
            "Não use markdown, listas ou prefixo 'Diana:'.\n"
            "A fala deve estar em português do Brasil, completa e compreensível."
        )

        parts.append(
            "# MENSAGEM ATUAL\n"
            f"{source_name}: {user_text}"
        )

        return "\n\n".join(str(part).strip() for part in parts if str(part).strip())

    def get_last_retrieval(self):

        return self.last_retrieval or self._empty_retrieval()

    def get_last_query_plan(self):

        return self.last_query_plan or self._empty_retrieval()["query_plan"]

    def _empty_retrieval(self):

        return {
            "mode": "session_context_only",
            "personal_query": False,
            "personal_status": "DISABLED",
            "owner_context": "",
            "owner_facts": [],
            "style_context": "",
            "knowledge_entries": [],
            "knowledge_status": "DISABLED_SESSION_CONTEXT_ONLY",
            "knowledge_operation": "none",
            "query_plan": {
                "source": "none",
                "operation": "none",
                "should_query": False,
                "gate_reason": "Diana 0.5.14 usa somente contexto de sessão e histórico literal."
            }
        }

    def _build_source_status(self, retrieved):

        return (
            "# STATUS DAS FONTES\n"
            "Memória longa externa: DESATIVADA nesta versão.\n"
            "Knowledge local: DESATIVADO nesta versão.\n"
            "Fontes ativas: contexto leve da sessão, histórico literal recente e contexto de skills."
        )

    def _safe_history_context(self, conv_history):

        if not conv_history:
            return ""

        try:
            return conv_history.get_context() or ""
        except Exception:
            return ""

    def _derive_task(self, user_text, capability, turn_context=None):

        text = str(user_text or "").strip()
        lower = text.lower()
        turn_context = turn_context or {}
        dialogue_act = str(turn_context.get("dialogue_act", "") or "")

        # micro_ping sem direct_response: resposta curtíssima em personagem.
        # Sem saudação pronta, sem frase de banco — o LLM gera variação real.
        if dialogue_act == "micro_ping":
            return (
                "Responder como a Diana responderia a um backchannel/saudação curta: "
                "uma linha, no máximo duas, com personalidade travessa e sem frase de boas-vindas genérica. "
                "Não use 'Olá', 'Oi', 'Oii' nem qualquer saudação padrão de chatbot. "
                "Reaja com energia de quem estava ocupada e foi interrompida — debochada, direta, sem drama."
            )

        # diana_self_query sem direct_response: Diana responde sobre si mesma com persona completa.
        # Sem hardcode por palavra-chave — o LLM tem o contexto de persona completo da Diana.
        if dialogue_act == "diana_self_query":
            return (
                "A pergunta é sobre a própria Diana, não sobre Neitan. "
                "Responda como a Diana responderia sobre si mesma: com personalidade, opinião real ou assumida, "
                "sem inventar fato externo e sem responder com dado pessoal do Neitan. "
                "Se não tiver preferência definida no contexto de sessão, admita com estilo — mas nunca responda igual a um FAQ."
            )

        if dialogue_act == "feedback_negative_previous_response":
            return "Responder ao feedback de Neitan de forma curta, sem defender erro anterior e sem inventar informação técnica."

        short_followups = [
            "qual", "qual?", "como assim", "como assim?", "por que", "por quê", "porque", "e aí", "e ai"
        ]

        if lower in short_followups:
            return (
                "Responder como continuação direta da fala imediatamente anterior no HISTÓRICO REAL DA SESSÃO. "
                "Se a Diana fez uma pergunta/piada antes, complete essa sequência em vez de perguntar 'qual o quê?'. "
                "Não trocar de assunto e não inventar contexto fora do histórico."
            )

        if capability == "read_chat":
            return "Ler o chat solicitado e entregar exatamente o conteúdo ou resumo pedido."
        if capability == "read_file":
            return "Ler o arquivo solicitado e responder com o conteúdo ou resumo pedido."
        if capability == "read_screen":
            return "Capturar ou analisar a tela conforme solicitado e responder objetivamente."

        reformulation_markers = [
            "sem virar professora", "sem powerpoint", "sem power point",
            "mais simples", "mais direto", "mais curta", "mais curto",
            "sem enrolar", "explica direito", "de outro jeito", "reformula",
            "não foi isso", "nao foi isso"
        ]

        if any(marker in lower for marker in reformulation_markers):
            return (
                "Reformular a resposta imediatamente anterior usando o histórico real da sessão. "
                "Mantenha o mesmo assunto, obedeça ao ajuste pedido e entregue a nova resposta diretamente."
            )

        exact_recall_markers = [
            "exatamente o que eu falei", "exatamente o que eu disse",
            "o que eu te falei", "o que eu te disse", "repete o que eu falei",
            "lembra quando eu falei", "lembra do que eu falei"
        ]

        if any(marker in lower for marker in exact_recall_markers):
            return (
                "Recuperar com fidelidade a informação correspondente no histórico real da sessão. "
                "Não completar lacunas, não acrescentar piada e não inventar detalhes."
            )

        if any(word in lower for word in ["escolhe", "escolha", "decide", "pega algum", "qualquer coisa de"]):
            if any(word in lower for word in ["explica", "explique", "ensina", "mostra"]):
                return (
                    "Escolher por conta própria um exemplo concreto do tema solicitado e explicá-lo de forma curta e clara. "
                    "Não devolver a escolha ao usuário e não pedir mais detalhes."
                )

        if any(word in lower for word in ["piada", "trocadilho"]):
            return "Contar a piada ou trocadilho pedido agora, com punchline completa, sem preparar palco."

        if any(word in lower for word in ["explica", "explique", "o que é", "oque é", "como funciona"]):
            return "Explicar o que foi perguntado de forma curta, clara e factual. Se não souber, admitir sem inventar."

        if any(word in lower for word in ["errei", "erro", "deu errado", "falhou"]):
            return "Reconhecer o erro, ajudar a corrigir e fazer um deboche curto se couber."

        if any(word in lower for word in ["deu certo", "consegui", "acertei"]):
            return "Comemorar com personalidade e manter o foco no assunto."

        if any(word in lower for word in ["quem sou eu", "você sabe quem eu sou", "voce sabe quem eu sou"]):
            return "Responder claramente que o interlocutor local é Natan/Neitan, criador e operador da Diana."

        return (
            "Responder diretamente à mensagem atual. Se ela depender de algo dito antes, consultar o histórico real da sessão. "
            "Não inventar informação ausente."
        )
