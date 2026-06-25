import unicodedata
import jaconv

from dataclasses import dataclass


@dataclass
class JapaneseToken:
    """One MeCab morpheme with its furigana breakdown"""

    surface: str                 # e.g. "強く"
    reading: str                 # hiragana reading, e.g. "つよく"
    furigana_pairs: list         # from split_okurigana: [("強","つよ"), ("く",)]

    def __str__(self):
        if not self.reading or self.surface == self.reading:
            return self.surface
        s = f'{self.surface} ({self.reading})'
        if len(self.furigana_pairs) <= 1:
            return s
        else:
            furigana_pairs_str = '; '.join([','.join(pair) for pair in self.furigana_pairs])
            return s + f' [{furigana_pairs_str}]'


# \u4E00-\u9FFF   # CJK Unified Ideographs (core)
# \u3400-\u4DBF   # CJK Extension A
# \u20000-\u2A6DF # CJK Extension B
def is_kanji(ch) -> bool:
    return unicodedata.name(ch).startswith('CJK UNIFIED IDEOGRAPH')


# \u3040-\u309F
def is_hiragana(ch) -> bool:
    return unicodedata.name(ch).startswith('HIRAGANA')


# \u30A0-\u30FF
def is_katakana(ch) -> bool:
    return unicodedata.name(ch).startswith('KATAKANA')


def is_kana(ch) -> bool:
    return is_hiragana(ch) or is_katakana(ch)


# \uAC00-\uD7AF
def is_hangul(ch) -> bool:
    return unicodedata.name(ch).startswith('HANGUL')


def is_cjk(ch) -> bool:
    return is_kanji(ch) or is_kana(ch) or is_hangul(ch)

# Small kana that combine with the preceding kana to form a single mora
SMALL_KANA = set('ぁぃぅぇぉゃゅょゎァィゥェォャュョヮ')


def should_combine(ch, prev):
    return ch in SMALL_KANA and is_kana(prev)


def split_tokens(text: str) -> list[str]:
    """
    Split by character for CJK characters and spaces for Latin characters.
    Accounts for Japanese small kana and mixed CJK/Latin text.
    This is a generic used as a generic character stream / parsing fallback;
    for proper word segmentation, see nlp.py which uses MeCab to parse Japanese text.

    For example:
    '我的名字' -> ['我', '的', '名', '字'] # all hanzi/kanji
    'これ' -> ['こ', 'れ'] # all kana
    '私はJohnです' -> ['私', 'は', 'John', 'で', 'す'] # mixed kanji/kana/Latin
    'しょうねん' -> 'しょ', 'う', 'ね, 'ん' # small kana combines with previous kana
    """
    tokens = []
    current_latin = []

    def flush_latin():
        # Flush buffered Latin text
        nonlocal tokens, current_latin
        if current_latin:
            tokens.append(''.join(current_latin))
            current_latin = []

    for ch in text:
        if is_cjk(ch):
            if tokens and should_combine(ch, tokens[-1]):
                tokens[-1] += ch
            else:
                flush_latin()
                tokens.append(ch)
        elif unicodedata.category(ch) == 'Zs' or ch.isspace():
            flush_latin()
        elif unicodedata.category(ch).startswith('P'):
            # Apostrophe: consider part of current word
            if ch == "'":
                current_latin.append(ch)
            else:
                # Punctuation: flush then emit punctuation as its own token
                flush_latin()
                tokens.append(ch)
        else:
            current_latin.append(ch)

    flush_latin()

    return tokens


def join_tokens(tokens: list[str]) -> str:
    """
    Join tokens directly for CJK characters (no space) and with spaces separators for Latin characters.
    For mixed text, join with no space since the
    In other words, 
    """
    if not tokens:
        return ''

    prev_token, result = None, ''
    for token in tokens:
        if not token:
            continue
        if not prev_token or is_cjk(prev_token[-1]) or is_cjk(token[0]):
            result += token
        else:
            result += ' ' + token
        prev_token = token

    return result

def split_okurigana(text, hiragana):
    """ 送り仮名 processing
      tested:
         * 出会(であ)う
         * 明(あか)るい
         * 駆(か)け抜(ぬ)け
         * (か)け抜(ぬ)け
         * お茶(おちゃ)
         * ご無沙汰(ごぶさた)
         * お子(こ)さん
         * 進(すす)め
         * 戦(たた)い
         * 温(あたた)かい
    """
    if not text:
        return
    # Hiragana prefix (e.g. お茶、ご無沙汰): yield the leading hiragana as-is
    if is_kana(text[0]):
        yield (text[0],)
        yield from split_okurigana(text[1:], hiragana[1:])
        return
    # Pure kanji block: the whole reading belongs to the whole block
    if all(is_kanji(ch) for ch in text):
        yield text, hiragana
        return
    # Mixed kanji+okurigana: find the first hiragana anchor in text.
    # Each kanji takes >=1 mora, so the anchor can't appear before index i in hiragana
    for i, ch in enumerate(text):
        if not is_kanji(ch):
            j = hiragana.index(ch, i)
            if i > 0:
                yield text[:i], hiragana[:j]
            yield (ch,)
            yield from split_okurigana(text[i + 1:], hiragana[j + 1:])
            return

def convert_to_hiragana(s: str, is_whole_word):
    # Convention is that uppercase words are English or non-Japanese loanwords
    if s.isupper():
        return s

    # "wa" and "o" should be は and を instead of わ and お when they are standalone particles
    if s == "wa" and is_whole_word:
        return "は"
    elif s == "o" and is_whole_word:
        return "お"

    return jaconv.alphabet2kana(s)
