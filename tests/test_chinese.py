from karaoke_tools.tokenizer import chinese_tokenizer, taigi_tokenizer
from karaoke_tools.timing import TimedWord, TimedSyllable

def convert(tokenizer, text):
    converted = tokenizer(text)
    for token in converted:
        print(repr(token))
    return converted

def assert_match(tokenizer, text, expected):
    converted = convert(tokenizer, text)
    assert len(text) == len(expected)
    for i, word in enumerate(converted):
        assert word.text == expected[i].text
        assert len(word.syllables) == len(expected[i].syllables)
        for j, syl in enumerate(word.syllables):
            assert syl.text == expected[i].syllables[j].text

def test_chinese():
    tokenizer = chinese_tokenizer()
    assert_match(
        tokenizer = tokenizer,
        text = '月亮代表我的心',
        expected = [
            TimedWord(text='yuè', syllables=[TimedSyllable(text='yuè', mode='start_end')], syl_joiner='-'),
            TimedWord(text='liàng', syllables=[TimedSyllable(text='liàng', mode='start_end')], syl_joiner='-'),
            TimedWord(text='dài', syllables=[TimedSyllable(text='dài', mode='start_end')], syl_joiner='-'),
            TimedWord(text='biǎo', syllables=[TimedSyllable(text='biǎo', mode='start_end')], syl_joiner='-'),
            TimedWord(text='wǒ', syllables=[TimedSyllable(text='wǒ', mode='start_end', )], syl_joiner='-'),
            TimedWord(text='de', syllables=[TimedSyllable(text='de', mode='start_end')], syl_joiner='-'),
            TimedWord(text='xīn', syllables=[TimedSyllable(text='xīn', mode='start_end')], syl_joiner='-'),
        ],
    )

def test_taigi():
    tokenizer = taigi_tokenizer()
    assert_match(
        tokenizer = tokenizer,
        text = '愛拚才會贏',
        expected = [
            TimedWord(text='Ài', syllables=[TimedSyllable(text='Ài', mode='start_end')], syl_joiner='-'),
            TimedWord(text='piànn', syllables=[TimedSyllable(text='piànn', mode='start_end')], syl_joiner='-'),
            TimedWord(text='tsâi', syllables=[TimedSyllable(text='tsâi', mode='start_end')], syl_joiner='-'),
            TimedWord(text='ē', syllables=[TimedSyllable(text='ē', mode='start_end')], syl_joiner='-'),
            TimedWord(text='iânn', syllables=[TimedSyllable(text='iânn', mode='start_end', )], syl_joiner='-'),
        ],
    )
