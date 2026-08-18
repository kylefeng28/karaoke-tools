import sys

from .cjk_utils import convert_to_romaji
from .merge import merge_files
from .nlp import FugashiParser, PykakasiParser
from .subs import convert_hiragana, read_ass_file

# parser = PykakasiParser()
parser = FugashiParser()
def convert_and_print(text, show_repr=True):
    converted = parser.convert(text)

    for token in converted:
        hiragana = (token.reading or token.surface)
        romaji = convert_to_romaji(hiragana, True)
        if show_repr:
            print(repr(token))
            print(romaji)
        else:
            print(token, romaji)


def read_txt_file(input_file):
    with open(input_file, 'r') as f:
        for line in f:
            line = line.strip()
            convert_and_print(line)


def main():
    if len(sys.argv) == 3:
        # Merge mode: romaji .ass + JP text → k-timed karaoke with kanji ruby
        ass_file, jp_file = sys.argv[1], sys.argv[2]
        merge_files(ass_file, jp_file)

    elif len(sys.argv) == 2:
        # Single file mode
        input_file = sys.argv[1]
        if input_file.endswith(".ass"):
            lines = read_ass_file(input_file)
            for line in lines:
                for word in line.tokens:
                    convert_hiragana(word)
                    print(word, end='\t')

        else:
            read_txt_file(input_file)

    else:
        import readline  # noqa: F401
        # REPL mode
        print("Enter Japanese text with kanji:")
        print("漢字を入力して：")
        while True:
            try:
                text = input('> ')
                convert_and_print(text)
            except EOFError | KeyboardInterrupt:
                break

if __name__ == "__main__":
    main()
