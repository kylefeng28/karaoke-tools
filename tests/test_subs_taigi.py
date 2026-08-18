import pytest

from karaoke_tools.subs import format_k_syllable, format_line, to_ssa_file
from karaoke_tools.timing import TimedWord, TimedSyllable, Line


type WordSyllable = tuple[str, list[tuple[str, int]]]
def make_line(start: float, word_syllables: list[WordSyllable]):
    t_s = start  # time in seconds so far

    def make_syl(text: str, duration_cs: float):
        nonlocal t_s
        start_s = t_s
        end_s = start_s + duration_cs / 100
        t_s = end_s
        return TimedSyllable(text, mode='start_end', timed=True, start=start_s, end=end_s)

    tokens = []
    for (word, word_syls) in word_syllables:
        syls = [make_syl(syl, dur) for (syl, dur) in word_syls]
        tokens.append(TimedWord(word, syls, syl_joiner='-'))

    return Line(tokens, start=start, end=t_s)


# ------------------------------------------------------------------------------
# Japanese
# ------------------------------------------------------------------------------
TIMED_LINES = [
    make_line(1.07, [
        ('つよく', [('つ', 41), ('よ', 32), ('く', 109)]),
    ]),
]

EXPECTED_LINES = [
    r'{\k41}つ-{\k32}よ-{\k109}く',
]

EXPECTED_TIMINGS = [
    ('0:00:01.07', '0:00:02.89'),
]

# ------------------------------------------------------------------------------
# Full .ass file tests
# ------------------------------------------------------------------------------
def assert_format_line(timed_lines, expected_lines):
    for i in range(len(timed_lines)):
        line = timed_lines[i]
        assert format_line(line) == expected_lines[i]

def test_format_line():
    assert_format_line(TIMED_LINES, EXPECTED_LINES)

# ------------------------------------------------------------------------------
# Full .ass file tests
# ------------------------------------------------------------------------------
COMMENT_LINE = r'Comment: 0,0:00:00.00,0:00:00.00,Sample KM [Up],,0,0,0,template pre-line all keeptags,!retime("line",$start < 900 and -$start or -900,200)!{!$start < 900 and "\\k" .. ($start/10) or "\\k90"!\fad(!$start < 900 and $start or 300!,200)}'

@pytest.mark.parametrize("template_file, style", [
    pytest.param('./templates/plain.ass', 'Default'),
    pytest.param('./templates/karaoke_mugen_template.ass', 'Sample KM [Up]'),
])
def test_to_ssa_file(template_file: str, style: str):
    expected = 'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'

    if template_file == './templates/karaoke_mugen_template.ass':
        expected += COMMENT_LINE + '\n'

    for i in range(len(EXPECTED_LINES)):
        start, end = EXPECTED_TIMINGS[i]
        line = EXPECTED_LINES[i]
        expected += f'Dialogue: 0,{start},{end},{style},,0,0,0,karaoke,{line}\n'

    subs = to_ssa_file(TIMED_LINES, template_file=template_file).to_string('ass')

    subs = subs.split('[Events]\n')[1]

    assert subs == expected
