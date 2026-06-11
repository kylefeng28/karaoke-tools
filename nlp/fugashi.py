# Uses https://github.com/polm/fugashi which is a wrapper around MeCab
# Based on this code which uses mecab-python3: https://github.com/MikimotoH/furigana/blob/master/furigana/furigana.py

import fugashi
import ipadic
import re
import jaconv
import unicodedata


IpadicFeatures = fugashi.create_feature_wrapper(
    'IpadicFeatures',
    'pos1 pos2 pos3 pos4 cType cForm lemma kana pron'.split(),
)
tagger = fugashi.GenericTagger(ipadic.MECAB_ARGS, wrapper=IpadicFeatures)

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


def needs_space_before(word):
    # Only used for romaji since Japanese doesn't use spaces.
    # We need to determine if a two segmentized "words" should be joined or separated by spaces
    # e.g. 食べない will be segmentized as [(食べ, たべ), (ない)], but they should be joined as "tabenai" and not "tabe nai"
    pos1 = word.feature.pos1
    pos2 = word.feature.pos2
    if pos1 == '助動詞':                       # ない、ます、た、だ…
        return False
    if pos2 in ('非自立', '接尾'):             # dependent verbs/adjectives, suffixes
        return False
    if pos1 == '助詞' and pos2 == '接続助詞':  # て、で、ながら…
        return False
    return True


def split_furigana(text):
    ret = []
    for word in tagger(text):
        origin = word.surface
        if not origin:
            continue

        space_before = needs_space_before(word)

        if any(is_kanji(ch) for ch in origin):
            kana = word.feature.kana
            if kana:
                hiragana = jaconv.kata2hira(kana)

                first = True
                for pair in split_okurigana(origin, hiragana):
                    ret += [(pair, first and space_before)]
                    first = False
            else:
                ret += [((origin,), space_before)]
        else:
            ret += [((origin,), space_before)]

    return ret


def convert(text):
    furigana_result = ''
    hiragana_result = ''

    for pair, space_before in split_furigana(text):
        if len(pair) == 2:
            kanji, hira = pair
            furigana_result += f"{kanji}({hira})"
        else:
            hira = pair[0]
            furigana_result += hira

        if space_before:
            hiragana_result += ' ' + hira
        else:
            hiragana_result += hira

    romaji_result = jaconv.kata2alphabet(hiragana_result)

    return [furigana_result, romaji_result]
