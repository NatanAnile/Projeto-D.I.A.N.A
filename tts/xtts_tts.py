import os
import re
import wave
from TTS.api import TTS


class XTTS:

    def __init__(self):

        self.tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=True)

        os.makedirs("outputs", exist_ok=True)

    # =========================
    # ✂️ QUEBRA DE TEXTO PARA TTS
    # =========================

    def dividir_texto(self, text, limite=190):

        frases = re.split(r"(?<=[.!?])\s+", text)

        partes = []
        atual = ""

        for frase in frases:

            frase = frase.strip()

            if not frase:
                continue

            if len(atual) + len(frase) + 1 <= limite:

                if atual:
                    atual += " " + frase
                else:
                    atual = frase

            else:

                if atual:
                    partes.append(atual)

                if len(frase) <= limite:
                    atual = frase
                else:
                    partes.append(frase[:limite])
                    atual = frase[limite:]

        if atual:
            partes.append(atual)

        return partes

    # =========================
    # 🔊 JUNTAR ÁUDIOS
    # =========================

    def juntar_wavs(self, arquivos, output_path):

        with wave.open(output_path, "wb") as saida:

            primeiro = True

            for arquivo in arquivos:

                with wave.open(arquivo, "rb") as entrada:

                    if primeiro:

                        saida.setparams(entrada.getparams())
                        primeiro = False

                    saida.writeframes(entrada.readframes(entrada.getnframes()))

    def speak(self, text):

        output_path = os.path.join("outputs", "output.wav")

        partes = self.dividir_texto(text)

        arquivos_temp = []

        for i, parte in enumerate(partes):

            temp_path = os.path.join("outputs", f"output_part_{i}.wav")

            self.tts.tts_to_file(
                text=parte,
                file_path=temp_path,
                speaker_wav="voices/reference.wav",
                language="pt"
            )

            arquivos_temp.append(temp_path)

        if len(arquivos_temp) == 1:

            os.replace(arquivos_temp[0], output_path)

        else:

            self.juntar_wavs(arquivos_temp, output_path)

            for arquivo in arquivos_temp:

                try:
                    os.remove(arquivo)
                except:
                    pass

        return output_path