from cjk_utils import is_kanji, is_kana, is_hangul, is_cjk, split_tokens


def assert_token(s: str, kanji: bool, kana: bool, hangul: bool, cjk: bool):
    for ch in s:
        print(ch)
        assert is_kanji(ch) == kanji
        assert is_kana(ch) == kana
        assert is_hangul(ch) == hangul
        assert is_cjk(ch) == cjk

def assert_kanji(s: str):
    assert_token(s, kanji=True, kana=False, hangul=False, cjk=True)


def assert_kana(s: str):
    assert_token(s, kanji=False, kana=True, hangul=False, cjk=True)


def assert_hangul(s: str):
    assert_token(s, kanji=False, kana=False, hangul=True, cjk=True)


def assert_latin(s: str):
    assert_token(s, kanji=False, kana=False, hangul=False, cjk=False)


def test_cjk():
    assert_kanji('漢字')
    assert_kana('これ')
    assert_kana('ひらがな')
    assert_kana('コレ')
    assert_kana('カタカナ')
    assert_hangul('한글')
    assert_hangul('안녕')
    assert_latin('hello')


def test_split_tokens():
    assert split_tokens('我的名字')         == ['我', '的', '名', '字']
    assert split_tokens('my name is')       == ['my', 'name', 'is']
    assert split_tokens('これはなんですか') == ['こ', 'れ', 'は', 'な', 'ん', 'で', 'す', 'か']
    assert split_tokens('コレハナンデスカ') == ['コ', 'レ', 'ハ', 'ナ', 'ン', 'デ', 'ス', 'カ']
    assert split_tokens('私はJohnです')     == ['私', 'は', 'John', 'で', 'す']

    # Small kana should be combined with previous mora
    assert split_tokens('しょうねん')      == ['しょ', 'う', 'ね', 'ん']
    assert split_tokens('しょうじょ')      == ['しょ', 'う', 'じょ']

