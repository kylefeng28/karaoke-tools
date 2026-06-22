from romaji_utils import is_potential_romaji

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def assert_romaji(word: str, expected_mora: int | None = None):
    result, mora = is_potential_romaji(word)
    assert result
    if expected_mora is not None:
        assert mora == expected_mora


def assert_not_romaji(word: str):
    result, mora = is_potential_romaji(word)
    assert not result


# ---------------------------------------------------------------------------
# Tests: clearly valid romaji
# ---------------------------------------------------------------------------

def test_clear_romaji():
    assert_romaji("watashi", expected_mora=3)
    assert_romaji("watasi", expected_mora=3)
    assert_romaji("kore", expected_mora=2)
    assert_romaji("susume", expected_mora=3)
    assert_romaji("gohan", expected_mora=3)
    assert_romaji("nihon", expected_mora=3)
    assert_romaji("sushi", expected_mora=2)
    assert_romaji("ryokan", expected_mora=3)
    assert_romaji("kyoto", expected_mora=2)
    assert_romaji("tokyo", expected_mora=2)
    assert_romaji("samurai", expected_mora=4)
    assert_romaji("katana", expected_mora=3)
    assert_romaji("kimono", expected_mora=3)
    assert_romaji("futon", expected_mora=3)
    assert_romaji("tsuki", expected_mora=2)
    assert_romaji("tsukimi", expected_mora=3)
    assert_romaji("karate", expected_mora=3)
    assert_romaji("origami", expected_mora=4)
    assert_romaji("emoji", expected_mora=3)
    assert_romaji("ikebana", expected_mora=4)


# sh, ch, ts, ky, ry, etc
def test_digraph_mora():
    assert_romaji("chichi", expected_mora=2)  # chi-chi (父)
    assert_romaji("sha", expected_mora=1)
    assert_romaji("shimbun", expected_mora=4)  # shi-m-bu-n (新聞)
    assert_romaji("tsuru", expected_mora=2)  # tsu-ru (鶴)
    assert_romaji("kyaku", expected_mora=2)  # kya-ku (客)
    assert_romaji("ryuu", expected_mora=2)  # ryu-u (竜, long vowel)
    assert_romaji("gyuudon", expected_mora=4)  # gyu-u-do-n (牛丼)
    assert_romaji("byaku", expected_mora=2)  # bya-ku
    assert_romaji("nyanko", expected_mora=3)  # nya-n-ko
    assert_romaji("jikan", expected_mora=3)  # ji-ka-n (時間)
    assert_romaji("fuji", expected_mora=2)  # fu-ji (富士)
    assert_romaji("sushi", expected_mora=2)
    assert_romaji("tsuki", expected_mora=2)
    assert_romaji("ryokan", expected_mora=3)


def test_geminate():
    assert_romaji("kitte", expected_mora=3)
    assert_romaji("itte", expected_mora=3)
    assert_romaji("zasshi", expected_mora=3)


def test_syllabic_n():
    # word final ん
    assert_romaji("ramen", expected_mora=3)  # ra-me-n
    assert_romaji("gohan", expected_mora=3)  # go-ha-n
    # ん can be written as "m" before a biliabial like b
    assert_romaji("shimbun", expected_mora=4)  # shi-m-bu-n
    # multiple ん
    assert_romaji("genkan", expected_mora=4)  # ge-n-ka-n
    assert_romaji("nani", expected_mora=2)   # na-ni
    assert_romaji("neko", expected_mora=2)   # ne-ko


def test_standalone_n():
    ok, reason = is_potential_romaji("n")
    assert ok, f"Standalone 'n' (ん) should be valid, got: {reason}"


def test_n_before_y_starts_digraph():
    # 'ny' begins a digraph (nya/nyu/nyo), not ん + y
    assert_romaji("nyuu", expected_mora=2)   # nyu-u


def test_n_in_middle_genkan():
    # ge-n-ka-n: both n's are ん (before consonant / word-final)
    assert_romaji("genkan", expected_mora=4)


def test_ambiguous():
    assert_romaji("hone")
    assert_romaji("sake")
    assert_romaji("kite")
    assert_romaji("mire")
    assert_romaji("home")

def test_not_romaji():
    # 'th' is not a valid romaji onset
    assert_not_romaji("this")
    # 'th' cluster is invalid in romaji
    assert_not_romaji("the")
    assert_not_romaji("something")
    assert_not_romaji("regard")
    assert_not_romaji("example")
    assert_not_romaji("string")
    # Consonant cluster with no vowels
    assert_not_romaji("rhythm")
    assert_not_romaji("strength")
    assert_not_romaji("scratch")
    assert_not_romaji("through")
    assert_not_romaji("world")
    assert_not_romaji("xl")
    # 'st' cluster is invalid
    assert_not_romaji("stop")
    assert_not_romaji("track")
    # ends in consonant cluster 'nt'
    assert_not_romaji("went")
    # 'x' is not a romaji consonant
    assert_not_romaji("exit")
    # 'v' does not appear in standard romaji
    assert_not_romaji("voice")
    # 'l' does not appear in standard romaji
    assert_not_romaji("love")
