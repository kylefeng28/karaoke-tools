import pytest

from karaoke_tools.subs import format_k_syllable, format_line, to_ssa_file
from karaoke_tools.timing import TimedWord, TimedSyllable, Line


def test_format_k_syllable():
    assert format_k_syllable(s=1.12, text="") == "{\\k112}"  # gap
    assert format_k_syllable(s=1.12, text="つ") == "{\\k112}つ"
    assert format_k_syllable(s=1.08, text="よ") == "{\\k108}よ"
    assert format_k_syllable(s=1.09, text="く") == "{\\k109}く"

    assert format_k_syllable(s=1.01, text="月") == "{\\k101}月"
    assert format_k_syllable(s=1.02, text="亮") == "{\\k102}亮"

    assert format_k_syllable(s=1.23, text="hello") == "{\\k123}hello"


type WordSyllable = tuple[str, list[tuple[str, int]]]
def make_line(start: float, word_syllables: list[WordSyllable], syl_joiner: str = ''):
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
        tokens.append(TimedWord(word, syls, syl_joiner=syl_joiner))

    return Line(tokens, start=start, end=t_s)


# ------------------------------------------------------------------------------
# Japanese
# ------------------------------------------------------------------------------
TIMED_LINES_JA = [
    make_line(1.07, [
        ('つよく', [('つ', 41), ('よ', 32), ('く', 109)]),
        ('なれる', [('な', 36), ('れ', 36), ('る', 90)]),
        ('理由', [('り', 15), ('ゆ', 21), ('う', 21)]),
        ('を', [('を', 34)]),
        ('知った', [('し', 53), ('っ', 45), ('た', 132)]),
    ]),

    make_line(18.86, [
        ('泥', [('ど', 36), ('ろ', 28)]),
        ('だらけ', [('だ', 41), ('ら', 28), ('け', 36)]),
        ('の', [('の', 94),]),
        ('走馬灯', [('そ', 19), ('う', 13), ('ま', 13), ('と', 26), ('う', 53)]),
        ('に', [('に', 87),]),
        ('酔う', [('よ', 15), ('う', 60),]),
        ('こわばる', [('こ', 21), ('わ', 15), ('ば', 19), ('る', 35)]),
        ('心', [('こ', 27), ('こ', 21), ('ろ', 30)]),
    ]),

    make_line(26.03, [
        ('震える', [('ふ', 34), ('る', 26), ('え', 38), ('る', 26)]),
        ('手', [('て', 26)]),
        ('は', [('は', 94)]),
        ('掴みたい', [('つ', 11), ('か', 14), ('み', 13), ('た', 13), ('い', 23)]),
        ('もの', [('も', 13), ('の', 26)]),
        ('が', [('が', 26)]),
        ('ある', [('あ', 13), ('る', 109)]),
        ('それだけ', [('そ', 21), ('れ', 30), ('だ', 31), ('け', 35)]),
        ('さ', [('さ', 69)]),
    ]),
]

EXPECTED_LINES_JA = [
    r'{\k41}つ{\k32}よ{\k109}く {\k36}な{\k36}れ{\k90}る {\k15}り{\k21}ゆ{\k21}う {\k34}を {\k53}し{\k45}っ{\k132}た',
    r'{\k36}ど{\k28}ろ {\k41}だ{\k28}ら{\k36}け {\k94}の {\k19}そ{\k13}う{\k13}ま{\k26}と{\k53}う {\k87}に {\k15}よ{\k60}う {\k21}こ{\k15}わ{\k19}ば{\k35}る {\k27}こ{\k21}こ{\k30}ろ',
    r'{\k34}ふ{\k26}る{\k38}え{\k26}る {\k26}て {\k94}は {\k11}つ{\k14}か{\k13}み{\k13}た{\k23}い {\k13}も{\k26}の {\k26}が {\k13}あ{\k109}る {\k21}そ{\k30}れ{\k31}だ{\k35}け {\k69}さ',
]

EXPECTED_TIMINGS_JA = [
    ('0:00:01.07', '0:00:07.72'),
    ('0:00:18.86', '0:00:26.03'),
    ('0:00:26.03', '0:00:32.94'),
]

# ------------------------------------------------------------------------------
# Chinese -> pinyin
# ------------------------------------------------------------------------------
TIMED_LINES_ZH = [
    make_line(0, [
        ('nǐ', [('nǐ', 34)]),
        ('wèn', [('wèn', 117)]),
        ('wǒ', [('wǒ', 37)]),
        ('ài', [('ài', 117)]),
        ('nǐ', [('nǐ', 36)]),
        ('yǒu', [('yǒu', 113)]),
        ('duō', [('duō', 38)]),
        ('shēn', [('shēn', 122)]),
    ], syl_joiner='-'),
]

EXPECTED_LINES_ZH = [
    r'{\k34}nǐ {\k117}wèn {\k37}wǒ {\k117}ài {\k36}nǐ {\k113}yǒu {\k38}duō {\k122}shēn',
]

# ------------------------------------------------------------------------------
# Taigi -> tai-lo
# ------------------------------------------------------------------------------
#
TIMED_LINES_TW = [
    make_line(0, [
        ('Tsi̍t-sî', [("Tsi̍t", 36), ("sî", 34)]),
        ('sit-tsì', [("sit", 117), ("tsì", 34)]),
        ('m-bián', [("m", 34), ("bián", 41)]),
        ('uàn-thàn', [("uàn", 68), ("thàn", 230)]),
    ], syl_joiner='-'),
]

EXPECTED_LINES_TW = [
    r'{\k36}Tsi̍t-{\k34}sî {\k117}sit-{\k34}tsì {\k34}m-{\k41}bián {\k68}uàn-{\k230}thàn',
]

# ------------------------------------------------------------------------------
# Full .ass file tests
# ------------------------------------------------------------------------------
def assert_format_line(timed_lines, expected_lines):
    for i in range(len(timed_lines)):
        line = timed_lines[i]
        assert format_line(line) == expected_lines[i]

def test_format_line_jp():
    assert_format_line(TIMED_LINES_JA, EXPECTED_LINES_JA)

def test_format_line_chinese_pinyin():
    assert_format_line(TIMED_LINES_ZH, EXPECTED_LINES_ZH)

def test_format_line_taigi_tailo():
    assert_format_line(TIMED_LINES_TW, EXPECTED_LINES_TW)

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

    for i in range(len(EXPECTED_LINES_JA)):
        start, end = EXPECTED_TIMINGS_JA[i]
        line = EXPECTED_LINES_JA[i]
        expected += f'Dialogue: 0,{start},{end},{style},,0,0,0,karaoke,{line}\n'

    subs = to_ssa_file(TIMED_LINES_JA, template_file=template_file).to_string('ass')

    subs = subs.split('[Events]\n')[1]

    assert subs == expected
