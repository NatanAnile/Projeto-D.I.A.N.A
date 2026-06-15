import numpy as np
import torch
import sounddevice as sd
import time

class SileroVAD:
    def __init__(self, sample_rate=16000):
        self.sample_rate = sample_rate

        # carrega modelo Silero VAD
        self.model, utils = torch.hub.load(
            repo_or_dir='snakers4/silero-vad',
            model='silero_vad',
            trust_repo=True
        )

        self.get_speech_timestamps = utils[0]

    def record(self, max_duration=10):
        print("🎤 aguardando fala...")

        audio_buffer = []
        silence_counter = 0
        speaking = False

        chunk_duration = 0.32
        chunk_size = int(self.sample_rate * chunk_duration)

        for _ in range(int(max_duration / chunk_duration)):

            chunk = sd.rec(chunk_size,
                           samplerate=self.sample_rate,
                           channels=1,
                           dtype='float32')

            sd.wait()
            chunk = chunk.squeeze()

            audio_buffer.append(chunk)

            # VAD score
            speech_prob = self.model(torch.tensor(chunk), self.sample_rate).item()

            if speech_prob > 0.5:
                speaking = True
                silence_counter = 0
            else:
                if speaking:
                    silence_counter += 1

            # para quando detectar silêncio após fala
            if speaking and silence_counter > 6:
                break

        audio = np.concatenate(audio_buffer)

        # remove silêncio final leve
        audio = audio.astype(np.float32)

        print("🎤 fala capturada")
        return audio, self.sample_rate