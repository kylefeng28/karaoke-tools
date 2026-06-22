import re
import pysubs2
from dataclasses import dataclass, field
from utils import convert_to_hiragana

# Matches both \k and \kf timing tags (with optional space before the number); group 1 = timing, group 2 = syllable text
K_TOKEN_RE = re.compile(r'\{\\kf? ?(\d+)\}([^{]*)')


# Represents a syllable marked with \k tags
@dataclass
class TimedSyllable:
    text: str
    timing: int = None

    def __str__(self):
        return f"{{{self.text}, {self.timing}}}"


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

    def detailed_str(self):
        syls = [s.text for s in self.syllables]
        timings = [str(s.timing) for s in self.syllables]
        timings_str = ' (' + ','.join(timings) + ')'
        return '-'.join(syls) + timings_str

    def convert_hiragana(self):
        is_whole_word = len(self.syllables) == 1
        converted = convert_to_hiragana(self.text, is_whole_word)
        self.text = converted

        for syl in self.syllables:
            converted = convert_to_hiragana(syl.text, is_whole_word)
            syl.text = converted


# Represents a line of words
@dataclass
class Line:
    words: TimedWord = field(default_factory=list)

def parse_k_timing(line: str) -> list[TimedWord]:
    """
    Parse an ASS karaoke timing line into a list of TimedWord objects.

    Format: {\\kN}text  where N is duration in centiseconds.
    - A trailing space on `text` marks a word boundary.

    Each TimedWord has:
      .text       — the full word string (e.g. 'watashi')
      .syllables  — list of TimedSyllable(text, cs) in order
    """
    tokens = [
        (int(m.group(1)), m.group(2))
        for m in K_TOKEN_RE.finditer(line)
    ]

    words: list[TimedWord] = []
    current: list[TimedSyllable] = []

    for cs, raw in tokens:
        ends_word = raw.endswith(' ')
        text = raw.rstrip(' ')

        if text:
            current.append(TimedSyllable(text.strip(), cs))

        if ends_word and current:
            word_text = "".join(s.text for s in current)
            words.append(TimedWord(word_text, current))
            current = []

    # Flush final word (no trailing space on last token)
    if current:
        word_text = "".join(s.text for s in current)
        words.append(TimedWord(word_text, current))

    return words


def read_ass_file(input_file):
    lines = pysubs2.load(input_file)

    for line in lines:
        if line.text.startswith('!'):
            continue

        timed_words = parse_k_timing(line.text)
        for word in timed_words:
            word.convert_hiragana()
            print(word, end='\t')

        print()
