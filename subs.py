import pyonfx
from dataclasses import dataclass, field

# Represents a line of words
@dataclass
class Line:
    _line: pyonfx.Line
    words: 'KTimedWord' = field(default_factory=list)

# Represents a word with its syllables marked with \k tags
@dataclass
class KTimedWord:
    _word: pyonfx.Word
    _syllables: list[pyonfx.Syllable] = field(default_factory=list)

    def add_syllable(self, syllable):
        self._syllables.append(syllable)

    def __str__(self):
        syls = [s.text for s in self._syllables]
        syls = ''.join(syls)
        return f"\\k({self._word.text}: {syls})"

    def convert_hiragana(self):
        import jaconv

        # Convention is that uppercase words are English or non-Japanese loanwords
        if self._word.text.isupper():
            return

        converted = jaconv.alphabet2kana(self._word.text)
        # print((word, converted))
        self._word.text = converted

        for syl in self._syllables:
            converted = jaconv.alphabet2kana(syl.text)
            # print((syl_text, converted))
            syl.text = converted

def read_ass_file(input_file):
    io = pyonfx.Ass(input_file)

    for line in io.lines:
        if line.effect != "karaoke":
            continue

        k_timed_words = [KTimedWord(w) for w in line.words]

        for syl in line.syls:
            k_timed_words[syl.word_i].add_syllable(syl)

        for word in k_timed_words:
            word.convert_hiragana()
            print(word)

        print()

