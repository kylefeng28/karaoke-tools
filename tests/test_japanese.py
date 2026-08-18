from karaoke_tools.nlp import FugashiParser
from karaoke_tools.cjk_utils import JapaneseToken, convert_to_romaji

parser = FugashiParser()

def convert(text):
    converted = parser.convert(text)
    # for token in converted:
    #     print(repr(token))
    return converted

def assert_match(text, expected, expected_romaji=None):
    assert convert(text) == expected
    romaji = []
    for token in expected:
        hiragana = (token.reading or token.surface)
        romaji.append(convert_to_romaji(hiragana, True))
    assert romaji == expected_romaji

def test_japanese():
    assert_match(
        text = '私は人間です',
        expected = [
            JapaneseToken(surface='私', reading='わたし', furigana_pairs=[('私', 'わたし')]),
            JapaneseToken(surface='は', reading=None, furigana_pairs=('は',)),
            JapaneseToken(surface='人間です', reading='にんげんです', furigana_pairs=[('人間', 'にんげん'), ('で',), ('す',)]),
        ],
        expected_romaji = ['watashi', 'wa', 'ningendesu']
    )

    assert_match(
        text = '強くなれる理由を知った　僕を連れて進め',
        expected = [
            JapaneseToken(surface='強く', reading='つよく', furigana_pairs=[('強', 'つよ'), ('く',)]),
            JapaneseToken(surface='なれる', reading=None, furigana_pairs=('なれる',)),
            JapaneseToken(surface='理由', reading='りゆう', furigana_pairs=[('理由', 'りゆう')]),
            JapaneseToken(surface='を', reading=None, furigana_pairs=('を',)),
            JapaneseToken(surface='知った', reading='しった', furigana_pairs=[('知', 'し'), ('っ',), ('た',)]),
            JapaneseToken(surface='僕', reading='ぼく', furigana_pairs=[('僕', 'ぼく')]),
            JapaneseToken(surface='を', reading=None, furigana_pairs=('を',)),
            JapaneseToken(surface='連れて', reading='つれて', furigana_pairs=[('連', 'つ'), ('れ',), ('て',)]),
            JapaneseToken(surface='進め', reading='すすめ', furigana_pairs=[('進', 'すす'), ('め',)]),
        ],
        expected_romaji = ['tsuyoku', 'nareru', 'riyuu', 'o', 'shitta', 'boku', 'o', 'tsurete', 'susume'],
    )

    assert_match(
        text = '人々　時々　様々',
        expected = [
            JapaneseToken(surface='人々', reading='ひとびと', furigana_pairs=[('人々', 'ひとびと')]),
            JapaneseToken(surface='時々', reading='ときどき', furigana_pairs=[('時々', 'ときどき')]),
            JapaneseToken(surface='様々', reading='さまざま', furigana_pairs=[('様々', 'さまざま')])
        ],
        expected_romaji = ['hitobito', 'tokidoki', 'samazama']
    )

def test_japanese_unknown_reading():
    assert_match(
        text = '憚',
        expected = [
            JapaneseToken(surface='憚', reading='?', furigana_pairs=[('憚', '?')]),
        ],
        expected_romaji = ['?']
    )

    assert_match(
        text = '憚るもの皆',
        expected = [
            JapaneseToken(surface='憚る', reading='?る', furigana_pairs=[('憚', '?'), ('る',)]),
            JapaneseToken(surface='もの', reading=None, furigana_pairs=('もの',)),
            JapaneseToken(surface='皆', reading='みな', furigana_pairs=[('皆', 'みな')])
        ],
        expected_romaji = ['?ru', 'mono', 'mina']
    )
