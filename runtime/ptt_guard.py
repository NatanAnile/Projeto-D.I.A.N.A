# -*- coding: utf-8 -*-

# =========================
# 🎛️ PUSH-TO-TALK GUARD
# =========================

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PTTStatus:
    key_name: str
    key_down: bool
    was_down: bool
    lockout_until_release: bool
    started_count: int
    ignored_count: int


class PushToTalkGuard:
    """Controle de borda para Push-to-Talk.

    O STT só pode iniciar em uma nova pressão da tecla (rising edge).
    Se a biblioteca `keyboard` ou o Windows ficarem reportando a tecla como
    presa depois da gravação, o guard entra em lockout e ignora STT até a tecla
    aparecer como solta. Isso preserva o input de texto do terminal.
    """

    def __init__(self, key_name="right ctrl"):
        self.key_name = str(key_name or "right ctrl")
        self.was_down = False
        self.lockout_until_release = False
        self.started_count = 0
        self.ignored_count = 0

    def should_start(self, is_down: bool) -> bool:
        is_down = bool(is_down)

        if self.lockout_until_release:
            if not is_down:
                self.lockout_until_release = False
                self.was_down = False
            else:
                self.ignored_count += 1
            return False

        if is_down and not self.was_down:
            self.was_down = True
            self.started_count += 1
            return True

        if not is_down:
            self.was_down = False

        return False

    def finish_recording(self, is_still_down: bool) -> bool:
        """Finaliza ciclo de STT.

        Retorna True se precisou ativar lockout por tecla ainda pressionada.
        """
        is_still_down = bool(is_still_down)
        if is_still_down:
            self.lockout_until_release = True
            self.was_down = True
            return True
        self.was_down = False
        self.lockout_until_release = False
        return False

    def reset(self) -> None:
        self.was_down = False
        self.lockout_until_release = False
        self.ignored_count = 0

    def status(self, is_down: bool = False) -> PTTStatus:
        return PTTStatus(
            key_name=self.key_name,
            key_down=bool(is_down),
            was_down=bool(self.was_down),
            lockout_until_release=bool(self.lockout_until_release),
            started_count=int(self.started_count),
            ignored_count=int(self.ignored_count),
        )
