import os
import tempfile
import numpy as np
import scipy.io.wavfile as wav

from faster_whisper import WhisperModel
from config import WHISPER_MODEL, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE
from stt.stt_postprocessor import postprocess_stt_text


class WhisperSTT:

    def __init__(self):

        print("🔊 Whisper carregando...")

        self.model = WhisperModel(
            WHISPER_MODEL,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE
        )

        print(f"🔊 Whisper carregado: {WHISPER_MODEL} / {WHISPER_DEVICE} / {WHISPER_COMPUTE_TYPE}")

    # =========================
    # 🧼 CORREÇÃO DE TERMOS
    # =========================

    def corrigir_termos(self, text):

        correcoes = {
            "Pasquinha": "Diana",
            "pasquinha": "Diana",
            "Tascuinha": "Diana",
            "tascuinha": "Diana",
            "Diana": "Diana",
            "diana": "Diana",
            "Neiton": "Neitan",
            "neiton": "Neitan",
            "Nathan": "Natan",
            "nathan": "Natan"
        }

        for errado, certo in correcoes.items():
            text = text.replace(errado, certo)

        return text

    def transcribe(self, audio, fs):

        if audio is None:
            return ""

        if len(audio) < fs * 0.3:
            return ""

        audio = np.asarray(audio, dtype=np.float32)

        volume_medio = np.mean(np.abs(audio))

        if volume_medio < 0.003:
            return ""

        tmp_path = None

        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
                wav.write(tmp_path, fs, audio)

            segments, info = self.model.transcribe(
                tmp_path,
                language="pt",
                task="transcribe",
                beam_size=5,
                best_of=5,
                temperature=0.0,
                vad_filter=False,
                condition_on_previous_text=False,
                initial_prompt=(
                    "Transcrição em português do Brasil. "
                    "O usuário fala sobre jogos, Super Metroid, speedrun, randomizer, "
                    "wall jump, shinespark, Chrono Trigger, Zelda, Angra, música, "
                    "programação, inteligência artificial e lives. "
                    "O nome da assistente é Diana. "
                    "O nome do usuário é Natan, também chamado de Neitan."
                )
            )

            text = " ".join([seg.text for seg in segments]).strip()

            if self._is_noise(text):
                return ""

            return postprocess_stt_text(self.corrigir_termos(text))

        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except:
                    pass

    def _is_noise(self, text):

        if not text:
            return True

        text = text.strip()

        if len(text) < 3:
            return True

        lixo_comum = [
            "legendas pela comunidade",
            "obrigado por assistir",
            "inscreva-se",
            "tchau"
        ]

        text_low = text.lower()

        for lixo in lixo_comum:
            if lixo in text_low:
                return True

        return False