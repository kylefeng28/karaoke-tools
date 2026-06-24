from cjk_utils import is_kanji, is_kana, is_hangul, is_cjk, split_tokens, join_tokens


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


def assert_token_split_join(joined: str, split: list[str]):
    assert split_tokens(joined) == split
    assert join_tokens(split) == joined

def test_split_and_join():
    assert_token_split_join('我的名字', ['我', '的', '名', '字'])
    assert_token_split_join('my name is', ['my', 'name', 'is'])
    assert_token_split_join('これはなんですか', ['こ', 'れ', 'は', 'な', 'ん', 'で', 'す', 'か'])
    assert_token_split_join('コレハナンデスカ', ['コ', 'レ', 'ハ', 'ナ', 'ン', 'デ', 'ス', 'カ'])
    assert_token_split_join('私はJohnです', ['私', 'は', 'John', 'で', 'す'])

    # Small kana should be combined with previous mora
    assert_token_split_join('しょうねん', ['しょ', 'う', 'ね', 'ん'])
    assert_token_split_join('しょうじょ', ['しょ', 'う', 'じょ'])

    # Apostrophe should be combined with previous word
    assert_token_split_join("I'll be goin'", ["I'll", 'be', "goin'"])
    assert_token_split_join("Ain't that right", ["Ain't", 'that', 'right'])
