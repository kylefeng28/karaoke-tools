from nlp import FugashiParser, PykakasiParser
import sys

from subs import read_ass_file, convert_hiragana
from merge import merge_files


# parser = PykakasiParser()
parser = FugashiParser()
def convert_and_print(text):
    converted = parser.convert(text)
    print(converted)


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
