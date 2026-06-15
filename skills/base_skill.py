# -*- coding: utf-8 -*-

# =========================
# 🧩 BASE SKILL
# =========================

import time
import random
from dataclasses import dataclass
from typing import Optional


@dataclass
class SkillContext:

    skill_name: str
    min_cooldown: int = 60
    max_cooldown: int = 120
    user_context: Optional[object] = None
    conversation: Optional[object] = None


class BaseSkill:

    def __init__(self, context):

        self.context = context
        self.last_used = 0
        self.current_cooldown = random.randint(
            self.context.min_cooldown,
            self.context.max_cooldown
        )

    def can_use(self):

        now = time.time()

        return now - self.last_used >= self.current_cooldown

    def mark_used(self, cooldown=None):

        self.last_used = time.time()

        if cooldown is not None:
            self.current_cooldown = cooldown
        else:
            self.current_cooldown = random.randint(
                self.context.min_cooldown,
                self.context.max_cooldown
            )

    def get_context(self, user_text="", conversation=None):

        return None