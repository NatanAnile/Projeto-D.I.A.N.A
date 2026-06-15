# -*- coding: utf-8 -*-

# =========================
# 🎤 PARAKEET TAGARELA STT (ONNX)
# =========================

import os
import re
import time
import tempfile
from pathlib import Path

import numpy as np
import scipy.io.wavfile as wav
from scipy.signal import resample_poly

from stt.stt_postprocessor import postprocess_stt_text

from config import (
    PARAKEET_MODEL_REPO,
    PARAKEET_MODEL_PATH,
    PARAKEET_AUTO_DOWNLOAD,
    PARAKEET_LANGUAGE,
    PARAKEET_ONNX_PROVIDER,
    DEBUG_STT
)


class ParakeetSTT:

    def __init__(self):

        self.model = None
        self.model_path = Path(PARAKEET_MODEL_PATH)
        self.language = PARAKEET_LANGUAGE or "pt"
        self.provider = PARAKEET_ONNX_PROVIDER or "auto"

        self._load_model()

    # =========================
    # 📦 LOAD
    # =========================

    def _ensure_model_path(self):

        if self.model_path.exists():
            return self.model_path

        if not PARAKEET_AUTO_DOWNLOAD:
            raise FileNotFoundError(
                "Modelo Parakeet não encontrado em "
                + str(self.model_path)
                + ". Baixe manualmente ou ative PARAKEET_AUTO_DOWNLOAD=True no config.py."
            )

        print("⬇️ Baixando Parakeet TAGARELA ONNX pelo Hugging Face Hub...")

        try:
            from huggingface_hub import snapshot_download
        except Exception as erro:
            raise RuntimeError(
                "huggingface_hub não está instalado. Instale com: pip install huggingface_hub"
            ) from erro

        try:
            snapshot_download(
                repo_id=PARAKEET_MODEL_REPO,
                local_dir=str(self.model_path),
                local_dir_use_symlinks=False
            )
        except TypeError:
            # Compatibilidade com versões novas/antigas do huggingface_hub.
            snapshot_download(
                repo_id=PARAKEET_MODEL_REPO,
                local_dir=str(self.model_path)
            )

        return self.model_path

    def _load_model(self):

        model_path = self._ensure_model_path()

        try:
            import onnx_asr
        except Exception as erro:
            raise RuntimeError(
                "onnx-asr não está instalado. Instale com: pip install \"onnx-asr[cpu,hub]\""
            ) from erro

        kwargs = {}

        # Nem toda versão do onnx-asr aceita provider/provider_options.
        # Por isso tentamos primeiro com provider e caímos no load simples.
        if self.provider and self.provider.lower() not in ["", "auto"]:
            kwargs["provider"] = self.provider

        try:
            self.model = onnx_asr.load_model(
                "nemo-conformer-tdt",
                str(model_path),
                **kwargs
            )
        except TypeError:
            self.model = onnx_asr.load_model(
                "nemo-conformer-tdt",
                str(model_path)
            )

        print("🎤 STT Parakeet TAGARELA ONNX carregado")

    # =========================
    # 🎚️ ÁUDIO
    # =========================

    def _to_mono_float32(self, audio):

        audio = np.asarray(audio)

        if audio.ndim > 1:
            audio = np.mean(audio, axis=1)

        audio = audio.astype(np.float32, copy=False)

        if audio.size == 0:
            return audio

        peak = float(np.max(np.abs(audio)))

        if peak > 1.0:
            audio = audio / peak

        return audio

    def _resample_to_16k(self, audio, sample_rate):

        sample_rate = int(sample_rate or 16000)

        if sample_rate == 16000:
            return audio, 16000

        gcd = np.gcd(sample_rate, 16000)
        up = 16000 // gcd
        down = sample_rate // gcd

        audio = resample_poly(audio, up, down).astype(np.float32)

        return audio, 16000

    def _write_temp_wav(self, audio, sample_rate):

        audio = self._to_mono_float32(audio)
        audio, sample_rate = self._resample_to_16k(audio, sample_rate)

        peak = float(np.max(np.abs(audio))) if audio.size else 0.0

        if peak <= 0.001:
            return None

        audio = np.clip(audio, -1.0, 1.0)
        audio_i16 = (audio * 32767.0).astype(np.int16)

        tmp = tempfile.NamedTemporaryFile(
            prefix="diana_parakeet_",
            suffix=".wav",
            delete=False
        )

        tmp_path = tmp.name
        tmp.close()

        wav.write(tmp_path, sample_rate, audio_i16)

        return tmp_path

    # =========================
    # 🧹 LIMPEZA / ANTI-LIXO
    # =========================

    def _extract_text(self, result):

        if result is None:
            return ""

        if isinstance(result, str):
            return result

        if isinstance(result, dict):
            for key in ["text", "transcript", "transcription", "result"]:
                value = result.get(key)
                if value:
                    return str(value)

        if isinstance(result, (list, tuple)):
            parts = []
            for item in result:
                parts.append(self._extract_text(item))
            return " ".join(part for part in parts if part)

        return str(result)

    def _clean_text(self, text):

        text = str(text or "").strip()
        text = re.sub(r"\s+", " ", text)
        text = text.strip(" \t\r\n\"'")

        # Remove marcações comuns de transcritores/legendas.
        text = re.sub(r"\[(silence|silêncio|noise|ruído|music|música)\]", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\((silence|silêncio|noise|ruído|music|música)\)", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s+", " ", text).strip()

        return text

    def _looks_like_garbage(self, text):

        text = str(text or "").strip()
        lower = text.lower()

        if len(lower) < 2:
            return True

        blocked = {
            "legendas pela comunidade amara.org",
            "inscreva-se no canal",
            "obrigado por assistir",
            "fim",
            "silêncio",
            "silencio"
        }

        if lower in blocked:
            return True

        compact = re.sub(r"\W+", "", lower)

        if len(compact) >= 8 and len(set(compact)) <= 2:
            return True

        return False

    # =========================
    # 🗣️ TRANSCRIÇÃO
    # =========================

    def transcribe(self, audio, sample_rate=16000):

        tmp_path = None
        started = time.time()

        try:
            tmp_path = self._write_temp_wav(audio, sample_rate)

            if not tmp_path:
                return ""

            result = self.model.recognize(tmp_path, language=self.language)
            text = self._clean_text(self._extract_text(result))
            text = postprocess_stt_text(text)

            if self._looks_like_garbage(text):
                return ""

            if DEBUG_STT:
                elapsed = time.time() - started
                print(f"🎤 Parakeet STT: {elapsed:.2f}s → {text}")

            return text

        except Exception as erro:
            print("⚠️ Erro no STT Parakeet:", erro)
            return ""

        finally:
            if tmp_path:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    def shutdown(self):

        self.model = None
