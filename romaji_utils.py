import re
import pytest

MORA_PATTERN = r"""
(?:
    # Digraph consonant + vowel combinations — MUST come before geminate and simple CV,
    # otherwise 'sh', 'ts', 'ky' etc. get split by the geminate lookahead first.
    ch[aiueo]|
    sh[aiueo]|
    ts[aiueo]|
    ky[aiueo]|
    ny[aiueo]|
    hy[aiueo]|
    my[aiueo]|
    ry[aiueo]|
    gy[aiueo]|
    by[aiueo]|
    py[aiueo]|
    sy[aiueo]|   # alternate romaji for し行
    ty[aiueo]|   # alternate romaji for ち行
    dy[aiueo]|
    zy[aiueo]|
    ji|ja|ju|je|jo|     # ジャ行
    di|du|              # alternate romaji for ぢ/づ
    ti|                 # alternate romaji for ち
    wi|we|wo|           # rare kana
    fu|                 # ふ

    # Geminate (double consonant) e.g. itte
    # 'h' is intentionally excluded: 'th' is not a valid Japanese geminate,
    # and including it would cause "the" to parse as t(geminate) + he.
    (?:k|s|t|p|m|r|w|g|z|d|b|n)(?=(?:k|s|t|p|m|r|w|g|z|d|b))|

    # Simple CV
    [kstphmyrwgzdbf][aiueo]|
    n[aiueo]|

    # Standalone vowel
    [aiueo]|

    # Syllabic n (ん) — only when NOT followed by a vowel or 'y'
    n(?![aiueoy])
)
"""

MORA_RE = re.compile(MORA_PATTERN, re.VERBOSE | re.IGNORECASE)


def is_potential_romaji(word: str) -> tuple[bool, int|str]:
    """
    Returns (is_romaji, mora_or_reason).
    A word is considered potential romaji if the entire string can be
    decomposed into valid Japanese mora (V or CV or syllabic ん) with nothing left over.
    True  -> the word *could* be romaji (doesn't rule out English homophones like 'hone').
    False -> the word *cannot* be romaji (violates Japanese syllable structure).
    """
    word = word.strip().lower()
    if not word:
        return False, 0

    pos = 0
    mora_count = 0
    while pos < len(word):
        m = MORA_RE.match(word, pos)
        if not m:
            return False, f"Invalid romaji structure at position {pos}: '...{word[pos:pos+4]}...'"
        pos = m.end()
        mora_count += 1

    return True, mora_count
