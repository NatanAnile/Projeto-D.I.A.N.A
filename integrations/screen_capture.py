# -*- coding: utf-8 -*-

# =========================
# 👁️ SCREEN CAPTURE
# =========================

from pathlib import Path

import mss
from PIL import Image

from config import SCREENSHOT_PATH, SCREENSHOT_FILE_NAME, SCREENSHOT_MONITOR


def capturar_tela():

    try:

        folder = Path(SCREENSHOT_PATH)
        folder.mkdir(parents=True, exist_ok=True)

        file_path = folder / SCREENSHOT_FILE_NAME

        with mss.mss() as sct:

            monitores = sct.monitors

            if SCREENSHOT_MONITOR < 1 or SCREENSHOT_MONITOR >= len(monitores):

                return None, (
                    "Monitor inválido. "
                    + "Monitores disponíveis: "
                    + str(len(monitores) - 1)
                )

            monitor = monitores[SCREENSHOT_MONITOR]

            screenshot = sct.grab(monitor)

            image = Image.frombytes(
                "RGB",
                screenshot.size,
                screenshot.rgb
            )

            image.save(file_path)

        return str(file_path), None

    except Exception as e:

        return None, str(e)