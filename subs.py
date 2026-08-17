import re
import pysubs2
from cjk_utils import convert_to_hiragana
from timing import TimedWord, TimedSyllable, Line
from utils import _fmt_time, _fmt_speed

# Matches both \k and \kf timing tags (with optional space before the number); group 1 = timing, group 2 = syllable text
K_TOKEN_RE = re.compile(r'\{\\kf? ?(\d+)\}([^{]*)')

_ASS_HEADER = """\
[Script Info]
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,80,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,3,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


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


def export_ass(lines: list[Line], out_path: str):
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(_ASS_HEADER)
        for ln in lines:
            text, last = '', ln.get_start()
            for tok in ln.tokens:
                for syl in tok.get_syllables():
                    if syl.timed:
                        gap = syl.start - last
                        extra = 0.0
                        if gap > 0.005:
                            text += '{\\kf%d}' % round(gap * 100)
                        text += '{\\kf%d}%s' % (round((syl.end - syl.start + extra) * 100), syl.preview())
                        last = syl.end
                    else:
                        text += syl.preview()

                # Add space between words
                if tok.get_type() == 'word':
                    text += ' '

            f.write(f"Dialogue: 0,{_fmt_time(ln.get_start())},{_fmt_time(ln.get_end())},"
                    f"Default,,0,0,0,karaoke,{text}\n")
