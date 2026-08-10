# Lyric Syllable Timing tool

Work in progress.

**Installation**
- Clone this repo by running `git clone https://github.com/kylefeng28/karaoke-tools` or downloading the zip [here](https://github.com/kylefeng28/karaoke-tools/archive/refs/heads/main.zip) and then unzipping it.
- This project requires [uv](https://docs.astral.sh/uv/getting-started/installation/) and also [mpv](https://mpv.io/installation/), so install those before proceeding.
  - If you are on Windows, please put `mpv.exe` in the `karaoke-tools` folder or ensure it is somewhere in your Command Line or Powershell `PATH`.

**Basic usage**:
$ uv sync
```
$ uv run gui.py lyrics.txt video_file.mp4 # default tokenizer, suitable for Chinese and Korean where 1 character = 1 syllable
$ uv run gui.py lyrics.txt video_file.mp4 --tokenize mecab  # use MeCab for adding furigana/readings to Japanese text
$ uv run gui.py lyrics.txt video_file.mp4 --tokenize kakasi # use MeCab for adding furigana/readings to Japanese text
```

### Demo

Click on any of the pictures below to see the video:

**Running timing tool for Japanese text, with furigana/readings generated with MeCab**:

```
$ uv run gui.py gurenge.txt gurenge.mp4 --tokenize mecab
```

<video src="https://github.com/user-attachments/assets/ee26bbd5-4442-4eca-8e50-993e55072527" width="3440" height="1440"></video>

**mpv with `.ass` subs generated with tool**:
<video src="https://github.com/user-attachments/assets/6da2ac1a-bdeb-4b7f-8c49-7811df975c23" width="3440" height="1440"></video>

**Running timing tool for Chinese text** (default tokenizer):

```
$ uv run gui.py moon_represents_my_heart.txt moon_represents_my_heart.mp4
```

<video src='https://github.com/user-attachments/assets/3f309c06-daf1-4548-a746-007bf0fcdb0f' width="566" height="462"></video>

**mpv with `.ass` subs generated with tool**:

<video src="https://github.com/user-attachments/assets/6af0e409-48c5-4c92-b8ca-21e676c1d6e1" width="1180" height="900"></video>

### Technical details
This tool supports 2 modes of Japanese parsing:
1. `--tokenize mecab`: uses [MeCab](https://github.com/shogo82148/mecab). MeCab is a classic phonological analyzer/segmentation tool for Japanese, and this uses [fugashi](https://github.com/polm/fugashi) as a Python wrapper for MeCab. This is more accurate but it requires downloading unidic which takes a couple hundred of megabytes.
- `--tokenize kakasi`: uses [pykakasi](https://pypi.org/project/pykakasi/). This is much more simple/easier to use than MeCab as it doesn't require unidic, but it might produce inaccurate results since it doesn't actually do proper text segmentation from what I can tell.

### Acknowledgement
Inspired by:
- [karass](https://vladkorotnev.me/karass/) [vladkorotnev/karass](https://github.com/vladkorotnev/karass) - similar tool, written in JavaScript
- [NicoKaraMaker](https://shinta0806be.ldblog.jp/tag/%E3%83%8B%E3%82%B3%E3%82%AB%E3%83%A9%E3%83%A1%E3%83%BC%E3%82%AB%E3%83%BC), [new version](https://shinta.coresv.com/software/nicokaramaker3-jpn/) [hinta0806/NicoKaraMaker3/](https://github.com/shinta0806/NicoKaraMaker3/) - Japanese tool for making karaoke videos
