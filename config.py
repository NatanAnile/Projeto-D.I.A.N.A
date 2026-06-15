import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# =========================
# 📁 CAMINHOS / MODELOS EXTERNOS
# =========================

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DIANA_MODELS_DIR = os.getenv(
    "DIANA_MODELS_DIR",
    os.path.join(os.path.expanduser("~"), "DianaModels")
)

# =========================
# ⚙️ CONFIGURAÇÕES GERAIS DO DIANA
# =========================

# 🤖 LLM (Ollama)
LLM_MODEL = "qwen2.5:7b-Instruct"
LLM_URL = "http://localhost:11434/api/chat"
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_TOP_P = float(os.getenv("LLM_TOP_P", "0.9"))

# 🎤 STT
LOAD_STT = os.getenv("LOAD_STT", "true").lower() == "true"  # padrão: STT ligado
STT_ENGINE = os.getenv("STT_ENGINE", "parakeet")  # "parakeet" ou "whisper"

# Whisper continua disponível como fallback manual
WHISPER_MODEL = "large-v3" 
WHISPER_DEVICE = "cuda"  # "cpu" se precisar
WHISPER_COMPUTE_TYPE = "float16"

# Parakeet TDT 0.6B V3 pt-BR TAGARELA ONNX
PARAKEET_MODEL_REPO = "alefiury/parakeet-tdt-0.6b-v3-ptBR-TAGARELA-onnx"
PARAKEET_MODEL_PATH = os.getenv(
    "PARAKEET_MODEL_PATH",
    os.path.join(DIANA_MODELS_DIR, "parakeet-tdt-0.6b-v3-ptBR-TAGARELA-onnx")
)
PARAKEET_AUTO_DOWNLOAD = os.getenv("PARAKEET_AUTO_DOWNLOAD", "true").lower() == "true"
PARAKEET_LANGUAGE = os.getenv("PARAKEET_LANGUAGE", "pt")
PARAKEET_ONNX_PROVIDER = os.getenv("PARAKEET_ONNX_PROVIDER", "auto")


# 🎧 VAD (Silero)
VAD_MIN_SILENCE_MS = 800
VAD_SPEECH_PAD_MS = 400
VAD_THRESHOLD = 0.3

# =========================
# 🔊 TTS
# =========================

TTS_ENABLED = os.getenv("TTS_ENABLED", "false").lower() == "true"
TTS_MODEL = os.getenv("TTS_MODEL", "xtts_v2")
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "xtts")  # "elevenlabs" ou "xtts"
TTS_FALLBACK = os.getenv("TTS_FALLBACK", "xtts")

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")
ELEVENLABS_MODEL = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")

# 🎮 INPUT
PUSH_TO_TALK_KEY = os.getenv("PUSH_TO_TALK_KEY", "right ctrl").strip().lower() or "right ctrl"
PTT_START_TIMEOUT_SECONDS = float(os.getenv("PTT_START_TIMEOUT_SECONDS", "3.0"))
PTT_MAX_RECORD_SECONDS = float(os.getenv("PTT_MAX_RECORD_SECONDS", "12.0"))
PTT_SILENCE_ABORT_SECONDS = float(os.getenv("PTT_SILENCE_ABORT_SECONDS", "2.0"))

# 🧠 SKILLS
SKILL_MIN_COOLDOWN = 60
SKILL_MAX_COOLDOWN = 120

# 🐞 DEBUG
DEBUG_STT = True
DEBUG_SKILLS = True

# =========================
# 💬 TWITCH CHAT
# =========================

TWITCH_CHANNEL = "natan_anile"
CHAT_LOG_PATH = "data/chat/live_chat.txt"
CHAT_MAX_LINES = 200
CHAT_READ_LAST_LINES = 12

# =========================
# 💬 CHAT OUTPUT / STREAMER.BOT
# =========================

CHAT_REPLY_ENABLED = True
CHAT_REPLY_QUEUE_PATH = "data/out/chat_queue"
CHAT_REPLY_MAX_CHARS = 200

# =========================
# 💬 CHAT IDENTITY
# =========================

CHAT_BOT_USERS = [
    "neitanbot"
]

# =========================
# 👁️ SCREEN CAPTURE
# =========================

SCREENSHOT_PATH = "data/screenshots"
SCREENSHOT_FILE_NAME = "last_screen.png"

# 1 = monitor principal
# 2 = segundo monitor
SCREENSHOT_MONITOR = 1

# =========================
# 💬 CHAT SAFETY / CHAOS MODE
# =========================

CHAT_BLOCK_LINKS = True
CHAT_ALLOW_CHAOS = False

# =========================
# 🎭 STYLE AUTONOMY
# =========================

STYLE_AUTONOMY_ENABLED = True

STYLE_CANDIDATES_PATH = "data/style/style_candidates.json"
STYLE_PROMOTED_PATH = "data/style/style_promoted.json"

STYLE_MIN_EXPRESSION_LEN = 4
STYLE_MAX_EXPRESSION_LEN = 80

STYLE_AUTO_PROMOTION_ENABLED = False

STYLE_PROMOTION_OCCURRENCES = 3
STYLE_PROMOTION_SCORE = 1.1

STYLE_CONTEXT_LIMIT = 6



# =========================
# 👤 IDENTIDADE DAS FONTES
# =========================

OWNER_NAME = "Natan"
OWNER_ALIASES = ["Natan", "Neitan", "natan_anile"]
LOCAL_INPUT_SOURCE = "OWNER"
LOCAL_INPUT_SOURCE_NAME = OWNER_NAME

# =========================
# 🎙️ HOST MODE / ANFITRIÃ
# =========================

HOST_MODE_ENABLED = False
HOST_SEND_TO_CHAT = False

# "autonomous" = lê o chat sozinho por tick/cooldown.
# "read_response" = só lê e responde quando você pedir pelo comando /host read.
HOST_MODE_KIND = os.getenv("HOST_MODE_KIND", "autonomous")

HOST_CHAT_LOG_PATH = "data/chat/live_chat.txt"

OWNER_USERS = [
    "natan_anile"
]

BOT_USERS = [
    "neitanbot",
    "diana"
]

HOST_COOLDOWN_SECONDS = 10
HOST_IDLE_SECONDS = 60

HOST_MAX_LINES_READ = 80
HOST_MAX_CANDIDATES = 15
HOST_MAX_RESPONSE_CHARS = 180

HOST_MIN_MESSAGE_LENGTH = 2

HOST_IGNORE_PREFIXES = [
    "!",
    "/",
    "."
]

# Evita a Diana responder a mesma pessoa sem parar
HOST_USER_COOLDOWN_SECONDS = 25

# Evita puxar assunto infinitamente se ninguém falar nada
HOST_IDLE_STREAK_LIMIT = 2

HOST_DEBUG = True


# =========================
# 🧠 MEMÓRIA LONGA / MEM0
# =========================

MEM0_ENABLED = os.getenv("MEM0_ENABLED", "true").lower() == "true"
MEM0_USER_ID = os.getenv("MEM0_USER_ID", "natan")
MEM0_COLLECTION_NAME = os.getenv("MEM0_COLLECTION_NAME", "diana_memories")
MEM0_QDRANT_PATH = os.getenv("MEM0_QDRANT_PATH", "mem0_qdrant")
MEM0_EMBEDDING_DIMS = int(os.getenv("MEM0_EMBEDDING_DIMS", "768"))
MEM0_LLM_MODEL = os.getenv("MEM0_LLM_MODEL", LLM_MODEL)
MEM0_EMBEDDER_MODEL = os.getenv("MEM0_EMBEDDER_MODEL", "nomic-embed-text")
MEM0_OLLAMA_BASE_URL = os.getenv("MEM0_OLLAMA_BASE_URL", "http://localhost:11434")
MEM0_RETRIEVAL_LIMIT = int(os.getenv("MEM0_RETRIEVAL_LIMIT", "3"))

# Ligado por padrão: a Diana salva interações do OWNER na memória longa.
# Para desligar sem editar código: MEM0_AUTO_SAVE_INTERACTIONS=false
MEM0_AUTO_SAVE_INTERACTIONS = os.getenv("MEM0_AUTO_SAVE_INTERACTIONS", "true").lower() == "true"

# Auto-save inteligente: mantém o recurso ligado, mas não chama Mem0 para cumprimento,
# pergunta vazia, zoeira curta ou frase sem valor de memória.
MEM0_AUTO_SAVE_SMART_FILTER = os.getenv("MEM0_AUTO_SAVE_SMART_FILTER", "true").lower() == "true"
MEM0_AUTO_SAVE_MIN_CHARS = int(os.getenv("MEM0_AUTO_SAVE_MIN_CHARS", "8"))
MEM0_DIRECT_IMPORT = os.getenv("MEM0_DIRECT_IMPORT", "true").lower() == "true"
MEM0_DEBUG = os.getenv("MEM0_DEBUG", "false").lower() == "true"


# =========================
# 🧠 CONTEXTO LEVE / DIANA NOVA
# =========================

CONTEXT_PROFILE_PATH = "data/context/short_profile.json"
CONTEXT_SESSION_SUMMARY_PATH = "data/context/session_summary.txt"
CONTEXT_CURRENT_SESSION_PATH = "data/context/current_session.json"

CONVERSATION_MAX_TURNS = 5

OWNER_DISPLAY_NAME = "Natan"
OWNER_CASUAL_NAME = "Neitan"

# Mencionar live/chat só quando o assunto permitir.
ALLOW_LIVE_REFERENCES_WITHOUT_CONTEXT = False


# =========================
# 📚 RECUPERAÇÃO DE CONTEXTO
# =========================

KNOWLEDGE_ROOT_PATH = "data/knowledge"
STYLE_DICTIONARY_PATH = "data/style_dictionaries"
STYLE_RETRIEVAL_LIMIT = 1
KNOWLEDGE_RETRIEVAL_LIMIT = 4

# =========================
# 🧩 DIANA 0.4 — MODELOS AUXILIARES
# =========================

PROJECT_VERSION = "0.5.1"

# Os modelos auxiliares ficam DESATIVADOS por padrão.
# Quando forem ativados, use outra instância do Ollama/porta para poder
# separar GPU (modelo principal) e CPU (planner/resumidor).
AUXILIARY_LLM_ENABLED = False
AUXILIARY_LLM_URL = os.getenv("AUXILIARY_LLM_URL", "http://localhost:11435/api/generate")
AUXILIARY_LLM_MODEL = os.getenv("AUXILIARY_LLM_MODEL", "qwen2.5:1.5b-instruct")
AUXILIARY_LLM_KEEP_ALIVE = os.getenv("AUXILIARY_LLM_KEEP_ALIVE", "0")
AUXILIARY_LLM_TIMEOUT = int(os.getenv("AUXILIARY_LLM_TIMEOUT", "300"))
AUXILIARY_LLM_NUM_CTX = int(os.getenv("AUXILIARY_LLM_NUM_CTX", "8192"))

# Query Planner: interpreta somente a CONSULTA. Não responde como Diana.
QUERY_PLANNER_ENABLED = False
QUERY_PLANNER_TEMPERATURE = float(os.getenv("QUERY_PLANNER_TEMPERATURE", "0.0"))
QUERY_PLANNER_MAX_TOKENS = int(os.getenv("QUERY_PLANNER_MAX_TOKENS", "260"))

# Resumidor episódico: roda apenas quando acumula turnos suficientes.
SESSION_SUMMARIZER_ENABLED = False
SESSION_SUMMARIZER_TRIGGER_TURNS = int(os.getenv("SESSION_SUMMARIZER_TRIGGER_TURNS", "10"))
SESSION_SUMMARIZER_BATCH_TURNS = int(os.getenv("SESSION_SUMMARIZER_BATCH_TURNS", "5"))
SESSION_SUMMARIZER_MAX_TOKENS = int(os.getenv("SESSION_SUMMARIZER_MAX_TOKENS", "700"))
SESSION_SUMMARIZER_STATE_PATH = "data/context/episodic_summary.json"
SESSION_SUMMARIZER_TEXT_PATH = "data/context/episodic_summary.txt"
