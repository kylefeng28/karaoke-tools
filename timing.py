from dataclasses import dataclass, field
from typing import Literal
from cjk_utils import join_tokens

class Token:
    def get_type():
        pass

    def get_syllables():
        pass

@dataclass
class TimedSyllable(Token):
    """
    Represents a syllable marked with k-timed tags (\k or \kf).
    Could be a standalone syllable or part of a TimedWord
    """
    text:      str
    mode:      Literal['start_end', 'duration']
    timed:     bool  = False
    duration:  int   = None
    start:     float = None
    end:       float = None

    syl_idx:   int = None   # represents syllable index within line
    word_info: tuple['TimedWord', int] | None = None # (word, syl_idx) where syl_idx represents syllable index within word

    @classmethod
    def from_duration(cls, text: str, duration: int):
        return cls(text, mode='duration', duration=duration)

    def __str__(self):
        return f"{{{self.text}, {self.duration}}}"

    def preview(self):
        return self.text

    def get_type(self):
        return 'syllable'

    def get_syllables(self):
        return [self]

@dataclass
class TimedWord(Token):
    """
    Represents a word containing TimedSyllables
    """
    text: str
    syllables: list[TimedSyllable] = field(default_factory=list)

    def __post_init__(self):
        for syl_idx, syllable in enumerate(self.syllables):
            syllable.word_info = (self, syl_idx)

    def __str__(self):
        if not self.syllables:
            return self.text
        syls = [s.text for s in self.syllables]
        if ''.join(syls) == self.text:
            return self.text
        return self.text + ' {' + '-'.join(syls) + '}'

    def preview(self):
        return self.text

    def detailed_str(self):
        syls = [s.text for s in self.syllables]
        timings = [str(s.timing) for s in self.syllables]
        timings_str = ' (' + ','.join(timings) + ')'
        return '-'.join(syls) + timings_str

    def get_type(self):
        return 'word'

    def get_syllables(self):
        return self.syllables

@dataclass
class Line:
    """
    Represents a line containing either TimedWords or TimedSyllables
    """
    tokens:  list[TimedWord | TimedSyllable] = field(default_factory=list)
    start:   float = None
    end:     float = None

    def __post_init__(self):
        for syl_idx, syl in enumerate(self.get_syllables()):
            syl.syl_idx = syl_idx

    def get_start(self):
        if self.start:
            return self.start
        if len(self.tokens) > 0:
            return self.tokens[0].start

    def get_end(self):
        if self.end:
            return self.end
        if len(self.tokens) > 0:
            return self.tokens[-1].end

    def preview(self):
        return join_tokens([token.preview() for token in self.tokens])

    def get_syllables(self):
        syllables = []
        for token in self.tokens:
            syllables.extend(token.get_syllables())
        return syllables

    def get_syllable(self, i):
        return self.get_syllables()[i]
