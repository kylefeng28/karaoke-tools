"""
Controls:
  P      — play / pause
  [ / ]  — slower / faster
  ; / '  — seek -3s / +3s
  SPACE  — end current syllable + start next
  N      — end current syllable, leave a gap
  /      — redo current line
  R      — reset current line
  S      — save .ass file
"""

import os
import sys

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QStatusBar)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QKeyEvent

from mpv import MpvIPC
from timing import TimedSyllable, TimedWord, Line
from nlp import FugashiParser, PykakasiParser
from cjk_utils import split_tokens, is_kanji, split_morae

def _fmt_time(sec: float) -> str:
    if sec is None:
        sec = 0.0
    cs = round(max(0.0, sec) * 100)
    h, r = divmod(cs, 360000); mn, r = divmod(r, 6000); sc, cs = divmod(r, 100)
    return f"{h}:{mn:02}:{sc:02}.{cs:02}"

def _fmt_speed(speed: float) -> str:
    return f"{speed:02}"


CONTROLS_DISPLAY = "SPACE=end+next  N=end(gap)  P=play/pause  [/]=speed  ;/'=seek  R=reset  S=save"

_ASS_HEADER = """\
[Script Info]
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,80,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,3,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

def export_ass(lines: list[Line], out_path: str):
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(_ASS_HEADER)
        for ln in lines:
            text, last = '', ln.get_start()
            for tok in ln.get_syllables():
                if tok.timed:
                    gap = tok.start - last
                    extra = 0.0
                    if gap > 0.005:
                        text += '{\\kf%d}' % round(gap * 100)
                    text += '{\\kf%d}%s' % (round((tok.end - tok.start + extra) * 100), tok.preview())
                    last = tok.end
                else:
                    text += tok.preview()
            f.write(f"Dialogue: 0,{_fmt_time(ln.get_start())},{_fmt_time(ln.get_end())},"
                    f"Default,,0,0,0,karaoke,{text}\n")


# Styles
MAIN_BG = '#263238'
MAIN_FG = '#eceff1'

CTX_LINE_FG = '#78909c'
CUR_TOK_ACTIVE_BG = '#00bcd4'
CUR_TOK_ACTIVE_FG = 'black'

CUR_TOK_BG = '#455a64'
CUR_TOK_FG = 'white'
TOK_TIMED_ACTIVE_WORD_FG = '#34694e'
TOK_TIMED_FG = '#4caf50'
TOK_DEFAULT_FG = '#ccc'

class SyllableWidget(QWidget):
    """Displays one line's words with furigana and per-syllable highlighting."""

    def __init__(self):
        super().__init__()
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._labels: list[QLabel] = []

    def set_tokens(self, tokens: list[TimedSyllable], cur_tok: int, timing_active: bool,
                   words: list = None):
        # clear old
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._labels.clear()

        if words is None:
            # Flat mode (Chinese or fallback): one label per syllable
            for idx, tok in enumerate(tokens):
                lbl = QLabel(tok.preview())
                lbl.setFont(QFont("sans-serif", 18))
                lbl.setStyleSheet(self._syl_style(idx, cur_tok, timing_active, tok.timed))
                self._layout.addWidget(lbl)
                self._labels.append(lbl)
        else:
            # Word-grouped mode with furigana (Japanese)
            syl_idx = 0
            for word in words:
                lbl = QLabel()
                lbl.setTextFormat(Qt.TextFormat.RichText)
                lbl.setFont(QFont("sans-serif", 18))
                html = self._render_word(word, syl_idx, cur_tok, timing_active)
                lbl.setText(html)
                lbl.setStyleSheet("padding: 0px 2px;")
                self._layout.addWidget(lbl)
                self._labels.append(lbl)
                syl_idx += len(word.syllables)

        self._layout.addStretch()

    def _syl_style(self, idx, cur_tok, timing_active, timed):
        if idx == cur_tok and timing_active:
            return "background: #00bcd4; color: black; padding: 2px 4px; border-radius: 3px; font-weight: bold;"
        elif idx == cur_tok:
            return "background: #455a64; color: white; padding: 2px 4px; border-radius: 3px; font-weight: bold;"
        elif timed:
            return "color: #4caf50; padding: 2px 4px;"
        else:
            return "color: #ccc; padding: 2px 4px;"

    def _syl_color(self, syl_idx, cur_tok, timing_active, timed):
        if syl_idx == cur_tok and timing_active:
            return "#00bcd4"
        elif syl_idx == cur_tok:
            return "#ffffff"
        elif timed:
            return "#4caf50"
        else:
            return "#999999"

    def _render_word(self, word, syl_start_idx, cur_tok, timing_active):
        surface = word.text
        reading = ''.join(s.text for s in word.syllables)
        has_kanji = any(is_kanji(ch) for ch in surface)

        # Determine overall word background if active syllable is in this word
        word_has_active = syl_start_idx <= cur_tok < syl_start_idx + len(word.syllables)
        bg = ""
        if word_has_active and timing_active:
            bg = "background-color: #00bcd4;"
        elif word_has_active:
            bg = "background-color: #455a64;"

        # Build colored syllable spans for the reading
        syl_spans = []
        for i, syl in enumerate(word.syllables):
            idx = syl_start_idx + i
            color = self._syl_color(idx, cur_tok, timing_active, syl.timed)
            syl_spans.append(f'<span style="color:{color};">{syl.text}</span>')

        if has_kanji and surface != reading:
            # Ruby: surface on bottom, reading on top
            rt = ''.join(syl_spans)
            # Color the surface chars too
            active_idx = cur_tok - syl_start_idx if word_has_active else -1
            surface_color = self._syl_color(cur_tok, cur_tok, timing_active,
                                            word.syllables[active_idx].timed) if word_has_active else "#ccc"
            html = (f'<span style="{bg} border-radius:3px; padding:1px 3px;">'
                    f'<ruby><span style="color:{surface_color}; font-size:18pt;">{surface}</span>'
                    f'<rt style="font-size:10pt;">{rt}</rt></ruby></span>')
        else:
            # No furigana needed — just show reading syllables
            html = (f'<span style="{bg} border-radius:3px; padding:1px 3px;">'
                    + ''.join(syl_spans) + '</span>')

        return html

class MainWindow(QMainWindow):
    def __init__(self, lines: list[Line], mpv: MpvIPC, out_path: str):
        super().__init__()
        self.lines = lines
        self.mpv = mpv
        self.out_path = out_path
        self.cur_line = 0
        self.cur_tok = 0
        self.syl_start: float | None = None
        self.playing = False
        self.last_t = 0.0

        self.setWindowTitle("Karaoke Syllable Timer")
        self.setMinimumSize(700, 400)
        self.setStyleSheet(f"background: {MAIN_BG}; color: {MAIN_FG};")

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # transport bar
        transport = QHBoxLayout()
        self.lbl_state = QLabel("⏸")
        self.lbl_state.setFont(QFont("sans-serif", 14))
        self.lbl_time = QLabel("0:00:00.00")
        self.lbl_time.setFont(QFont("monospace", 14))
        self.lbl_speed = QLabel("1.00x")
        self.lbl_speed.setFont(QFont("monospace", 14))
        transport.addWidget(self.lbl_state)
        transport.addWidget(self.lbl_time)
        transport.addStretch()
        transport.addWidget(self.lbl_speed)
        layout.addLayout(transport)

        # context lines above
        self.ctx_above = QLabel()
        self.ctx_above.setFont(QFont("sans-serif", 13))
        self.ctx_above.setStyleSheet(f"color: {CTX_LINE_FG}; padding: 4px;")
        self.ctx_above.setWordWrap(True)
        layout.addWidget(self.ctx_above)

        # current line syllables
        self.syl_widget = SyllableWidget()
        layout.addWidget(self.syl_widget)

        # context lines below
        self.ctx_below = QLabel()
        self.ctx_below.setFont(QFont("sans-serif", 13))
        self.ctx_below.setStyleSheet(f"color: {CTX_LINE_FG}; padding: 4px;")
        self.ctx_below.setWordWrap(True)
        layout.addWidget(self.ctx_below)

        layout.addStretch()

        # progress
        self.lbl_progress = QLabel()
        self.lbl_progress.setFont(QFont("monospace", 11))
        layout.addWidget(self.lbl_progress)

        # status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage(CONTROLS_DISPLAY)


        # timer for polling mpv
        self._timer = QTimer()
        self._timer.timeout.connect(self._tick)
        self._timer.start(100)

        self._refresh()

    def _tick(self):
        if self.mpv:
            self.last_t = self.mpv.get_time()
            self.lbl_time.setText(_fmt_time(self.last_t))
            if self.playing:
                self._auto_advance()

    def _auto_advance(self):
        t = self.last_t
        idx = next((i for i, ln in enumerate(self.lines) if ln.start <= t < ln.end), -1)
        if idx != -1 and idx != self.cur_line:
            if self.syl_start is not None:
                self._end_syl(advance=False)
            self.cur_line = idx; self.cur_tok = 0
            self._refresh()

    def _start_syl(self):
        tok = self.lines[self.cur_line].get_syllable(self.cur_tok)
        tok.start = self.last_t
        tok.timed = False
        self.syl_start = self.last_t

    def _end_syl(self, advance: bool):
        tok = self.lines[self.cur_line].get_syllable(self.cur_tok)
        if self.syl_start is not None:
            tok.end = self.last_t; tok.timed = True
        self.syl_start = None

        if advance:
            self.token_next() or self.line_next()
            self._start_syl()

    def _refresh(self):
        # context above
        above = [self.lines[i].preview() for i in range(max(0, self.cur_line-2), self.cur_line)]
        self.ctx_above.setText('\n'.join(above))

        # word/syllable display
        ln = self.lines[self.cur_line]
        words = ln.tokens if ln.tokens and isinstance(ln.tokens[0], TimedWord) else None
        self.syl_widget.set_tokens(ln.get_syllables(), self.cur_tok, self.syl_start is not None,
                                   words=words)

        # context below
        below = [self.lines[i].preview() for i in range(self.cur_line+1, min(len(self.lines), self.cur_line+4))]
        self.ctx_below.setText('\n'.join(below))

        # progress
        done = sum(1 for tk in ln.get_syllables() if tk.timed)
        self.lbl_progress.setText(
            f"Line {self.cur_line+1}/{len(self.lines)}  "
            f"Syl {self.cur_tok+1}/{len(ln.get_syllables())}  ({done} timed)")


    def keyPressEvent(self, ev: QKeyEvent):
        key = ev.key()

        if self.mpv:
            ###############################################################
            ### Playback / speed controls
            ###############################################################
            # P      — play / pause
            if key == Qt.Key.Key_P:
                if self.playing:
                    self.pause()
                else:
                    self.play()
                self._refresh()
            # [ / ]  — slower / faster
            elif key == Qt.Key.Key_BracketRight:
                self.mpv.faster()
                self.lbl_speed.setText(_fmt_speed(self.mpv.speed))
                self.status.showMessage("speed + 0.5")
                self._refresh()
            elif key == Qt.Key.Key_BracketLeft:
                self.mpv.slower()
                self.lbl_speed.setText(_fmt_speed(self.mpv.speed))
                self.status.showMessage("speed - 0.5")
                self._refresh()
            # ; / '  — seek -3s / +3s
            elif key == Qt.Key.Key_Semicolon:
                self.mpv.seek_rel(-3.0)
                self.status.showMessage("⟵ -3s")
            elif key == Qt.Key.Key_Apostrophe:
                self.mpv.seek_rel(+3.0)
                self.status.showMessage("⟶ +3s")

            ###############################################################
            ### Syllable timing
            ###############################################################
            # space  — end current syllable + start next syllable
            elif key == Qt.Key.Key_Space:
                self.last_t = self.mpv.get_time()
                if self.syl_start is None:
                    self._start_syl()
                    self.status.showMessage(f"Started: {self.lines[self.cur_line].get_syllable(self.cur_tok).preview()!r}")
                else:
                    tok = self.lines[self.cur_line].get_syllable(self.cur_tok)
                    self._end_syl(advance=True)
                    self.status.showMessage(f"✓ {tok.preview()!r}  {tok.start:.2f}–{tok.end:.2f}s")
                self._refresh()

            # N      — end current syllable, leave a gap (don't start next syllable)
            elif key == Qt.Key.Key_N:
                self.last_t = self.mpv.get_time()
                if self.syl_start is not None:
                    tok = self.lines[self.cur_line].get_syllable(self.cur_tok)
                    self._end_syl(advance=False)
                    self.token_next() or self.line_next()
                    self.status.showMessage(f"✓ {tok.preview()!r} ended, gap …")
                self._refresh()

            # /      — redo current line
            elif key == Qt.Key.Key_Slash:
                self.syl_start = None
                if self.cur_tok > 0: self.cur_tok = 0
                elif self.cur_line > 0: self.cur_line -= 1; self.cur_tok = 0
                self.mpv.seek(self.lines[self.cur_line].start)
                self.status.showMessage(f"↩ Line {self.cur_line+1}")
                self._refresh()

            # R      — reset current line
            elif key == Qt.Key.Key_R:
                for tk in self.lines[self.cur_line].get_syllables(): tk.timed=False; tk.start=tk.end=0.0
                self.cur_tok = 0; self.syl_start = None
                self.status.showMessage("Line reset.")
                self._refresh()

            elif key == Qt.Key.Key_S:
                self.pause()
                export_ass(self.lines, self.out_path)
                self.status.showMessage(f"✓ Saved → {self.out_path}")
                self._refresh()

        if key == Qt.Key.Key_Right:
            self.syl_start = None
            self.token_next() or self.line_next()
            self._refresh()
        elif key == Qt.Key.Key_Left:
            self.syl_start = None
            self.token_prev() or (self.line_prev() and self.line_end())
            self._refresh()
        elif key == Qt.Key.Key_Down:
            self.syl_start = None
            self.line_next()
            self._refresh()
        elif key == Qt.Key.Key_Up:
            self.syl_start = None
            self.line_prev()
            self._refresh()

        else:
            super().keyPressEvent(ev)

    def play(self):
        self.mpv.play()
        self.playing = True

    def pause(self):
        self.mpv.pause()
        self.playing = False

    def token_prev(self):
        if self.cur_tok > 0:
            self.cur_tok -= 1
            return True

    def token_next(self):
        if self.cur_tok < len(self.lines[self.cur_line].get_syllables())-1:
            self.cur_tok += 1
            return True

    def line_prev(self):
        if self.cur_line > 0:
            self.cur_line -= 1
            self.cur_tok = 0
            return True

    def line_next(self):
        if self.cur_line < len(self.lines)-1:
            self.cur_line += 1
            self.cur_tok = 0
            return True

    def line_end(self):
        self.cur_tok = len(self.lines[self.cur_line].get_syllables())-1
        return True

    def closeEvent(self, ev):
        if self.mpv:
            self.mpv.close()
        super().closeEvent(ev)


def load_raw_lyrics(path: str) -> list[str]:
    line = []
    with open(path) as f:
        for raw in f:
            raw = raw.strip()
            if raw:
                line.append(raw)
    return line


def generic_tokenizer(text):
    """Generic tokenizer, suitable for Chinese and Korean. Can be used as a fallback for other languages."""
    tokens = split_tokens(text)
    return [TimedSyllable(tok, mode='start_end') for tok in tokens]


def japanese_tokenizer(parser):
    def tokenizer(text: str) -> list[TimedWord]:
        """Japanese text tokenizer. Processes text using MeCab/kakasi and converts them into mora-based TimedSyllables"""
        tokens = []
        jp_tokens = parser.convert(text)
        for token in jp_tokens:
            surface = token.surface
            hiragana = token.reading or token.surface
            morae = split_morae(hiragana)
            syllables = [TimedSyllable(m, mode='start_end') for m in morae]
            tokens.append(TimedWord(text=surface, syllables=syllables))

        return tokens

    return tokenizer


def tokenize_lyrics(raw_lines: list[str], tokenizer) -> list[Line]:
    lines = []
    for raw in raw_lines:
        lines.append(Line(start=0.0, end=0.0, tokens=tokenizer(raw)))
    return lines


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Karaoke syllable timer")
    parser.add_argument('lyrics', help='Lyrics file (.txt)')
    parser.add_argument('media', nargs='?', help='Audio/video file for mpv')
    parser.add_argument('--tokenize', choices=['jp', 'mecab', 'kakasi', 'pykakasi'], default=None,
                        help='(None)=no special parsing. split by CJK characters and Latin alphabet words, jp=use MeCab to generate furigana/readings for Japanese text')
    parser.add_argument('--out', '-o', default=None,
                        help='path to export generated .ass file')

    args = parser.parse_args()

    lyrics_file = args.lyrics
    media_file = args.media
    out_path = args.out

    if not out_path:
        out_path = os.path.splitext(lyrics_file)[0] + '_timed.ass'

    raw_lines = load_raw_lyrics(lyrics_file)

    if args.tokenize == 'jp' or args.tokenize == 'mecab':
        print('Tokenizing with MeCab')
        tokenizer = japanese_tokenizer(FugashiParser())
    elif args.tokenize == 'kakasi' or args.tokenize == 'pykakasi':
        print('Tokenizing with pykakasi')
        tokenizer = japanese_tokenizer(PykakasiParser())
    else:
        print('Using generic tokenizer')
        tokenizer = generic_tokenizer

    lines = tokenize_lyrics(raw_lines, tokenizer)

    if not lines:
        print(f"No lines found in {lyrics_file}")
        sys.exit(1)

    mpv = MpvIPC(media_file) if media_file else None

    app = QApplication(sys.argv)
    win = MainWindow(lines, mpv, out_path)
    win.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
