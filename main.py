from nlp import convert, set_backend
import sys

from subs import read_ass_file

# set_backend('kakasi')
set_backend('fugashi')

def convert_and_print(text):
    converted = convert(text)
    print(converted[0])
    print(converted[1])

def read_txt_file(input_file):
    with open(input_file, 'r') as f:
        for line in f:
            line = line.strip()
            convert_and_print(line)

def main():
    if len(sys.argv) > 1:
        # Read file
        input_file = sys.argv[1]

        if input_file.endswith(".ass"):
            read_ass_file(input_file)
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
