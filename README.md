# karaoke-tools

A collection of scripts and tools for dealing with Japanese karaoke and lyrics, like adding furigana to text.

Work in progress.

- [pykakasi](https://pypi.org/project/pykakasi/) - transliteration tool to romanize kanji, based on dictionary lookups.
  - This is the simplest one, but it might produce inaccurate results since it doesn't actually do proper text segmentation

Planned features:
- [ ] Use [mecab](https://github.com/shogo82148/mecab) which is a Japanese morphological analyser, and [MikimotoH/furigana](https://github.com/MikimotoH/furigana) to properly segmentize Japanese text and add furigana
- [ ] Support Chinese and pinyin

Future roadmap:
- [ ] Support other languages/dialects using Chinese characters like Cantonese and Hokkien/Minnan/台語

### Usage

```
# File input mode
$ uv run main.py gurenge_jp.txt
強く[つよく]なれる理由[りゆう]を知っ[しっ]た　僕[ぼく]を連れ[つれ]て進め[すすめ]
tsuyoku nareru riyuu wo shitsu ta 　boku wo tsure te susume

泥[どろ]だらけの走馬灯[そうまとう]に酔う[よう]　こわばる心[こころ]
doro darakeno soumatou ni you 　kowabaru kokoro
震え[ふるえ]る手[て]は掴み[つかみ]たいものがある　それだけさ
furue ru te ha tsukami taimonogaaru 　soredakesa
夜[よる]の匂い[におい]に空[そら]睨ん[にらん]でも
yoru no nioi ni sora niran demo
変わ[かわ]っていけるのは自分自身[じぶんじしん]だけ　それだけさ
kawa tteikerunoha jibunjishin dake 　soredakesa
...
```

# REPL mode
```
$ uv run main.py
Enter Japanese text with kanji:
漢字を入力して：
> 私は人間です
私[わたし]は人間[にんげん]です
watashi ha ningen desu
```
