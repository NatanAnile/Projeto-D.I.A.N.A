# =========================
# 🔊 TTS MANAGER
# =========================

from config import TTS_PROVIDER, TTS_FALLBACK

from tts.xtts_tts import XTTS
from tts.elevenlabs_tts import ElevenLabsTTS


class TTSManager:

    def __init__(self):

        self.xtts = XTTS()
        self.elevenlabs = ElevenLabsTTS()

        self.provider = TTS_PROVIDER
        self.fallback = TTS_FALLBACK

        print(f"🔊 TTS principal: {self.provider}")

    def speak(self, text):

        try:

            if self.provider == "elevenlabs":
                return self.elevenlabs.speak(text)

            return self.xtts.speak(text)

        except Exception as e:

            print(f"⚠️ TTS principal falhou: {e}")

            if self.fallback == "xtts":
                print("🔁 Usando XTTS local como fallback")
                return self.xtts.speak(text)

            return None