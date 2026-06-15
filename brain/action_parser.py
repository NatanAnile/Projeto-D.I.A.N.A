# -*- coding: utf-8 -*-

# =========================
# 🎬 ACTION PARSER
# =========================

import re


class ActionParser:

    def parse(self, raw_text):

        raw_text = str(raw_text or "").strip()

        result = {
            "speaking": "",
            "emotion": "",
            "raw": raw_text
        }

        if not raw_text:
            return result

        emotion_match = re.search(
            r"Action\s*:\s*Emotion\s*:\s*([A-Za-zÀ-ÿ_ -]+)",
            raw_text,
            flags=re.IGNORECASE
        )

        if emotion_match:
            result["emotion"] = emotion_match.group(1).strip()

        patterns = [
            r"<\s*Action\s*:\s*Speaking\s*:\s*(.*?)\s*>",
            r"<\s*Action\s*:\s*Speaking\s*>\s*(.*?)\s*<\s*/\s*Action\s*:\s*Speaking\s*>",
            r"Action\s*:\s*Speaking\s*:\s*(.*)"
        ]

        for pattern in patterns:
            match = re.search(pattern, raw_text, flags=re.IGNORECASE | re.DOTALL)
            if match:
                result["speaking"] = match.group(1).strip()
                return result

        # Fallback: se o modelo desobedecer o formato, usa a resposta bruta.
        text = raw_text
        text = re.sub(r"Action\s*:\s*Emotion\s*:\s*[A-Za-zÀ-ÿ_ -]+", "", text, flags=re.IGNORECASE)
        text = text.strip()

        result["speaking"] = text
        return result
