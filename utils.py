import unicodedata
import jaconv


def is_kanji(ch):
    return 'CJK UNIFIED IDEOGRAPH' in unicodedata.name(ch)


def is_hiragana(ch):
    return 'HIRAGANA' in unicodedata.name(ch)


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
    if is_hiragana(text[0]):
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
