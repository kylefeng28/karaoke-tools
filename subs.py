import re
import pysubs2
from dataclasses import dataclass, field
from utils import convert_to_hiragana
from timing import TimedWord, TimedSyllable, Line

# Matches both \k and \kf timing tags (with optional space before the number); group 1 = timing, group 2 = syllable text
K_TOKEN_RE = re.compile(r'\{\\kf? ?(\d+)\}([^{]*)')


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


def convert_hiragana(word: TimedWord):
    is_whole_word = len(word.syllables) == 1
    converted = convert_to_hiragana(word.text, is_whole_word)
    word.text = converted

    for syl in word.syllables:
        converted = convert_to_hiragana(syl.text, is_whole_word)
        syl.text = converted


def read_ass_file(input_file) -> Line:
    sub_lines = pysubs2.load(input_file)

    lines = []
    for sub_line in sub_lines:
        if sub_line.text.startswith('!'):
            continue

        timed_words = parse_k_timing(sub_line.text)
        lines.append(Line(tokens=timed_words))

    return lines
