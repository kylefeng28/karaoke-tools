# Uses Pykakasi which is based on dictionary lookups: https://codeberg.org/miurahr/pykakasi

import pykakasi

kks = pykakasi.kakasi()

def convert(text):
    result = kks.convert(text)

    furigana_result = ''
    romaji_result = ''

    for item in result:
        orig = item['orig']
        hiragana = item['hira']
        katakana = item['kana']
        romaji = item['hepburn']

        if orig.isspace():
            furigana_result += orig
            romaji_result += orig
        elif orig == hiragana or orig == katakana:
            furigana_result += orig
            romaji_result += romaji + ' '
        else:
            furigana_result += f"{orig}[{hiragana}]"
            romaji_result += romaji + ' '

    return [furigana_result, romaji_result]

