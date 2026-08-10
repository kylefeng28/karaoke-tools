from timing import TimedSyllable, TimedWord, Line
from cjk_utils import split_tokens, split_morae, is_cjk, convert_to_romaji
from romaji_utils import split_romaji_morae


def generic_tokenizer(text):
    """Generic tokenizer, suitable for Chinese and Korean. Can be used as a fallback for other languages."""
    tokens = split_tokens(text)
    return [TimedSyllable(tok, mode='start_end') for tok in tokens]


def japanese_tokenizer(parser, convert_romaji=False):
    def tokenizer(text: str) -> list[TimedWord]:
        """Japanese text tokenizer. Processes text using MeCab/kakasi and converts them into mora-based TimedSyllables"""
        tokens = []
        jp_tokens = parser.convert(text)
        for token in jp_tokens:
            surface = token.surface

            if all(is_cjk(ch) for ch in surface):
                hiragana = token.reading or token.surface
                morae = split_morae(hiragana)
                syllables = [TimedSyllable(m, mode='start_end') for m in morae]
            else:
                syllables = [TimedSyllable(token.surface, mode='start_end')]

            tokens.append(TimedWord(text=surface, syllables=syllables))

        if convert_romaji:
            for word in tokens:
                n_syllables = len(word.syllables)
                for i in range(n_syllables-1, -1, -1):
                    syllable = word.syllables[i]
                    syllable.text = convert_to_romaji(syllable.text, n_syllables == 1)
                    # Handle sokuon/small tsu (っ): jaconv converts it to 'xtsu', but we need to
                    # replace it with the first character of the following syllable
                    # e.g. あっさり -> axtsu-sari -> assari, 真っ白 まっしろ -> maxtsu-shiro -> masshiro
                    if syllable.text == 'xtsu':
                        if i < n_syllables-1:
                            replacer = word.syllables[i+1].text[0]
                        else:
                            replacer = "'"
                        syllable.text = syllable.text.replace('xtsu', replacer)

                word.text = ''.join([syl.text for syl in word.syllables])

        return tokens

    return tokenizer


def romaji_tokenizer():
    def tokenizer(text: str) -> list[TimedWord]:
        tokens = []
        for word in split_tokens(text):
            if morae := split_romaji_morae(word):
                syllables = [TimedSyllable(m, mode='start_end') for m in morae]
            else:
                syllables = [TimedSyllable(word, mode='start_end')]
            tokens.append(TimedWord(text=word, syllables=syllables))

        return tokens

    return tokenizer


def tokenize_lyrics(raw_lines: list[str], tokenizer) -> list[Line]:
    lines = []
    i = 0
    for raw in raw_lines:
        try:
            lines.append(Line(start=0.0, end=0.0, tokens=tokenizer(raw)))
        except Exception as e:
            raise Exception(f'Error tokenizing line {i}: {raw}') from e
        i += 1
    return lines
