import pykakasi
import sys

kks = pykakasi.kakasi()

def convert_kakasi(text):
    result = kks.convert(text)

    furigana_result = ''
    romaji_result = ''

    for item in result:
        orig = item['orig']
        hiragana = item['hira']
        katakana = item['kana']
        romaji = item['hepburn']

        if orig.isspace():
            furigana_result += orig
            romaji_result += orig
        elif orig == hiragana or orig == katakana:
            furigana_result += orig
            romaji_result += romaji + ' '
        else:
            furigana_result += f"{orig}[{hiragana}]"
            romaji_result += romaji + ' '

    print(furigana_result)
    print(romaji_result)

def main():
    if len(sys.argv) > 1:
        # Read file
        input_file = sys.argv[1]
        with open(input_file, 'r') as f:
            for line in f:
                line = line.strip()
                convert_kakasi(line)

    else:
        # REPL mode
        print("Enter Japanese text with kanji:")
        print("漢字を入力して：")
        while True:
            try:
                text = input('> ')
                convert_kakasi(text)
            except EOFError | KeyboardInterrupt:
                break

if __name__ == "__main__":
    main()
