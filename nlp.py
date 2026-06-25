import fugashi
import ipadic
import jaconv
from cjk_utils import is_kanji, split_okurigana, JapaneseToken

# Pykakasi is simpler and faster, based on dictionary lookups: https://codeberg.org/miurahr/pykakasi
import pykakasi
class PykakasiParser:
    def convert(self, text):
        kks = pykakasi.kakasi()
        kks_result = kks.convert(text)

        result = []
        for item in kks_result:
            surface = item['orig']
            hiragana = item['hira']
            katakana = item['kana']
            # romaji = item['hepburn']

            if surface.isspace():
                continue
            elif surface == hiragana or surface == katakana:
                pairs = (surface,)
            else:
                pairs = list(split_okurigana(surface, hiragana))

            token = JapaneseToken(surface=surface, reading=hiragana, furigana_pairs=pairs)
            result.append(token)

        return result

# ------------------------------------------------------------
# Uses https://github.com/polm/fugashi which is a wrapper around MeCab
# Based on this code which uses mecab-python3: https://github.com/MikimotoH/furigana/blob/master/furigana/furigana.py

IpadicFeatures = fugashi.create_feature_wrapper(
    'IpadicFeatures',
    'pos1 pos2 pos3 pos4 cType cForm lemma kana pron'.split(),
)
tagger = fugashi.GenericTagger(ipadic.MECAB_ARGS, wrapper=IpadicFeatures)

class FugashiParser:
    def convert(self, text):
        result = []
        for word in tagger(text):
            surface = word.surface
            if not surface:
                continue

            kana = word.feature.kana
            if surface.isspace():
                continue
            elif any(is_kanji(ch) for ch in surface) and kana:
                hiragana = jaconv.kata2hira(kana)
                pairs = list(split_okurigana(surface, hiragana))
            else:
                hiragana = None
                pairs = (surface,)

            token = JapaneseToken(surface=surface, reading=hiragana, furigana_pairs=pairs)
            result.append(token)

        return result
