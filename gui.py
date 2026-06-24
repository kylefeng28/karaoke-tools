import sys
from dataclasses import dataclass, field
import re

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QStatusBar)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QKeyEvent

from mpv import MpvIPC

def _fmt_time(sec: float) -> str:
    cs = round(max(0.0, sec) * 100)
    h, r = divmod(cs, 360000); mn, r = divmod(r, 6000); sc, cs = divmod(r, 100)
    return f"{h}:{mn:02}:{sc:02}.{cs:02}"

def _fmt_speed(speed: float) -> str:
    return f"{speed:02}"

@dataclass
class Token:
    text:      str
    preview:   str
    start:     float = 0.0
    end:       float = 0.0
    timed:     bool  = False

@dataclass
class Line:
    start:   float
    end:     float
    tokens:  list[Token] = field(default_factory=list)
    preview: str = ""

class SyllableWidget(QWidget):
    """Displays one line's tokens with color-coded states."""

    def __init__(self):
        super().__init__()
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._labels: list[QLabel] = []

    def set_tokens(self, tokens: list[Token], cur_tok: int, timing_active: bool):
        # clear old
        for lbl in self._labels:
            lbl.deleteLater()
        self._labels.clear()

        for idx, tok in enumerate(tokens):
            lbl = QLabel(tok.preview)
            lbl.setFont(QFont("sans-serif", 18))
            if idx == cur_tok and timing_active:
                lbl.setStyleSheet("background: #00bcd4; color: black; padding: 2px 4px; border-radius: 3px; font-weight: bold;")
            elif idx == cur_tok:
                lbl.setStyleSheet("background: #455a64; color: white; padding: 2px 4px; border-radius: 3px; font-weight: bold;")
            elif tok.timed:
                lbl.setStyleSheet("color: #4caf50; padding: 2px 4px;")
            else:
                lbl.setStyleSheet("color: #ccc; padding: 2px 4px;")
            self._layout.addWidget(lbl)
            self._labels.append(lbl)

        self._layout.addStretch()


class MainWindow(QMainWindow):
    def __init__(self, lines: list[Line], mpv: MpvIPC):
        super().__init__()
        self.lines = lines
        self.mpv = mpv
        self.cur_line = 0
        self.cur_tok = 0
        self.syl_start: float | None = None
        self.playing = False
        self.last_t = 0.0

        self.setWindowTitle("Karaoke Syllable Timer")
        self.setMinimumSize(700, 400)
        self.setStyleSheet("background: #263238; color: #eceff1;")

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
        self.ctx_above.setStyleSheet("color: #78909c; padding: 4px;")
        self.ctx_above.setWordWrap(True)
        layout.addWidget(self.ctx_above)

        # current line syllables
        self.syl_widget = SyllableWidget()
        layout.addWidget(self.syl_widget)

        # context lines below
        self.ctx_below = QLabel()
        self.ctx_below.setFont(QFont("sans-serif", 13))
        self.ctx_below.setStyleSheet("color: #78909c; padding: 4px;")
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
        self.status.showMessage("SPACE=end+next  N=end(gap)")

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

    def _refresh(self):
        # context above
        above = [self.lines[i].preview for i in range(max(0, self.cur_line-2), self.cur_line)]
        self.ctx_above.setText('\n'.join(above))

        # syllable display
        ln = self.lines[self.cur_line]
        self.syl_widget.set_tokens(ln.tokens, self.cur_tok, self.syl_start is not None)

        # context below
        below = [self.lines[i].preview for i in range(self.cur_line+1, min(len(self.lines), self.cur_line+4))]
        self.ctx_below.setText('\n'.join(below))

        # progress
        done = sum(1 for tk in ln.tokens if tk.timed)
        self.lbl_progress.setText(
            f"Line {self.cur_line+1}/{len(self.lines)}  "
            f"Syl {self.cur_tok+1}/{len(ln.tokens)}  ({done} timed)")


    def keyPressEvent(self, ev: QKeyEvent):
        key = ev.key()

        if self.mpv:
            if key == Qt.Key.Key_P:
                if self.playing: self.mpv.pause(); self.playing = False
                else:            self.mpv.play();  self.playing = True
                self._refresh()
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
            elif key == Qt.Key.Key_Semicolon:
                self.mpv.seek_rel(-3.0)
                self.status.showMessage("⟵ -3s")
            elif key == Qt.Key.Key_Apostrophe:
                self.mpv.seek_rel(+3.0)
                self.status.showMessage("⟶ +3s")

        if key == Qt.Key.Key_Right:
            self.syl_start = None
            self.token_next()
            self._refresh()
        elif key == Qt.Key.Key_Left:
            self.syl_start = None
            self.token_prev()
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

    def token_prev(self):
        if self.cur_tok > 0:
            self.cur_tok -= 1

    def token_next(self):
        if self.cur_tok < len(self.lines[self.cur_line].tokens)-1:
            self.cur_tok += 1

    def line_prev(self):
        if self.cur_line > 0:
            self.cur_line -= 1
            self.cur_tok = 0

    def line_next(self):
        if self.cur_line < len(self.lines)-1:
            self.cur_line += 1
            self.cur_tok = 0

    def closeEvent(self, ev):
        self.mpv.close()
        super().closeEvent(ev)


def split_tokens(text):
    # Split by character for CJK characters and spaces for Latin characters
    # Regex matches: 
    # [^\s\w] -> Any punctuation, symbols, or formatting marks
    # [\u4e00-\u9fff] -> All standard Chinese, Japanese, and Korean characters
    # \w+ -> Latin characters/words
    pattern = r'[^\s\w]|[\u4e00-\u9fff]|\w+'
    
    tokens = re.findall(pattern, text)
    return [Token(tok, tok) for tok in tokens]


def load_lyrics(path: str) -> list[Line]:
    lines = []
    with open(path) as f:
        for raw in f:
            raw = raw.strip()
            if raw:
                lines.append(Line(start=0.0, end=0.0,
                                  tokens=(split_tokens(raw)),
                                  preview=raw))
    return lines

def main():
    if len(sys.argv) < 2:
        print("usage: <lyrics_file> [media_file]")
        sys.exit(1)

    lyrics_file = sys.argv[1]
    if len(sys.argv) >= 3:
        media_file = sys.argv[2]
    else:
        media_file = None

    lines = load_lyrics(lyrics_file)
    if not lines:
        print(f"No lines found in {lyrics_file}"); sys.exit(1)

    mpv = MpvIPC(media_file) if media_file else None

    app = QApplication(sys.argv)
    win = MainWindow(lines, mpv)
    win.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
