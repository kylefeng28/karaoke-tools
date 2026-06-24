from dataclasses import dataclass, field
from typing import Literal
from cjk_utils import join_tokens

# Represents a syllable marked with \k tags
@dataclass
class TimedSyllable:
    text:      str
    mode:      Literal['start_end', 'duration']
    timed:     bool  = False
    duration:  int   = None
    start:     float = None
    end:       float = None

    @classmethod
    def from_duration(cls, text: str, duration: int):
        return cls(text, mode='duration', duration=duration)

    def __str__(self):
        return f"{{{self.text}, {self.duration}}}"

    def preview(self):
        return self.text

# Represents a word with its k-timed syllables
@dataclass
class TimedWord:
    text: str
    syllables: list[TimedSyllable] = field(default_factory=list)

    def add_syllable(self, syllable):
        self.syllables.append(syllable)

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

# Represents a line of words
@dataclass
class Line:
    tokens:   list[TimedWord | TimedSyllable] = field(default_factory=list)
    start:   float = None
    end:     float = None

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
            if isinstance(token, TimedWord):
                syllables.append(token.syllables)
            elif isinstance(token, TimedSyllable):
                syllables.append(token)
        return syllables

    def get_syllable(self, i):
        return self.get_syllables()[i]
