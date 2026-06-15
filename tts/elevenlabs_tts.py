# =========================
# 🔊 ELEVENLABS TTS
# =========================

import os
import wave
import requests

from config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, ELEVENLABS_MODEL


class ElevenLabsTTS:

    def __init__(self):

        self.api_key = ELEVENLABS_API_KEY
        self.voice_id = ELEVENLABS_VOICE_ID
        self.model = ELEVENLABS_MODEL

        os.makedirs("outputs", exist_ok=True)

    def speak(self, text):

        if not self.api_key:
            raise Exception("ELEVENLABS_API_KEY não configurada")

        if not self.voice_id:
            raise Exception("ELEVENLABS_VOICE_ID não configurado")

        output_path = os.path.join("outputs", "output_elevenlabs.wav")

        url = (
            f"https://api.elevenlabs.io/v1/text-to-speech/"
            f"{self.voice_id}?output_format=pcm_24000"
        )

        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        payload = {
            "text": text,
            "model_id": self.model,
            "voice_settings": {
                "stability": 0.45,
                "similarity_boost": 0.75,
                "style": 0.35,
                "use_speaker_boost": True
            }
        }

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=60
        )

        if response.status_code != 200:
            raise Exception(f"Erro ElevenLabs: {response.status_code} - {response.text}")

        pcm_data = response.content

        with wave.open(output_path, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(24000)
            wav_file.writeframes(pcm_data)

        return output_path