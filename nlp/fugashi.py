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


def split_okurigana_reverse(text, hiragana):
    yield (text[0],)
    yield from split_okurigana(text[1:], hiragana[1:])


def split_okurigana(text, hiragana):
    if is_hiragana(text[0]):
        yield from split_okurigana_reverse(text, hiragana)
    if all(is_kanji(_) for _ in text):
        yield text, hiragana
        return
    text = list(text)
    ret = (text[0], [hiragana[0]])
    for hira in hiragana[1:]:
        for char in text:
            if hira == char:
                text.pop(0)
                if ret[0]:
                    if is_kanji(ret[0]):
                        yield ret[0], ''.join(ret[1][:-1])
                        yield (ret[1][-1],)
                    else:
                        yield (ret[0],)
                else:
                    yield (hira,)
                ret = ('', [])
                if text and text[0] == hira:
                    text.pop(0)
                break
            else:
                if is_kanji(char):
                    if ret[1] and hira == ret[1][-1]:
                        text.pop(0)
                        yield ret[0], ''.join(ret[1][:-1])
                        yield char, hira
                        ret = ('', [])
                        text.pop(0)
                    else:
                        ret = (char, ret[1]+[hira])
                else:
                    # char is also hiragana
                    if hira != char:
                        break
                    else:
                        break


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
