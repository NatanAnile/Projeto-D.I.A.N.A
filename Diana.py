# -*- coding: utf-8 -*-

# =========================
# 🧠 DIANA BRAIN — LOOP PRINCIPAL
# =========================

import os
import sys
import time
import queue
import threading
import warnings
import re
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

warnings.filterwarnings("ignore")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["PYTHONWARNINGS"] = "ignore"

import keyboard
import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav

from config import (
    LOAD_STT,
    TTS_ENABLED,
    PUSH_TO_TALK_KEY,
    PTT_START_TIMEOUT_SECONDS,
    PTT_MAX_RECORD_SECONDS,
    PTT_SILENCE_ABORT_SECONDS,
    OWNER_NAME,
    LOCAL_INPUT_SOURCE,
    LOCAL_INPUT_SOURCE_NAME,
    CONVERSATION_MAX_TURNS,
    ALLOW_LIVE_REFERENCES_WITHOUT_CONTEXT,
    PROJECT_VERSION,
    QUERY_PLANNER_ENABLED,
    SESSION_SUMMARIZER_ENABLED,
    STT_ENGINE,
    MEM0_AUTO_SAVE_INTERACTIONS,
    MEM0_AUTO_SAVE_SMART_FILTER,
    MEM0_AUTO_SAVE_MIN_CHARS
)

from llm.ollama_llm import OllamaLLM
from tts.tts_manager import TTSManager
from stt.whisper_stt import WhisperSTT
from stt.parakeet_stt import ParakeetSTT
from stt.silero_vad import SileroVAD

from brain.prompt_builder import PromptBuilder
from brain.action_parser import ActionParser
from brain.session_context import SessionContext
from brain.session_summarizer import SessionSummarizer
from brain.memory_mem0 import Mem0Memory
from brain.activity_context import ActivityContextProvider
from brain.dialogue_act_gate import DialogueActGate

from skills.skill_system import SkillManager
from integrations.streamerbot_chat import set_chat_chaos_mode, enviar_mensagem_chat
from integrations.chat_host_mode import ChatHostMode

from utils.response_cleaner import ResponseCleaner
from utils.text_cleaner import clean_for_tts

from runtime.input_firewall import InputFirewall


# =========================
# 🚀 INICIALIZAÇÃO
# =========================

llm = OllamaLLM()
tts = TTSManager()

if LOAD_STT:

    if STT_ENGINE.lower().strip() == "parakeet":
        stt = ParakeetSTT()
    else:
        stt = WhisperSTT()

    vad = SileroVAD()
else:
    stt = None
    vad = None
    print("🎙️ STT desativado para testes por texto")

session_context = SessionContext()
skill_manager = SkillManager()
response_cleaner = ResponseCleaner(
    allow_live_without_context=ALLOW_LIVE_REFERENCES_WITHOUT_CONTEXT
)

session_summarizer = SessionSummarizer()
mem0_memory = Mem0Memory()
prompt_builder = PromptBuilder(
    session_summarizer=session_summarizer,
    mem0_memory=mem0_memory
)
action_parser = ActionParser()
activity_context = ActivityContextProvider()
dialogue_act_gate = DialogueActGate()
input_firewall = InputFirewall()

print(f"🧠 Diana Brain carregado — versão {PROJECT_VERSION}")
print(f"🎤 STT selecionado: {STT_ENGINE}")
print(f"🗺️ Query Planner auxiliar: {'ATIVADO' if QUERY_PLANNER_ENABLED else 'DESATIVADO'}")
print(f"🧠 Resumidor auxiliar: {'ATIVADO' if SESSION_SUMMARIZER_ENABLED else 'DESATIVADO'}")
print(f"🧠 Mem0 auto-save: {'ATIVADO' if MEM0_AUTO_SAVE_INTERACTIONS else 'DESATIVADO'}")

# Estados runtime de módulos simples. Não alteram config.py; só valem até fechar a Diana.
tts_runtime_enabled = bool(TTS_ENABLED)
stt_runtime_enabled = bool(LOAD_STT)
mem0_autosave_runtime_enabled = bool(MEM0_AUTO_SAVE_INTERACTIONS)
last_prompt_text = ""
last_input_channel = "OWNER_TEXT"


# =========================
# 📝 HISTÓRICO DE CONVERSA
# =========================

class ConversationHistory:

    def __init__(self, max_turns=5):

        self.history = []
        self.max_turns = max_turns

    def add_turn(self, user_text, assistant_text, source_role="OWNER", source_name="Natan"):

        self.history.append({
            "user": user_text,
            "assistant": assistant_text,
            "source_role": source_role,
            "source_name": source_name
        })

        if len(self.history) > self.max_turns:
            self.history.pop(0)

    def get_context(self):

        if not self.history:
            return ""

        context_text = "# HISTÓRICO RECENTE — ÚLTIMAS INTERAÇÕES\n"

        for turn in self.history:
            source_role = turn.get("source_role", "OWNER")
            source_name = turn.get("source_name", "Natan")
            context_text += f"Fonte: {source_role} | Nome: {source_name}\n"
            context_text += f"{source_name}: {turn['user']}\n"
            context_text += f"Diana: {turn['assistant']}\n\n"

        return context_text.strip()

    def clear(self):

        self.history = []


# =========================
# ⌨️ INPUT DE TEXTO NÃO BLOQUEANTE
# =========================

text_input_queue = queue.Queue()
terminal_thread = None


def terminal_input_worker():

    print("⌨️ Modo texto pronto.")

    while True:

        try:
            text = input("Digite sua mensagem: ").strip()

            if text:
                print()
                print("─" * 60)
                print(f"🧑 Neitan: {text}")
                print("─" * 60)
                print()
                text_input_queue.put(text)

        except EOFError:
            break

        except KeyboardInterrupt:
            break


terminal_thread = threading.Thread(
    target=terminal_input_worker,
    daemon=True
)

terminal_thread.start()


# =========================
# 🎤 ÁUDIO / STT
# =========================

def should_process_audio():

    if not LOAD_STT:
        return False

    try:
        return keyboard.is_pressed(PUSH_TO_TALK_KEY)
    except Exception:
        return False


def record_audio(fs=16000):

    print("🎤 gravando...")

    chunks = []
    start_wait = time.monotonic()

    while not keyboard.is_pressed(PUSH_TO_TALK_KEY):
        if not text_input_queue.empty():
            print("⌨️ texto no terminal detectado; STT atual cancelado.")
            return np.array([]), fs

        if time.monotonic() - start_wait >= PTT_START_TIMEOUT_SECONDS:
            print("⏱️ PTT não estabilizou; encerrando busca de áudio.")
            return np.array([]), fs

        time.sleep(0.01)

    time.sleep(0.1)

    record_start = time.monotonic()
    last_audio_time = record_start
    interrupted_by_text = False

    while keyboard.is_pressed(PUSH_TO_TALK_KEY):

        if not text_input_queue.empty():
            print("⌨️ texto no terminal detectado; encerrando STT atual para processar texto.")
            interrupted_by_text = True
            break

        elapsed = time.monotonic() - record_start

        if elapsed >= PTT_MAX_RECORD_SECONDS:
            print("⏱️ limite de gravação STT atingido; encerrando áudio atual.")
            break

        if not chunks and elapsed >= PTT_SILENCE_ABORT_SECONDS:
            print("⚠️ nenhum áudio útil detectado; encerrando gravação STT.")
            break

        chunk = sd.rec(int(0.1 * fs), samplerate=fs, channels=1, dtype="float32")
        sd.wait()

        chunk = chunk.squeeze()

        if np.max(np.abs(chunk)) > 0.001:
            chunks.append(chunk)
            last_audio_time = time.monotonic()

    if interrupted_by_text:
        return np.array([]), fs

    if not chunks:
        return np.array([]), fs

    audio = np.concatenate(chunks).squeeze()
    peak = np.max(np.abs(audio))

    if peak > 0:
        audio = audio / peak

    return audio, fs


def obter_entrada_usuario():

    global last_input_channel

    try:
        text = text_input_queue.get_nowait()
        last_input_channel = "OWNER_TEXT"
        return text
    except queue.Empty:
        pass

    if not LOAD_STT or not stt_runtime_enabled:
        return None

    if should_process_audio():

        time.sleep(0.2)
        audio, fs = record_audio()

        if stt is None:
            print("⚠️ STT está desativado")
            return None

        text = stt.transcribe(audio, fs)

        if not text:
            print("⚠️ STT não retornou texto útil")
            return None

        print()
        print("─" * 60)
        print(f"🧑 Neitan: {text}")
        print("─" * 60)
        print()

        last_input_channel = "OWNER_STT"
        return text

    return None


# =========================
# ✅ VALIDAÇÃO
# =========================

def is_valid_text(text):

    if not text:
        return False

    text = text.strip()

    if len(text) < 2:
        return False

    if text.count("!") > len(text) * 0.3:
        return False

    return True


# =========================
# 🧭 DETECÇÃO SIMPLES DE CAPACIDADES
# =========================

def detectar_capacidade(text):

    texto = str(text or "").lower().strip()

    if re.search(r"\b(l[eê]|leia|ler|lê)\b.*\b(chat|mensagem|mensagens)\b", texto):
        return "read_chat"

    if re.search(r"\b(resume|resumir|resuma)\b.*\b(chat|mensagem|mensagens)\b", texto):
        return "read_chat"

    if re.search(r"\b(l[eê]|leia|ler|abre|abrir|resume|resuma)\b.*\b(arquivo|\.txt|\.json|\.py)\b", texto):
        return "read_file"

    if re.search(r"\b(tela|print|screenshot|screen)\b", texto):
        if re.search(r"\b(v[eê]|ver|leia|ler|captura|capturar|olha|analisar|analisa)\b", texto):
            return "read_screen"

    # Envio real ao chat pertence exclusivamente ao Host Mode.

    return "none"


def criar_turn_context(text):

    capability = detectar_capacidade(text)
    response_budget = "short"

    if any(palavra in text.lower() for palavra in ["explica", "explique", "detalha", "passo a passo"]):
        response_budget = "medium"

    activity_info = activity_context.process_user_turn(text)

    return {
        "source": LOCAL_INPUT_SOURCE,
        "source_name": LOCAL_INPUT_SOURCE_NAME,
        "requested_capability": capability,
        "response_budget": response_budget,
        "activity_context": activity_info.get("prompt_context", ""),
        "activity_task": activity_info.get("task", ""),
        "activity_direct_response": activity_info.get("direct_response", ""),
        "activity_event": activity_info.get("event", "none"),
        "activity_state": activity_info.get("state", {})
    }


def capacidade_eh_operacional(capacidade):

    return response_cleaner.is_operational(capacidade)


def limpar_resposta(response, text, turn_context=None, mode="normal"):

    turn_context = turn_context or {}
    capability = str(turn_context.get("requested_capability", "none")).lower().strip()
    budget = turn_context.get("response_budget", "short")

    return response_cleaner.clean(
        text=response,
        user_text=text,
        mode=mode,
        capability=capability,
        response_budget=budget
    ).strip()




# =========================
# 🛡️ INPUT FIREWALL
# =========================

def aplicar_input_firewall(text, source_channel="OWNER_TEXT"):

    packet = input_firewall.analyze(text, source=source_channel)

    correction = ""
    if packet.changed:
        correction = f" | corrigido='{packet.text}'"

    print(
        f"🛡️ InputFirewall: quality={packet.quality} | intent={packet.intent_hint or 'none'} | "
        f"llm={'SIM' if packet.allow_llm else 'NÃO'} | mem={'SIM' if packet.allow_memory else 'NÃO'} | "
        f"retrieval={'SIM' if packet.allow_retrieval else 'NÃO'} | motivo={packet.reason}{correction}"
    )

    return packet


def resposta_direta_input_firewall(packet):

    direct = str(getattr(packet, "direct_response", "") or "").strip()
    if not direct:
        return ""

    return limpar_resposta(direct, packet.text or packet.raw_text, turn_context=packet.to_turn_context(), mode="normal")


# =========================
# 🧭 DIÁLOGO / ALVO / RUÍDO
# =========================

def aplicar_dialogue_act_gate(text, turn_context):

    result = dialogue_act_gate.analyze(text, conv_history=conv_history, turn_context=turn_context)
    turn_context.update(result.to_turn_context())

    if result.direct_response:
        turn_context["dialogue_direct_response"] = result.direct_response

    print(f"🎭 DialogueAct: act={result.act} | target={result.target} | direct={'SIM' if result.direct_response else 'NÃO'} | motivo={result.reason}")

    return result


def resposta_direta_dialogue_act(text, turn_context):

    direct = str((turn_context or {}).get("dialogue_direct_response", "")).strip()
    if not direct:
        return ""

    return limpar_resposta(direct, text, turn_context=turn_context, mode="normal")


# =========================
# 🔊 SAÍDA
# =========================

def play_audio(file_path):

    rate, data = wav.read(file_path)
    sd.play(data, rate)
    sd.wait()


def entregar_resposta(text, response, turn_context=None):

    print(f'Diana: "{response}"')

    if tts_runtime_enabled:

        clean_response = clean_for_tts(response)
        output_file = tts.speak(clean_response)

        if output_file:
            play_audio(output_file)
        else:
            print("⚠️ áudio não foi gerado")

    else:
        print("🔇 TTS desativado para testes")


# =========================
# 💾 REGISTRAR INTERAÇÃO
# =========================

def _normalizar_mem0_autosave(text):

    text = str(text or "").lower().strip()
    text = re.sub(r"[^a-záàâãéêíóôõúç0-9 _/-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _limpar_valor_memoria(valor):

    valor = str(valor or "").strip()

    if "?" in valor:
        return ""

    valor = re.split(r"\b(mas qual|qual desses|qual dos|e qual|sao cinco|são cinco)\b", valor, maxsplit=1, flags=re.IGNORECASE)[0]
    valor = re.split(r"[.!?]", valor, maxsplit=1)[0]
    valor = valor.strip(" .,!?:;\"\'")
    valor = re.sub(r"^(o|a|os|as)\s+", "", valor).strip()
    valor = re.sub(r"^(muito|bastante|demais)\s+", "", valor, flags=re.IGNORECASE).strip()
    valor = re.sub(r"\s+demais$", "", valor, flags=re.IGNORECASE).strip()

    if not valor or len(valor) > 80:
        return ""

    return valor


def _chave_generica_memoria(categoria):

    categoria = _normalizar_mem0_autosave(categoria)
    categoria = re.sub(r"[^a-z0-9_ ]+", " ", categoria)
    categoria = re.sub(r"\s+", "_", categoria).strip("_")
    categoria = re.sub(r"^(?:o|a|os|as)_+", "", categoria)

    if not categoria or len(categoria) > 40:
        return ""

    bloqueados = {"coisa", "negocio", "bagulho", "isso", "aquilo"}
    if categoria in bloqueados:
        return ""

    return categoria + "_favorito"


def extrair_memoria_direta_mem0(text):

    texto_original = str(text or "").strip()
    normalized = _normalizar_mem0_autosave(texto_original)

    patterns = [
        (r"\b(?:o )?meu filme alien favorito (?:é|e|eh)\s+(.+)$", "filme_alien_favorito"),
        (r"\bmeu filme favorito (?:é|e|eh)\s+(.+)$", "filme_favorito"),
        (r"\bmeu jogo favorito (?:é|e|eh)\s+(.+)$", "jogo_favorito"),
        (r"\bminha comida favorita (?:é|e|eh)\s+(.+)$", "comida_favorita"),
        (r"\bme chama de\s+(.+)$", "apelido_preferido"),
        (r"\bpode me chamar de\s+(.+)$", "apelido_preferido"),
    ]

    gosto_patterns = [
        r"\b(?:eu\s+)?gosto\s+muito\s+de\s+(.+)$",
        r"\b(?:eu\s+)?gosto\s+bastante\s+de\s+(.+)$",
        r"\b(?:eu\s+)?gosto\s+de\s+(.+)$",
        r"\b(?:eu\s+)?curto\s+muito\s+(.+)$",
        r"\b(?:eu\s+)?curto\s+demais\s+(.+)$",
        r"\b(?:eu\s+)?curto\s+(.+)$",
        r"\btambém\s+gosto\s+de\s+(.+)$",
        r"\btambem\s+gosto\s+de\s+(.+)$",
        r"\btambém\s+curto\s+(.+)$",
        r"\btambem\s+curto\s+(.+)$",
    ]
    for pattern in gosto_patterns:
        match = re.search(pattern, normalized)
        if match:
            value = _limpar_valor_memoria(match.group(1))
            if value:
                return f"gosta_de: {value}"

    favor_verb = r"(?:é|e|eh|continua\s+sendo|segue\s+sendo|agora\s+é|agora\s+e|agora\s+eh)"
    contexto = r"(?:\s+(?:de|do|da|dos|das|em|no|na|nos|nas|pra|para|pro|nessa|nesse)\s+[a-záàâãéêíóôõúç0-9_ %+.\-]{2,80})?"
    favorite_patterns = [
        r"\b(?:pra|para|pro)\s+([a-záàâãéêíóôõúç0-9_ %+.\-]{2,60})\s*,?\s+(?:o\s+)?meu\s+favorit[oa]s?\s+" + favor_verb + r"\s+(.+)$",
        r"\b(?:pra|para|pro)\s+([a-záàâãéêíóôõúç0-9_ %+.\-]{2,60})\s*,?\s+(?:a\s+)?minha\s+favorit[oa]s?\s+" + favor_verb + r"\s+(.+)$",
        r"\b(?:o\s+)?meu\s+([a-záàâãéêíóôõúç0-9_ %+.\-]{2,60})\s+favorit[oa]s?" + contexto + r"\s+" + favor_verb + r"\s+(.+)$",
        r"\b(?:a\s+)?minha\s+([a-záàâãéêíóôõúç0-9_ %+.\-]{2,60})\s+favorit[oa]s?" + contexto + r"\s+" + favor_verb + r"\s+(.+)$",
    ]

    for pattern in favorite_patterns:
        generic_match = re.search(pattern, normalized)
        if generic_match:
            key = _chave_generica_memoria(generic_match.group(1))
            value = _limpar_valor_memoria(generic_match.group(2))
            if value in ["motola", "motorola"] or ("celular" in key and "motorola" in value):
                value = "Motorola"
            if "codec" in key:
                low = _normalizar_mem0_autosave(value)
                if "av1" in low:
                    value = "av1"
                elif "h 265" in low or "h.265" in low or "h265" in low:
                    value = "h 265"
                elif "h 264" in low or "h.264" in low or "h264" in low:
                    value = "h 264"
            if key and value:
                return f"{key}: {value}"

    for pattern, key in patterns:
        match = re.search(pattern, normalized)
        if not match:
            continue

        value = _limpar_valor_memoria(match.group(1))

        if value in ["motola", "motorola"] or ("celular" in key and "motorola" in value):
            value = "Motorola"

        if key == "filme_alien_favorito":
            low = _normalizar_mem0_autosave(value)
            if "alien 2" in low or "aliens" in low or "resgate" in low:
                value = "Aliens: O Resgate"

        if value:
            return f"{key}: {value}"

    return ""


def deve_salvar_mem0_auto(text, response):

    if not MEM0_AUTO_SAVE_SMART_FILTER:
        return True

    normalized = _normalizar_mem0_autosave(text)

    if len(normalized) < MEM0_AUTO_SAVE_MIN_CHARS:
        return False

    tokens = set(normalized.split())
    simple_tokens = {
        "oi", "olá", "ola", "e", "aí", "ai", "eai", "eae", "fala", "salve",
        "bom", "boa", "dia", "tarde", "noite", "sim", "não", "nao", "ok",
        "blz", "beleza", "valeu", "obrigado", "obrigada", "kk", "kkk", "haha"
    }

    if tokens and tokens.issubset(simple_tokens) and len(tokens) <= 5:
        return False

    # Perguntas comuns não são memória. Elas podem consultar Mem0, mas não devem alimentar Mem0.
    if normalized.endswith("?") or re.search(r"\b(qual|quais|quem|quando|onde|como|por que|porque)\b", normalized):
        has_memory_write_signal = re.search(
            r"\b(lembra|memoriza|salva|guarda|anota|meu|minha|meus|minhas|eu sou|eu gosto|eu curto|eu prefiro)\b",
            normalized
        )
        if not has_memory_write_signal:
            return False

    memory_patterns = [
        r"\b(lembra|memoriza|salva|guarda|anota)\b",
        r"\b(meu|minha|meus|minhas)\b.+\b(eh|é|era|sao|são|foi|fica|vai ser)\b",
        r"\b(eu sou|eu era|eu gosto|eu curto|eu prefiro|eu odeio|eu nao gosto|eu não gosto|também gosto|tambem gosto|também curto|tambem curto|gosto bastante|curto demais)\b",
        r"\b(pode me chamar|me chama de|troca .+ para|troca .+ pra|atualiza .+ agora|agora .+ eh|agora .+ é|continua sendo|segue sendo)\b",
        r"\b(o|a) .+ (eh|é) .+\b"
    ]

    if any(re.search(pattern, normalized) for pattern in memory_patterns):
        return True

    return False


def registrar_interacao(text, response, turn_context=None):

    turn_context = turn_context or {}
    source_role = str(turn_context.get("source", LOCAL_INPUT_SOURCE)).upper().strip()
    source_name = str(turn_context.get("source_name", LOCAL_INPUT_SOURCE_NAME)).strip()

    conv_history.add_turn(text, response, source_role=source_role, source_name=source_name)
    session_summarizer.record_turn(text, response, source_role=source_role, source_name=source_name)

    try:
        activity_context.record_assistant_response(response)
    except Exception as e:
        print("⚠️ ActivityContext ignorado por erro:", e)

    try:
        session_context.registrar_turno(text, response, turn_context=turn_context)
    except Exception as e:
        print("⚠️ SessionContext ignorado por erro:", e)

    if turn_context.get("allow_memory") is False:
        print("🧠 Mem0 auto-save: ignorado pelo InputFirewall")
        return

    if mem0_autosave_runtime_enabled and turn_context.get("source", LOCAL_INPUT_SOURCE).upper() == "OWNER":
        if deve_salvar_mem0_auto(text, response):
            try:
                memoria_direta = extrair_memoria_direta_mem0(text)
                if memoria_direta:
                    mem0_memory.salvar_interacao(text, response, memoria_direta=memoria_direta)
                else:
                    print("🧠 Mem0 auto-save: ignorado por memória ambígua")
            except Exception as e:
                print("⚠️ Mem0 auto-save ignorado por erro:", e)
        else:
            print("🧠 Mem0 auto-save: ignorado por filtro leve")


# =========================
# 🧾 FORMATAÇÃO DE CAMPOS DA BASE
# =========================

def formatar_resposta_de_campo(entry, field, field_data):

    nome = str(entry.get("name", "esta entrada")).strip()
    status = str(field_data.get("status", "unknown")).strip()
    value = field_data.get("value")

    if status == "unknown":
        labels = {
            "area": "a área",
            "room": "a sala",
            "requirements": "os requisitos",
            "boss": "o chefe necessário",
            "effect": "o efeito",
            "uses": "os usos",
            "acquisition": "a forma de aquisição"
        }
        return f"A base ainda não informa {labels.get(field, 'esse campo')} de {nome}, Neitan."

    if status == "none":
        labels = {
            "requirements": "não possui requisitos cadastrados",
            "boss": "não exige derrotar chefe ou miniboss",
            "acquisition": "não possui evento obrigatório de aquisição"
        }
        return f"{nome} {labels.get(field, 'não possui esse requisito')}, Neitan."

    if field == "area":
        room = entry.get("raw", {}).get("room")
        complemento = f", na {room}" if room else ""
        return f"{nome} fica em {value}{complemento}, Neitan."

    if field == "room":
        area = entry.get("raw", {}).get("area")
        complemento = f", em {area}" if area else ""
        return f"{nome} fica na {value}{complemento}, Neitan."

    if field == "boss":
        return f"Para obter {nome} pela progressão normal, você precisa derrotar {value}, Neitan."

    if field == "requirements":
        data = value if isinstance(value, dict) else {}
        parts = []
        all_items = data.get("all_items") or []
        any_items = data.get("any_items") or []
        if all_items:
            parts.append("todos estes itens: " + ", ".join(all_items))
        if any_items:
            parts.append("pelo menos um destes itens: " + ", ".join(any_items))
        if data.get("minimum_energy_tanks") is not None:
            parts.append(f"pelo menos {data['minimum_energy_tanks']} Energy Tanks")
        if data.get("minimum_reserve_tanks") is not None:
            parts.append(f"pelo menos {data['minimum_reserve_tanks']} Reserve Tanks")
        ammo = data.get("ammo") or {}
        for key, amount in ammo.items():
            parts.append(f"{amount} de {key.replace('_', ' ')}")
        if not parts:
            return f"A base marca os requisitos de {nome} como conhecidos, mas não lista nenhum requisito específico, Neitan."
        return f"Para {nome}, a base exige " + "; ".join(parts) + "."

    if field in {"effect", "uses"}:
        values = value if isinstance(value, list) else [value]
        return f"{nome}: " + " ".join(str(item) for item in values if item) 

    if field == "acquisition":
        data = value if isinstance(value, dict) else {}
        notes = data.get("normal_route_notes")
        if notes:
            return f"{nome}: {notes}"
        return f"A aquisição de {nome} está cadastrada, mas sem descrição detalhada, Neitan."

    return f"{nome}: {value}"


# =========================
# 🧭 RESPOSTAS DETERMINÍSTICAS DE RETRIEVAL
# =========================

def resolver_resposta_deterministica_retrieval(retrieved):

    if not retrieved:
        return None

    if retrieved.get("personal_query"):
        facts = retrieved.get("owner_facts", [])
        mem0_memories = retrieved.get("mem0_memories", [])

        if facts:
            fact = facts[0]
            key = str(fact.get("key", "")).strip()
            value = str(fact.get("value", "")).strip()
            labels = {
                "filme_favorito": "filme favorito",
                "comida_favorita": "comida favorita",
                "jogo_favorito": "jogo favorito",
                "serie_favorita": "série favorita",
                "desenho_favorito": "desenho favorito",
                "banda_favorita": "banda favorita",
                "franquia_de_jogo_favorita": "franquia de jogo favorita",
                "doom_favorito": "Doom favorito",
                "metroid_favorito": "Metroid favorito",
                "zelda_favorito": "Zelda favorito"
            }
            label = labels.get(key, key.replace("_", " "))

            if value:
                return f"Seu {label} é {value}, Neitan."

        if mem0_memories:
            # Deixa o LLM responder usando o bloco MEMÓRIAS MEM0 RECUPERADAS do prompt.
            return None

        return "Eu não tenho essa informação no meu perfil, no Mem0 nem no histórico atual, Neitan."

    operation = retrieved.get("knowledge_operation")

    if operation == "correction":
        return "Você tem razão, Neitan. Eu inventei ou recuperei a entrada errada; descartei esse contexto e não vou defender a resposta anterior."

    if operation == "topic_change":
        return "Beleza, Neitan. Assunto anterior encerrado; manda o próximo."

    if operation in {"feedback", "topic_setup"}:
        return None

    if retrieved.get("knowledge_operation") == "count":
        collection = retrieved.get("knowledge_collection") or "base"
        count = retrieved.get("knowledge_count", 0)
        return f"Encontrei {count} entrada(s) na coleção {collection}, Neitan."

    if retrieved.get("knowledge_operation") == "field":
        entries = retrieved.get("knowledge_entries", [])
        fields = retrieved.get("knowledge_requested_fields", []) or [retrieved.get("knowledge_requested_field", "")]
        fields = [field for field in fields if field]

        if entries and fields:
            entry = entries[0]
            responses = []
            for field in fields:
                field_data = prompt_builder.context_retriever.knowledge.get_field_value(entry, field)
                responses.append(formatar_resposta_de_campo(entry, field, field_data))

            # Evita repetir nome e vocativo em respostas compostas.
            if len(responses) == 1:
                return responses[0]

            cleaned = []
            for index, response in enumerate(responses):
                response = response.strip()
                if index > 0:
                    response = re.sub(r"^" + re.escape(str(entry.get("name", ""))) + r"\s*", "", response, flags=re.IGNORECASE)
                response = re.sub(r", Neitan\.$", ".", response)
                cleaned.append(response)
            return " ".join(cleaned)

    if retrieved.get("knowledge_status") == "NOT_FOUND" and retrieved.get("knowledge_collection"):
        return "Não encontrei uma entrada compatível na minha base local, Neitan."

    return None


# =========================
# 🔒 VALIDAÇÃO DE RESPOSTA ANCORADA
# =========================

def validar_resposta_ancorada(response, retrieved):

    if not response or not retrieved:
        return response

    if retrieved.get("knowledge_status") != "FOUND":
        return response

    entries = retrieved.get("knowledge_entries", [])

    if not entries:
        return response

    lower = str(response).lower()
    sinais_de_fuga = [
        "vou precisar do nome",
        "preciso do nome",
        "qual técnica",
        "qual tecnica",
        "tem outras também",
        "tem outras tambem",
        "não sei qual",
        "nao sei qual"
    ]

    if any(sinal in lower for sinal in sinais_de_fuga):
        entry = entries[0]
        nome = str(entry.get("name", "")).strip()
        definicao = str(entry.get("definition", "")).strip() or str(entry.get("details", "")).strip()

        if nome and definicao:
            return f"{nome}: {definicao}"

    return response


# =========================
# 🧠 GERAR RESPOSTA PELO BRAIN
# =========================

def gerar_resposta_brain(text, turn_context):

    global last_prompt_text

    activity_direct_response = str((turn_context or {}).get("activity_direct_response", "")).strip()
    if activity_direct_response:
        return limpar_resposta(activity_direct_response, text, turn_context=turn_context, mode="normal")

    dialogue_direct_response = resposta_direta_dialogue_act(text, turn_context)
    if dialogue_direct_response:
        return dialogue_direct_response

    if turn_context.get("allow_llm") is False:
        return "Não peguei isso com confiança suficiente pra mandar pro meu cérebro grande. Repete essa com carinho técnico, Neitan."

    prompt = prompt_builder.build(
        user_text=text,
        conv_history=conv_history,
        extra_context=None,
        turn_context=turn_context
    )
    last_prompt_text = prompt

    retrieved = prompt_builder.get_last_retrieval()

    memoria_direta = extrair_memoria_direta_mem0(text)
    query_plan = (retrieved or {}).get("query_plan") or {}
    if memoria_direta and query_plan.get("operation") == "remember":
        chave, valor = memoria_direta.split(":", 1)
        chave = chave.strip()
        valor = valor.strip()
        label = chave.replace("_", " ")
        return f"Anotado: {label} = {valor}."

    deterministic_response = resolver_resposta_deterministica_retrieval(retrieved)

    if deterministic_response:
        return deterministic_response

    raw_response = llm.chat(
        prompt,
        response_budget=turn_context.get("response_budget", "short")
    )

    parsed = action_parser.parse(raw_response)
    response = parsed.get("speaking", "")

    response = limpar_resposta(
        response,
        text,
        turn_context=turn_context,
        mode="operational" if capacidade_eh_operacional(turn_context.get("requested_capability")) else "normal"
    )

    response = validar_resposta_ancorada(response, retrieved)

    if not response:
        # Fallback mínimo: usa resposta crua sem virar "debug falado".
        response = response_cleaner.clean_minimal(
            raw_response,
            response_budget=turn_context.get("response_budget", "short")
        )

    return response.strip()


# =========================
# 🧹 SHUTDOWN
# =========================

def shutdown():

    print("\nEncerrando...")

    try:
        sd.stop()
    except Exception:
        pass

    for obj in [tts, stt, vad, session_context, mem0_memory, host_mode, activity_context]:

        if obj is None:
            continue

        for method_name in ["shutdown", "close", "fechar", "stop"]:

            method = getattr(obj, method_name, None)

            if callable(method):
                try:
                    method()
                except Exception:
                    pass
                break


# =========================
# 🧾 COMANDOS LOCAIS
# =========================

COMMANDS_BANNER = (
    "/limpar | /limpar sessao | /fatos | /atividade | /modulos | "
    "/modulo NOME on|off | /host on|off | /host status | /host send on|off | "
    "/host mode autonomous|read | /host read | /prompt | /mem0 status | "
    "/mem0 remember TEXTO | /history clear | /tts on|off|status | /stt on|off|status | /comandos"
)


def format_runtime_modules_status():

    linhas = [
        f"host: {'ON' if host_mode.enabled else 'OFF'}",
        f"host_send: {'ON' if host_mode.send_to_chat else 'OFF'}",
        f"host_mode: {host_mode.mode}",
        f"tts: {'ON' if tts_runtime_enabled else 'OFF'}",
        f"stt: {'ON' if stt_runtime_enabled and stt is not None else 'OFF'}",
        f"mem0_autosave: {'ON' if mem0_autosave_runtime_enabled else 'OFF'}",
        f"query_planner: {'ON' if QUERY_PLANNER_ENABLED else 'OFF'}",
        f"session_summarizer: {'ON' if SESSION_SUMMARIZER_ENABLED else 'OFF'}",
        "skills: read_chat, read_file, read_screen, donate, command, style, game_context, chat_reply"
    ]

    return "\n".join(linhas)


def limpar_sessao_runtime():

    conv_history.clear()

    try:
        session_context.current = session_context.default_current_session()
        session_context.save_current_session()
        session_context.ensure_session_summary_format()
    except Exception as e:
        print("⚠️ Falha ao limpar SessionContext:", e)

    try:
        activity_context.clear()
    except Exception as e:
        print("⚠️ Falha ao limpar ActivityContext:", e)

    try:
        session_summarizer.state = session_summarizer._default_state()
        session_summarizer._save_state()
        session_summarizer._write_readable_summary()
    except Exception:
        pass


def set_runtime_module(name, enabled):

    global tts_runtime_enabled, stt_runtime_enabled, mem0_autosave_runtime_enabled

    name = str(name or "").lower().strip()

    if name in ["tts", "voz"]:
        tts_runtime_enabled = bool(enabled)
        return True, f"TTS: {'ON' if tts_runtime_enabled else 'OFF'}"

    if name in ["stt", "mic", "microfone"]:
        stt_runtime_enabled = bool(enabled)
        return True, f"STT: {'ON' if stt_runtime_enabled and stt is not None else 'OFF'}"

    if name in ["mem0", "memoria", "memória"]:
        mem0_autosave_runtime_enabled = bool(enabled)
        return True, f"Mem0 auto-save: {'ON' if mem0_autosave_runtime_enabled else 'OFF'}"

    if name in ["host", "hostmode", "chat_host"]:
        host_mode.set_enabled(bool(enabled))
        return True, f"Host Mode: {'ON' if host_mode.enabled else 'OFF'}"

    return False, "Módulo desconhecido. Use: tts, stt, mem0 ou host."


def handle_terminal_command(comando, texto_original):

    global tts_runtime_enabled, stt_runtime_enabled, mem0_autosave_runtime_enabled

    if comando == "/comandos":
        print("Comandos: " + COMMANDS_BANNER)
        return True

    if comando == "/limpar":
        conv_history.clear()
        print("🧹 Histórico curto limpo.")
        return True

    if comando == "/limpar sessao":
        limpar_sessao_runtime()
        print("🧼 Sessão limpa: histórico curto, contexto leve, atividade e resumo auxiliar.")
        return True

    if comando == "/fatos":
        print(json.dumps(session_context.current.get("owner_session_preferences", {}), ensure_ascii=False, indent=2))
        return True

    if comando == "/atividade":
        print(activity_context.get_prompt_context() or "Nenhuma atividade contextual ativa.")
        return True

    if comando == "/modulos":
        print(format_runtime_modules_status())
        return True

    if comando.startswith("/modulo "):
        parts = comando.split()
        if len(parts) != 3 or parts[2] not in ["on", "off"]:
            print("Uso: /modulo NOME on|off")
            return True
        ok, msg = set_runtime_module(parts[1], parts[2] == "on")
        print(msg)
        return True

    if comando in ["/tts on", "/tts off"]:
        tts_runtime_enabled = comando.endswith(" on")
        print(f"TTS: {'ON' if tts_runtime_enabled else 'OFF'}")
        return True

    if comando == "/tts status":
        print(f"TTS: {'ON' if tts_runtime_enabled else 'OFF'} | provider={getattr(tts, 'provider', 'desconhecido')}")
        return True

    if comando in ["/stt on", "/stt off"]:
        stt_runtime_enabled = comando.endswith(" on")
        print(f"STT: {'ON' if stt_runtime_enabled and stt is not None else 'OFF'}")
        return True

    if comando == "/stt status":
        print(f"STT: {'ON' if stt_runtime_enabled and stt is not None else 'OFF'} | engine={STT_ENGINE}")
        return True

    if comando == "/mem0 status":
        print(f"Mem0 auto-save: {'ON' if mem0_autosave_runtime_enabled else 'OFF'} | Mem0 enabled={getattr(mem0_memory, 'enabled', False)}")
        return True

    if comando == "/prompt":
        print(last_prompt_text or "Ainda não existe prompt de turno para mostrar.")
        return True

    return False


# =========================
# 🔁 LOOP PRINCIPAL
# =========================

print(f"🎮 SEGURE {PUSH_TO_TALK_KEY.upper()} PARA FALAR | DIGITE SUA MENSAGEM NO TERMINAL (Ctrl+C para sair)")
print("Comandos: " + COMMANDS_BANNER)

conv_history = ConversationHistory(max_turns=CONVERSATION_MAX_TURNS)

host_mode = ChatHostMode(
    llm=llm,
    clean_response_fn=lambda response, user_text="": response_cleaner.clean(response, user_text=user_text, mode="normal"),
    send_chat_fn=enviar_mensagem_chat
)

try:

    while True:

        text = obter_entrada_usuario()

        if not text:
            host_mode.tick()
            time.sleep(0.05)
            continue

        if not is_valid_text(text):
            print("⚠️ ignorado (sem entrada útil)")
            continue

        comando = text.lower().strip()

        if handle_terminal_command(comando, text):
            continue

        if comando in ["/chat caos on", "/chaos on"]:
            set_chat_chaos_mode(True)
            continue

        if comando in ["/chat caos off", "/chaos off"]:
            set_chat_chaos_mode(False)
            continue

        if comando == "/host on":
            host_mode.set_enabled(True)
            continue

        if comando == "/host off":
            host_mode.set_enabled(False)
            continue

        if comando == "/host send on":
            host_mode.set_send_to_chat(True)
            continue

        if comando == "/host send off":
            host_mode.set_send_to_chat(False)
            continue

        if comando == "/host mode autonomous":
            host_mode.set_mode("autonomous")
            continue

        if comando in ["/host mode read", "/host mode read_response", "/host mode leitura"]:
            host_mode.set_mode("read_response")
            continue

        if comando in ["/host read", "/host responder", "/host resposta"]:
            host_mode.read_and_respond()
            continue

        if re.search(r"\b(l[eê]|leia|ler)\b.*\bchat\b.*\b(responde|responder|resposta)\b", comando):
            host_mode.read_and_respond()
            continue

        if comando == "/host status":
            print(host_mode.get_status_text())
            continue

        if comando.startswith("/mem0 remember ") or comando.startswith("/mem0 lembrar "):
            memoria_manual = re.sub(r"^/mem0\s+(remember|lembrar)\s+", "", text, flags=re.IGNORECASE).strip()

            if memoria_manual:
                mem0_memory.salvar_memoria_manual(memoria_manual, metadata={"source": "manual_runtime"})
                print("🧠 Mem0: memória manual enviada.")
            else:
                print("⚠️ Use: /mem0 lembrar texto da memória")

            continue

        if comando == "/history clear":
            conv_history.clear()
            print("🧹 Histórico curto limpo.")
            continue

        input_packet = aplicar_input_firewall(text, source_channel=last_input_channel)

        firewall_direct_response = resposta_direta_input_firewall(input_packet)
        if firewall_direct_response:
            turn_context = criar_turn_context(input_packet.text)
            turn_context.update(input_packet.to_turn_context())
            if input_packet.quality != "BLOCKED":
                registrar_interacao(input_packet.text, firewall_direct_response, turn_context=turn_context)
            else:
                print("🧠 Histórico/Mem0: entrada bloqueada não registrada")
            entregar_resposta(input_packet.text, firewall_direct_response, turn_context=turn_context)
            time.sleep(0.5)
            continue

        text = input_packet.text

        turn_context = criar_turn_context(text)
        turn_context.update(input_packet.to_turn_context())
        dialogue_result = aplicar_dialogue_act_gate(text, turn_context)
        capability = turn_context.get("requested_capability", "none")
        modo_operacional = capacidade_eh_operacional(capability)

        # =========================
        # ⚡ SKILLS OPERACIONAIS DIRETAS
        # =========================

        response = None

        if modo_operacional:
            response = skill_manager.verificar_resposta_direta(
                user_text=text,
                conversation=conv_history,
                turn_context=turn_context
            )

        if response:
            response = limpar_resposta(
                response,
                text,
                turn_context=turn_context,
                mode="operational"
            )

            if response:
                registrar_interacao(text, response, turn_context=turn_context)
                entregar_resposta(text, response, turn_context=turn_context)

                time.sleep(0.5)
                continue

        # =========================
        # 🧠 BRAIN PRINCIPAL
        # =========================

        response = gerar_resposta_brain(text, turn_context)

        if not response:
            print("⚠️ resposta vazia ignorada; nada foi enviado para TTS/chat.")
            time.sleep(0.5)
            continue

        registrar_interacao(text, response, turn_context=turn_context)
        entregar_resposta(text, response, turn_context=turn_context)

        time.sleep(0.5)

except KeyboardInterrupt:

    shutdown()
