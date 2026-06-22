import fugashi
import ipadic
import jaconv
from utils import is_kanji, is_hiragana, split_okurigana

# Pykakasi is simpler and faster, based on dictionary lookups: https://codeberg.org/miurahr/pykakasi
import pykakasi
class PykakasiParser:
    def convert(self, text):
        kks = pykakasi.kakasi()
        kks_result = kks.convert(text)

        result = []
        for item in kks_result:
            orig = item['orig']
            hiragana = item['hira']
            katakana = item['kana']
            romaji = item['hepburn']

            if orig.isspace():
                result += [(orig,)]
            elif orig == hiragana or orig == katakana:
                result += [(orig,)]
            else:
                result += [(orig, hiragana)]

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
            orig = word.surface
            if not orig:
                continue

            if any(is_kanji(ch) for ch in orig):
                kana = word.feature.kana
                if kana:
                    hiragana = jaconv.kata2hira(kana)
                    result += [(orig, hiragana)]
                else:
                    result += [(orig,)]
            else:
                result += [(orig,)]

        return result
