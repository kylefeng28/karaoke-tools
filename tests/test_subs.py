from subs import format_k_syllable, format_line, to_ssa_file
from timing import TimedWord, TimedSyllable, Line


def test_format_k_syllable():
    assert format_k_syllable(s=1.12, text="つ") == "{\\k112}つ"
    assert format_k_syllable(s=1.08, text="よ") == "{\\k108}よ"
    assert format_k_syllable(s=1.09, text="く") == "{\\k109}く"


def test_format_line():
    t_s = 0  # time in seconds so far

    def syl(text: str, duration_cs: int):
        nonlocal t_s
        start_s = t_s
        end_s = start_s + duration_cs / 100
        t_s = end_s
        return TimedSyllable(text, mode='start_end', timed=True, start=start_s, end=end_s)

    line = Line([
        TimedWord('つよく', [syl('つ', 41), syl('よ', 32), syl('く', 109)]),
        TimedWord('なれる', [syl('な', 36), syl('れ', 36), syl('る', 90)]),
        TimedWord('理由', [syl('り', 15), syl('ゆ', 21), syl('う', 21)]),
        TimedWord('を', [syl('を', 34)]),
        TimedWord('知った', [syl('し', 53), syl('っ', 45), syl('た', 132)]),
    ])
    expected = r'{\k41}つ{\k32}よ{\k109}く {\k36}な{\k36}れ{\k90}る {\k15}り{\k21}ゆ{\k21}う {\k34}を {\k53}し{\k45}っ{\k132}た'

    assert format_line(line) == expected


def test_to_ssa_file():
    pass
