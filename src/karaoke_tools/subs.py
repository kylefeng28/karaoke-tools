import re

import pysubs2
from pysubs2 import SSAEvent, SSAFile, make_time

from .cjk_utils import convert_to_hiragana
from .timing import Line, TimedSyllable, TimedWord

# Matches both \k and \kf timing tags (with optional space before the number); group 2 = timing, group 2 = syllable text
K_TOKEN_RE = re.compile(r'(\{\\kf? ?(\d+)\})?([^{\s]*)')  # } to make vim indent formatting happy from unmatched bracket in regex


def parse_k_timing(line: str, line_start: float) -> list[TimedWord]:
    """
    Parse an ASS karaoke timing line into a list of TimedWord objects.

    Format: {\\kN}text  where N is duration in centiseconds.
    - A trailing space on `text` marks a word boundary.

    Each TimedWord has:
      .text       — the full word string (e.g. 'watashi')
      .syllables  — list of TimedSyllable in order
    """
    words: list[TimedWord] = []

    t_s = line_start
    for word_token in line.split():
        current: list[TimedSyllable] = []
        matches = [
            (int(m.group(2)) if m.group(2) else None, m.group(3))
            for m in K_TOKEN_RE.finditer(word_token)
        ]
        for cs, raw in matches:
            text = raw.strip()

            if text:
                if cs:
                    start = t_s
                    end = start + cs / 100
                    t_s = end
                    current.append(TimedSyllable(text, mode='start_end', timed=True, start=start, end=end))
                else:
                    current.append(TimedSyllable(text, mode='start_end', timed=False))

        word_text = "".join(s.text for s in current)
        words.append(TimedWord(word_text, current))
        current = []

    return words


def convert_hiragana(word: TimedWord):
    is_whole_word = len(word.syllables) == 1
    converted = convert_to_hiragana(word.text, is_whole_word)
    word.text = converted

    for syl in word.syllables:
        converted = convert_to_hiragana(syl.text, is_whole_word)
        syl.text = converted


def read_ass_file(input_file) -> list[Line]:
    sub_lines = pysubs2.load(input_file)

    lines = []
    for sub_line in sub_lines:
        if sub_line.text.startswith('!'):
            continue

        line_start = sub_line.start / 1000 # convert from ms to s
        timed_words = parse_k_timing(sub_line.text, line_start)
        lines.append(Line(tokens=timed_words))

    return lines


def format_k_syllable(s: float, text: str) -> str:
    # Return : {\\kN}text  where N is duration in centiseconds.
    return '{\\k%d}%s' % (round(s * 100), text)


def format_line(line: Line) -> str:
    text, last = [], line.get_start()
    for i, tok in enumerate(line.tokens):
        cur_text = []
        for syl in tok.get_syllables():
            if syl.timed:
                gap = syl.start - last
                extra = 0.0
                if gap > 0.005:
                    # TODO: handle gap if there are non-empty syllable joiners
                    # TODO: this usually shouldn't be a problem as gaps are between top-level TimedWord/TimedSyllable tokens
                    # and not in between the individual TimedSyllables of a word
                    cur_text.append(format_k_syllable(s=gap, text=''))
                cur_text.append(format_k_syllable(s=syl.end - syl.start + extra, text=syl.preview()))
                last = syl.end
            else:
                cur_text.append(syl.preview())

        text.append(tok.syl_joiner.join(cur_text))

    return ' '.join(text)


def to_ssa_file(lines: list[Line], template_file: str) -> SSAFile:
    subs = SSAFile.load(template_file)
    style = next(iter(subs.styles.keys()))

    for line in lines:
        text = format_line(line)
        event = SSAEvent(start=make_time(s=line.get_start() or 0), end=make_time(s=line.get_end() or 0),
                         style=style,
                         effect="karaoke",
                         text=text)
        subs.append(event)

    return subs


def export_ass(lines: list[Line], out_path: str, template_file: str) -> str:
    subs = to_ssa_file(lines, template_file)
    subs.save(out_path)
    return out_path
