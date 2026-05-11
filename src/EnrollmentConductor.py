import os
import re
import random
import numpy as np
from AppLogger import AppLogger

_AGE_WORDS = {
    'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
    'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14,
    'fifteen': 15, 'sixteen': 16, 'seventeen': 17, 'eighteen': 18,
    'nineteen': 19, 'twenty': 20, 'thirty': 30, 'forty': 40,
    'fifty': 50, 'sixty': 60, 'seventy': 70, 'eighty': 80, 'ninety': 90,
}

_OPENING_QUESTION = "What's your favorite cartoon character or TV show?"

_FOLLOWUP_TEMPLATES = [
    "That's so cool! What do they do?",
    "Who's your favorite character besides them?",
    "Why do you like that?",
    "What's the best part about it?",
    "Tell me something else you love!",
    "What's your favorite game to play?",
    "What do you like to do after school?",
    "What's your favorite food?",
]

_SAMPLES_NEEDED = 6
_AGE_ASK_AFTER = 2  # ask age after this many samples collected


class EnrollmentConductor:
    """Drives conversational voice enrollment for one new speaker.

    Collects voice samples through natural conversation, captures the speaker's age,
    then saves a .npz profile. _next_prompt() is the Phase 4 seam — Phase 3 uses
    hardcoded templates; Phase 4 replaces that one method body with a Claude call.
    """

    def __init__(self, name: str, pronoun: str, ask_claude=None, tts_name: str = None):
        with AppLogger.enter('EnrollmentConductor.__init__') as log:
            self.name = name
            self.tts_name = tts_name if tts_name is not None else name
            self.pronoun = pronoun
            self.age: int | None = None
            self._samples: list = []
            self._question_history: list = []
            self._age_asked = False
            self._followups = list(_FOLLOWUP_TEMPLATES)
            self._ask_claude = ask_claude  # callable(last_answer, conductor) -> str; Phase 4 seam
            random.shuffle(self._followups)
            log.log('INFO', f'enrollment started name={name!r} pronoun={pronoun!r} claude={"yes" if ask_claude else "no"}')

    def greeting(self) -> str:
        with AppLogger.enter('EnrollmentConductor.greeting') as log:
            msg = (
                f"Hi {self.tts_name}! I'm Jarvis. I want to learn your voice so I can "
                f"recognize you. I'm going to ask you a few questions — just talk naturally. "
                f"{_OPENING_QUESTION}"
            )
            self._question_history.append(msg)
            log.log('DEBUG', 'greeting prepared')
            return msg

    def add_sample(self, embedding: np.ndarray) -> None:
        with AppLogger.enter('EnrollmentConductor.add_sample') as log:
            self._samples.append(embedding)
            log.log('INFO', f'sample added total={len(self._samples)}/{_SAMPLES_NEEDED}')

    def try_parse_age(self, text: str) -> bool:
        """Try to extract an age from text. Returns True if age was found and stored."""
        with AppLogger.enter('EnrollmentConductor.try_parse_age') as log:
            t = text.lower()
            for word in re.findall(r'[a-z]+', t):
                if word in _AGE_WORDS:
                    self.age = _AGE_WORDS[word]
                    log.log('INFO', f'age parsed from word {word!r} → {self.age}')
                    return True
            match = re.search(r'\b([1-9][0-9]?)\b', t)
            if match:
                candidate = int(match.group(1))
                if 1 <= candidate <= 99:
                    self.age = candidate
                    log.log('INFO', f'age parsed from digits → {self.age}')
                    return True
            log.log('DEBUG', 'no age found in transcript')
            return False

    def next_prompt(self, last_answer: str) -> str:
        with AppLogger.enter('EnrollmentConductor.next_prompt') as log:
            prompt = self._next_prompt(last_answer)
            self._question_history.append(prompt)
            log.log('DEBUG', 'next prompt prepared')
            return prompt

    def _next_prompt(self, last_answer: str) -> str:
        # Phase 4 seam: use Claude if available
        if self._ask_claude:
            result = self._ask_claude(last_answer, self)
            if result:
                return result
        # Phase 3 hardcoded templates — also serve as fallback when Claude is unavailable
        if not self._age_asked and len(self._samples) >= _AGE_ASK_AFTER:
            self._age_asked = True
            return f"That's awesome! How old are you, {self.tts_name}?"
        if self._followups:
            return self._followups.pop()
        return "Tell me one more thing you really love!"

    def is_complete(self) -> bool:
        return len(self._samples) >= _SAMPLES_NEEDED and self.age is not None

    def needs_age(self) -> bool:
        return self.age is None and len(self._samples) >= _SAMPLES_NEEDED

    def save(self, profiles_dir: str) -> str:
        with AppLogger.enter('EnrollmentConductor.save') as log:
            os.makedirs(profiles_dir, exist_ok=True)
            avg_emb = np.mean(self._samples, axis=0)
            path = os.path.join(profiles_dir, f'{self.name.lower()}.npz')
            np.savez(
                path,
                embedding=avg_emb,
                name=np.str_(self.name),
                age=np.int32(self.age if self.age is not None else 0),
                pronoun=np.str_(self.pronoun),
            )
            log.log('INFO', f'profile saved path={path!r} name={self.name!r} age={self.age}')
            return path
