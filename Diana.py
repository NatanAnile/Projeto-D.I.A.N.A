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
    PTT_RELEASE_LOCKOUT_ENABLED,
    OWNER_NAME,
    LOCAL_INPUT_SOURCE,
    LOCAL_INPUT_SOURCE_NAME,
    CONVERSATION_MAX_TURNS,
    ALLOW_LIVE_REFERENCES_WITHOUT_CONTEXT,
    PROJECT_VERSION,
    QUERY_PLANNER_ENABLED,
    SESSION_SUMMARIZER_ENABLED,
    STT_ENGINE
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
from brain.activity_context import ActivityContextProvider
from brain.dialogue_act_gate import DialogueActGate

from skills.skill_system import SkillManager
from integrations.streamerbot_chat import set_chat_chaos_mode, enviar_mensagem_chat
from integrations.chat_host_mode import ChatHostMode

from utils.response_cleaner import ResponseCleaner
from utils.text_cleaner import clean_for_tts

from runtime.input_firewall import InputFirewall
from runtime.conversation_ledger import ConversationLedger
from runtime.retrieval_responder import RetrievalResponder
from runtime.ptt_guard import PushToTalkGuard
from runtime.output_firewall import OutputFirewall
from runtime.session_preference_responder import SessionPreferenceResponder
from runtime.intent_router import detect_capability


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
prompt_builder = PromptBuilder(
    session_summarizer=session_summarizer,
    session_context=session_context
)
retrieval_responder = RetrievalResponder(prompt_builder)
action_parser = ActionParser()
activity_context = ActivityContextProvider()
dialogue_act_gate = DialogueActGate()
input_firewall = InputFirewall()
ptt_guard = PushToTalkGuard(PUSH_TO_TALK_KEY)
output_firewall = OutputFirewall()
session_preference_responder = SessionPreferenceResponder(session_context)

print(f"🧠 Diana Brain carregado — versão {PROJECT_VERSION}")
print(f"🎤 STT selecionado: {STT_ENGINE}")
print(f"🗺️ Query Planner auxiliar: {'ATIVADO' if QUERY_PLANNER_ENABLED else 'DESATIVADO'}")
print(f"🧠 Resumidor auxiliar: {'ATIVADO' if SESSION_SUMMARIZER_ENABLED else 'DESATIVADO'}")

# Estados runtime de módulos simples. Não alteram config.py; só valem até fechar a Diana.
tts_runtime_enabled = bool(TTS_ENABLED)
stt_runtime_enabled = bool(LOAD_STT)
last_prompt_text = ""
last_input_channel = "OWNER_TEXT"


# =========================
# 📝 HISTÓRICO DE CONVERSA
# =========================

# ConversationLedger é a fonte de verdade literal da sessão.
# Toda resposta final entregue ao usuário deve ser registrada nele,
# inclusive direct_response, joke_bank, retrieval determinístico e LLM.


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

def _is_ptt_pressed():

    try:
        return keyboard.is_pressed(PUSH_TO_TALK_KEY)
    except Exception:
        return False


def should_process_audio():

    if not LOAD_STT or not stt_runtime_enabled:
        return False

    # Edge-trigger: só inicia STT na transição solto -> pressionado.
    # Se o Windows/keyboard ficar reportando RIGHT CTRL preso, o guard
    # entra em lockout e o terminal continua utilizável.
    return ptt_guard.should_start(_is_ptt_pressed())

def record_audio(fs=16000):

    print("🎤 gravando...")

    chunks = []

    if not _is_ptt_pressed():
        print("⏱️ PTT soltou antes da gravação estabilizar; STT cancelado.")
        return np.array([]), fs

    time.sleep(0.08)

    record_start = time.monotonic()
    last_audio_time = record_start
    interrupted_by_text = False

    while _is_ptt_pressed():

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

        time.sleep(0.05)
        audio, fs = record_audio()

        if PTT_RELEASE_LOCKOUT_ENABLED:
            locked = ptt_guard.finish_recording(_is_ptt_pressed())
            if locked:
                print("🎛️ PTT ainda parece pressionado; STT em lockout até soltar a tecla. Texto continua liberado.")

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

    return detect_capability(text)


def criar_turn_context(text):

    capability = detectar_capacidade(text)
    confidence = 1.0 if capability != "none" else 0.0
    response_budget = "short"

    if any(palavra in text.lower() for palavra in ["explica", "explique", "detalha", "passo a passo"]):
        response_budget = "medium"

    activity_info = activity_context.process_user_turn(text)

    return {
        "source": LOCAL_INPUT_SOURCE,
        "source_name": LOCAL_INPUT_SOURCE_NAME,
        "requested_capability": capability,
        "confidence": confidence,
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
    raw_response = str(response or "").strip()

    # Leitura direta de arquivo é saída operacional literal.
    # Não passa pelo orçamento curto do ResponseCleaner, senão o arquivo lido é cortado.
    if capability == "read_file" and raw_response.lstrip().startswith("Li o arquivo "):
        return output_firewall.clean(raw_response)

    cleaned = response_cleaner.clean(
        text=response,
        user_text=text,
        mode=mode,
        capability=capability,
        response_budget=budget
    ).strip()

    return output_firewall.clean(cleaned)




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

    capability = str((turn_context or {}).get("requested_capability", "none")).lower().strip()
    if capacidade_eh_operacional(capability):
        return ""

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

def registrar_interacao(text, response, turn_context=None):

    turn_context = turn_context or {}
    source_role = str(turn_context.get("source", LOCAL_INPUT_SOURCE)).upper().strip()
    source_name = str(turn_context.get("source_name", LOCAL_INPUT_SOURCE_NAME)).strip()

    conv_history.add_turn(text, response, source_role=source_role, source_name=source_name, turn_context=turn_context)
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
        print("🧠 Contexto de sessão: entrada não usada para atualização leve")


# =========================
# 🧭 RETRIEVAL DETERMINÍSTICO
# =========================

# Implementado em runtime/retrieval_responder.py para manter Diana.py como orquestrador.


# =========================
# 🧠 GERAR RESPOSTA PELO BRAIN
# =========================

def gerar_resposta_brain(text, turn_context):

    global last_prompt_text

    activity_direct_response = str((turn_context or {}).get("activity_direct_response", "")).strip()
    if activity_direct_response:
        turn_context["response_origin"] = "activity_direct_response"
        turn_context["used_llm"] = False
        return limpar_resposta(activity_direct_response, text, turn_context=turn_context, mode="normal")

    dialogue_direct_response = resposta_direta_dialogue_act(text, turn_context)
    if dialogue_direct_response:
        turn_context["response_origin"] = "dialogue_direct_response"
        turn_context["used_llm"] = False
        return dialogue_direct_response

    if turn_context.get("allow_llm") is False:
        turn_context["response_origin"] = "llm_blocked_by_firewall"
        turn_context["used_llm"] = False
        return "Não peguei isso com confiança suficiente pra mandar pro meu cérebro grande. Repete essa com carinho técnico, Neitan."

    if str(turn_context.get("dialogue_act", "")) == "owner_preference_query":
        response = session_preference_responder.responder(text)
        turn_context["response_origin"] = "session_preference_direct"
        turn_context["used_llm"] = False
        return limpar_resposta(response, text, turn_context=turn_context, mode="normal")

    skill_extra = skill_manager.verificar_skills(
        user_text=text,
        conversation=conv_history,
        turn_context=turn_context
    )

    if skill_extra:
        turn_context["skill_context_active"] = True

    prompt = prompt_builder.build(
        user_text=text,
        conv_history=conv_history,
        extra_context=skill_extra,
        turn_context=turn_context
    )
    last_prompt_text = prompt

    retrieved = prompt_builder.get_last_retrieval()
    turn_context["retrieval_status"] = (retrieved or {}).get("knowledge_status", "") or ("FOUND" if (retrieved or {}).get("owner_facts") else "")
    turn_context["used_retrieval"] = bool((retrieved or {}).get("query_plan", {}).get("should_query") or (retrieved or {}).get("owner_facts") or (retrieved or {}).get("knowledge_entries"))

    deterministic_response = retrieval_responder.resolve(retrieved)

    if deterministic_response:
        turn_context["response_origin"] = "retrieval_deterministic"
        turn_context["used_llm"] = False
        return deterministic_response

    turn_context["response_origin"] = "llm"
    turn_context["used_llm"] = True

    raw_response = llm.chat(
        prompt,
        response_budget=turn_context.get("response_budget", "short")
    )

    if not raw_response and getattr(llm, "last_error", ""):
        turn_context["response_origin"] = "llm_error"
        return "Meu cérebro grande não respondeu agora. O Ollama recusou conexão, então não vou fingir que pensei bonito."

    parsed = action_parser.parse(raw_response)
    response = parsed.get("speaking", "")

    response = limpar_resposta(
        response,
        text,
        turn_context=turn_context,
        mode="operational" if capacidade_eh_operacional(turn_context.get("requested_capability")) else "normal"
    )

    response = retrieval_responder.validate_grounded_response(response, retrieved)

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

    for obj in [tts, stt, vad, session_context, host_mode, activity_context]:

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
    "/host mode autonomous|read | /host read | /prompt | /history clear | "
    "/tts on|off|status | /stt on|off|status | /ptt status|reset | /comandos"
)


def format_runtime_modules_status():

    linhas = [
        f"host: {'ON' if host_mode.enabled else 'OFF'}",
        f"host_send: {'ON' if host_mode.send_to_chat else 'OFF'}",
        f"host_mode: {host_mode.mode}",
        f"tts: {'ON' if tts_runtime_enabled else 'OFF'}",
        f"stt: {'ON' if stt_runtime_enabled and stt is not None else 'OFF'}",
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

    global tts_runtime_enabled, stt_runtime_enabled

    name = str(name or "").lower().strip()

    if name in ["tts", "voz"]:
        tts_runtime_enabled = bool(enabled)
        return True, f"TTS: {'ON' if tts_runtime_enabled else 'OFF'}"

    if name in ["stt", "mic", "microfone"]:
        stt_runtime_enabled = bool(enabled)
        return True, f"STT: {'ON' if stt_runtime_enabled and stt is not None else 'OFF'}"

    if name in ["host", "hostmode", "chat_host"]:
        host_mode.set_enabled(bool(enabled))
        return True, f"Host Mode: {'ON' if host_mode.enabled else 'OFF'}"

    return False, "Módulo desconhecido. Use: tts, stt ou host."


def handle_terminal_command(comando, texto_original):

    global tts_runtime_enabled, stt_runtime_enabled

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

    if comando == "/ptt status":
        status = ptt_guard.status(_is_ptt_pressed())
        print(
            f"PTT: key={status.key_name} | down={'SIM' if status.key_down else 'NÃO'} | "
            f"lockout={'SIM' if status.lockout_until_release else 'NÃO'} | "
            f"starts={status.started_count} | ignored={status.ignored_count}"
        )
        return True

    if comando == "/ptt reset":
        ptt_guard.reset()
        print("🎛️ PTT resetado. Próxima gravação só inicia em nova pressão da tecla.")
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

conv_history = ConversationLedger(max_turns=CONVERSATION_MAX_TURNS)

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

        if comando == "/history clear":
            conv_history.clear()
            print("🧹 Histórico curto limpo.")
            continue

        input_packet = aplicar_input_firewall(text, source_channel=last_input_channel)

        firewall_direct_response = resposta_direta_input_firewall(input_packet)
        if firewall_direct_response:
            turn_context = criar_turn_context(input_packet.text)
            turn_context.update(input_packet.to_turn_context())
            turn_context["response_origin"] = "input_firewall"
            turn_context["used_llm"] = False
            turn_context["used_retrieval"] = False
            if input_packet.quality != "BLOCKED":
                registrar_interacao(input_packet.text, firewall_direct_response, turn_context=turn_context)
            else:
                print("🧠 Histórico/contexto: entrada bloqueada não registrada")
            entregar_resposta(input_packet.text, firewall_direct_response, turn_context=turn_context)
            time.sleep(0.5)
            continue

        text = input_packet.text

        turn_context = criar_turn_context(text)
        turn_context.update(input_packet.to_turn_context())
        dialogue_result = aplicar_dialogue_act_gate(text, turn_context)
        capability = turn_context.get("requested_capability", "none")
        confidence = float(turn_context.get("confidence", 0.0) or 0.0)
        print(f"🧭 Capability: {capability} | confidence={confidence:.2f}")
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
            turn_context["response_origin"] = "skill_direct"
            turn_context["used_llm"] = False
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
