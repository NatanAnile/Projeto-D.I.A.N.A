# -*- coding: utf-8 -*-

# =========================
# 🧠 DIANA BRAIN PROMPT BUILDER
# =========================

from brain.brain_loader import DianaBrain
from brain.context_retriever import ContextRetriever
from brain.query_planner import QueryPlanner
from brain.query_gate import QueryGate


class PromptBuilder:

    def __init__(self, *args, **kwargs):

        self.brain = kwargs.get("brain") or DianaBrain()
        self.mem0_memory = kwargs.get("mem0_memory")
        self.context_retriever = kwargs.get("context_retriever") or ContextRetriever(mem0_memory=self.mem0_memory)
        self.query_planner = kwargs.get("query_planner") or QueryPlanner()
        self.query_gate = kwargs.get("query_gate") or QueryGate()
        self.session_summarizer = kwargs.get("session_summarizer")
        self.last_retrieval = None
        self.last_query_plan = None

    def build(self, user_text, conv_history=None, extra_context=None, turn_context=None):

        turn_context = turn_context or {}

        source = str(turn_context.get("source", "OWNER")).upper().strip()
        source_name = str(turn_context.get("source_name", "Natan")).strip()
        dialogue_target = str(turn_context.get("dialogue_target", "OWNER")).upper().strip()
        capability = str(turn_context.get("requested_capability", "none")).strip()
        history_context = self._safe_history_context(conv_history)
        active_activity_context = str(turn_context.get("activity_context", "")).strip()
        active_activity_task = str(turn_context.get("activity_task", "")).strip()
        last_collection = getattr(self.context_retriever.knowledge, "last_collection", "")
        last_entry = getattr(self.context_retriever.knowledge, "last_entry", None) or {}

        if turn_context.get("allow_retrieval") is False:
            gate = {"should_query": False, "reason": "InputFirewall bloqueou retrieval para este turno"}
        else:
            gate = self.query_gate.decide(user_text, has_active_entry=bool(last_entry))

        if gate["should_query"]:
            query_plan = self.query_planner.plan(
                user_text=user_text,
                history_text=history_context,
                last_collection=last_collection,
                last_entry_name=str(last_entry.get("name", ""))
            )
            if not query_plan:
                query_plan = {"source": "knowledge", "collection": "", "operation": "search", "filters": {"contains": [], "category": ""}, "limit": None, "requires_local_source": False}
        else:
            query_plan = {"source": "none", "collection": "", "operation": "none", "filters": {"contains": [], "category": ""}, "limit": None, "requires_local_source": False}
        query_plan["should_query"] = gate["should_query"]
        query_plan["gate_reason"] = gate["reason"]
        self.last_query_plan = query_plan
        retrieved = self.context_retriever.retrieve(user_text, history_text=history_context, query_plan=query_plan)
        self.last_retrieval = retrieved
        task = self._derive_task(user_text, capability, retrieved)

        parts = []

        parts.append(
            "# POLÍTICA DE VERDADE — PRIORIDADE MÁXIMA\n"
            "Criatividade pode mudar a forma da fala, nunca os fatos.\n"
            "Não invente fatos pessoais, lembranças, nomes, termos técnicos, siglas, regras ou definições.\n"
            "Para fatos pessoais sobre Neitan, use somente FATOS PESSOAIS RECUPERADOS, MEMÓRIAS MEM0 RECUPERADAS e HISTÓRICO REAL DA SESSÃO.\n"
            "Para conhecimento técnico local, use o CONHECIMENTO RECUPERADO como fonte factual principal.\n"
            "Se uma informação pessoal não foi encontrada, diga claramente que não sabe e não dê palpite.\n"
            "Se uma informação técnica não foi encontrada e você não tiver certeza, admita a incerteza.\n"
            "Se Neitan disser que você inventou ou errou, reconheça e pare de chutar."
        )

        parts.append(self._build_source_status(retrieved))

        if query_plan and query_plan.get("should_query") and self.query_planner.enabled:
            parts.append(
                "# PLANO DE CONSULTA AUXILIAR — NÃO É RESPOSTA\n"
                "O plano abaixo apenas escolheu a fonte e a operação. Os fatos continuam vindo dos arquivos locais.\n"
                + str(query_plan)
            )

        if retrieved["owner_context"]:
            parts.append("# FATOS PESSOAIS RECUPERADOS\n" + retrieved["owner_context"])

        if retrieved.get("mem0_context"):
            parts.append("# MEMÓRIAS MEM0 RECUPERADAS\n" + retrieved["mem0_context"])

        if retrieved["knowledge_context"]:
            parts.append("# CONHECIMENTO RECUPERADO\n" + retrieved["knowledge_context"])

        if self.session_summarizer:
            episodic_context = self.session_summarizer.get_prompt_context()
            if episodic_context:
                parts.append(episodic_context)

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
                "Este histórico tem prioridade sobre exemplos de estilo.\n\n"
                + history_context
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

        if retrieved["style_context"]:
            parts.append("# ESTILO OPCIONAL RECUPERADO\n" + retrieved["style_context"])

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

        return self.last_retrieval or {}

    def get_last_query_plan(self):

        return self.last_query_plan

    def _build_source_status(self, retrieved):

        lines = ["# STATUS DAS FONTES"]

        if retrieved["personal_query"]:
            if retrieved["personal_status"] == "FOUND":
                values = "; ".join(f"{fact['path']}={fact['value']}" for fact in retrieved.get("owner_facts", []))
                lines.append(
                    "Pergunta pessoal detectada: fatos locais encontrados. "
                    "Use estes valores exatamente; não substitua e não dê outro palpite. " + values
                )
            elif retrieved.get("mem0_memories"):
                lines.append(
                    "Pergunta pessoal detectada: fatos locais não encontrados, mas o Mem0 trouxe memória(s). "
                    "Use o Mem0 somente se responder diretamente à pergunta. Se não responder, admita que não sabe."
                )
            else:
                lines.append(
                    "Pergunta pessoal detectada: INFORMAÇÃO NÃO ENCONTRADA. "
                    "A resposta obrigatória é admitir que não sabe. Não adivinhe, não improvise e não invente."
                )

        if retrieved["technical_query"] or retrieved.get("knowledge_source_required"):
            if retrieved["knowledge_status"] == "FOUND":
                collection = retrieved.get("knowledge_collection") or "geral"
                lines.append(f"Pergunta técnica detectada: consulta já resolvida na coleção {collection}. A entrada recuperada é obrigatória. Explique exatamente essa entrada; não peça nome, não troque de entrada e não acrescente fatos ausentes.")
            elif retrieved.get("knowledge_source_required"):
                lines.append(
                    "FONTE LOCAL OBRIGATÓRIA NÃO ENCONTRADA. "
                    "Diga que não encontrou essa informação na base. Não use conhecimento próprio e não invente."
                )
            else:
                lines.append(
                    "Pergunta técnica detectada: nenhuma fonte local relevante foi encontrada. "
                    "Só responda pelo conhecimento geral se tiver certeza; caso contrário, admita incerteza."
                )

        if len(lines) == 1:
            lines.append("Nenhuma consulta factual especial foi necessária.")

        return "\n".join(lines)

    def _safe_history_context(self, conv_history):

        if not conv_history:
            return ""

        try:
            return conv_history.get_context() or ""
        except Exception:
            return ""

    def _derive_task(self, user_text, capability, retrieved=None):

        text = str(user_text or "").strip()
        lower = text.lower()
        retrieved = retrieved or {}

        operation = retrieved.get("knowledge_operation", "")

        if operation == "correction":
            return "Reconhecer o erro apontado por Neitan sem discutir, sem defender a resposta anterior e sem inventar uma nova explicação."

        if operation == "topic_change":
            return "Confirmar brevemente a mudança de assunto sem puxar contexto antigo nem inventar uma nova pauta."

        if operation == "topic_setup":
            return "Acompanhar o assunto proposto sem consultar ou explicar uma entrada específica até que Neitan faça uma pergunta concreta."

        if operation == "feedback":
            return "Responder ao feedback de Neitan de forma curta, sem repetir a consulta anterior e sem inventar informação técnica."

        if retrieved.get("knowledge_status") == "FOUND":
            entries = retrieved.get("knowledge_entries", [])
            names = ", ".join(str(entry.get("name", "")).strip() for entry in entries if str(entry.get("name", "")).strip())
            operation = retrieved.get("knowledge_operation", "search")

            if operation == "count":
                return "Responder com a quantidade exata recuperada pela consulta estrutural."

            if entries:
                if operation in {"same", "reformulate"}:
                    return (
                        f"Reexplicar a mesma entrada já selecionada ({names}) obedecendo ao formato pedido agora. "
                        "Não realizar nova escolha e não acrescentar fatos ausentes na fonte."
                    )

                return (
                    f"A consulta já selecionou a entrada correta: {names}. "
                    "Explicar diretamente essa entrada usando somente os fatos explícitos do CONHECIMENTO RECUPERADO. "
                    "Não pedir o nome da técnica/item, não sugerir outra opção e não acrescentar efeitos, riscos, requisitos ou locais ausentes."
                )

        short_followups = [
            "qual", "qual?", "como assim", "como assim?", "por que", "por quê", "porque", "e aí", "e ai"
        ]

        if lower in short_followups:
            return (
                "Responder como continuação direta da fala imediatamente anterior no HISTÓRICO REAL DA SESSÃO. "
                "Se a Diana fez uma pergunta/piada antes, complete essa sequência em vez de perguntar 'qual o quê?'. "
                "Não trocar de assunto e não inventar contexto fora do histórico."
            )

        if retrieved.get("mem0_memories") and retrieved.get("personal_query"):
            return (
                "Responder à pergunta pessoal usando as MEMÓRIAS MEM0 RECUPERADAS somente se elas forem diretamente relevantes. "
                "Se a memória não responder, diga que ainda não sabe. Não invente preferência ou lembrança."
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
