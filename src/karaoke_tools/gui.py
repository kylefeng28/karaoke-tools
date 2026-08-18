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

import signal
import sys
from operator import attrgetter
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QKeyEvent
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from .launcher import LauncherDialog
from .mpv import MpvIPC
from .nlp import FugashiParser, PykakasiParser
from .settings import DEFAULT_TEMPLATE_FILE, Settings
from .subs import export_ass, read_ass_file
from .timing import Line, TimedSyllable, TimedWord
from .tokenizer import (
    chinese_tokenizer,
    generic_tokenizer,
    japanese_tokenizer,
    romaji_tokenizer,
    taigi_tokenizer,
    tokenize_lyrics,
)
from .utils import _fmt_speed, _fmt_time

TITLE = "Karaoke Syllable Timer"
CONTROLS_DISPLAY = "SPACE=end+next  N=end(gap)  P=play/pause  [/]=speed  ;/'=seek  R=reset  S=save  W=playback  ESC=main menu"


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
    """Displays one line's syllable tokens with color-coded states."""

    def __init__(self):
        super().__init__()
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._labels: list[QLabel] = []

    def set_tokens(self, tokens: list[TimedSyllable | TimedWord], cur_tok: int, timing_active: bool):
        # clear old
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._labels.clear()

        syl_idx = 0
        for tok in tokens:
            lbl = QLabel()
            lbl.setFont(QFont("sans-serif", 18))
            lbl.setTextFormat(Qt.TextFormat.RichText)
            html, style = self.render_html(tok, syl_idx, cur_tok, timing_active)
            lbl.setText(html)
            lbl.setStyleSheet(style)
            self._layout.addWidget(lbl)
            self._labels.append(lbl)
            syl_idx += len(tok.get_syllables())

        self._layout.addStretch()

    def _syl_style(self, tok, syl_idx, cur_tok, timing_active, word_active) -> str:
        style = ''

        if syl_idx == cur_tok:
            style += 'text-decoration: underline; '
            if timing_active:
                fg = CUR_TOK_ACTIVE_FG
            elif syl_idx == cur_tok:
                fg = CUR_TOK_FG
        elif word_active and tok.timed:
            fg = TOK_TIMED_ACTIVE_WORD_FG
        elif tok.timed:
            fg = TOK_TIMED_FG
        else:
            fg = TOK_DEFAULT_FG

        style += f'color: {fg}'
        return style

    def _word_style(self, timing_active, word_active) -> str:
        style = 'padding: 2px 4px; '

        bg = None
        if word_active:
            style += "border-radius:3px; font-weight: bold; "
            if timing_active:
                bg = CUR_TOK_ACTIVE_BG
            else:
                bg = CUR_TOK_BG

        style += f'background: {bg}'
        return style

    def render_html(self, tok, syl_start_idx, cur_tok, timing_active) -> (str, str):  # (html, style)
        word_active = syl_start_idx <= cur_tok < syl_start_idx + len(tok.get_syllables())
        style = self._word_style(timing_active, word_active)

        spans = []
        for i, syl in enumerate(tok.get_syllables()):
            syl_style = self._syl_style(syl, syl_start_idx + i, cur_tok, timing_active, word_active)
            spans.append(f'<span style="{syl_style}">{syl.preview()}</span>')

        if tok.preview() != tok.preview_syllables():
            display = f'{tok.preview()} [' + tok.syl_joiner.join(spans) + ']'
        else:
            display = tok.syl_joiner.join(spans)


        html = '<div>' + display + '</div>'
        return (html, style)


class MainWindow(QMainWindow):
    lines: list[Line]
    mpv: MpvIPC
    settings: Settings
    cur_line: int
    cur_tok: int
    syl_start: float | None
    playing: bool
    last_t: float

    def __init__(self, lines: list[Line], mpv: MpvIPC | None, settings: Settings):
        super().__init__()
        self.lines = lines
        self.mpv = mpv
        self.settings = settings
        self.cur_line = 0
        self.cur_tok = 0
        self.syl_start: float | None = None
        self.playing = False
        self.last_t = 0.0
        self.playback = False

        self.setWindowTitle(TITLE)
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

        # status bar: controls and messages
        self.status = QStatusBar()
        self.status_label = QLabel()
        self.status.addWidget(self.status_label)
        self.setStatusBar(self.status)
        self.show_status('')


        # timer for polling mpv
        self._timer = QTimer()
        self._timer.timeout.connect(self._tick)
        self._timer.start(100)

        self._refresh()


    def show_status(self, text: str):
        self.status_label.setText(text + "\n" + CONTROLS_DISPLAY)

    def _tick(self):
        if self.mpv:
            try:
                self.last_t = self.mpv.get_time()
                self.lbl_time.setText(_fmt_time(self.last_t))
                if self.playback:
                    self._playback_advance()
            except BrokenPipeError:
                print('mpv has stopped unexpectedly')
                self.mpv = None

    def _playback_advance(self):
        t = self.last_t
        tok = self.get_cur_tok()

        if tok.start and tok.end and tok.start <= t <= tok.end:
            pass
        elif tok.end and t > tok.end:
            self.token_next() or self.line_next()
        self._refresh()

    def _start_syl(self):
        tok = self.get_cur_tok()
        tok.start = self.last_t
        tok.timed = False
        self.syl_start = self.last_t

    def _end_syl(self, advance: bool):
        tok = self.get_cur_tok()
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
        self.syl_widget.set_tokens(ln.tokens, self.cur_tok, self.syl_start is not None)

        # context below
        below = [self.lines[i].preview() for i in range(self.cur_line+1, min(len(self.lines), self.cur_line+4))]
        self.ctx_below.setText('\n'.join(below))

        # progress
        done = sum(1 for tk in ln.get_syllables() if tk.timed)
        self.lbl_progress.setText(
            f"Line {self.cur_line+1}/{len(self.lines)}  "
            f"Syl {self.cur_tok+1}/{len(ln.get_syllables())}  ({done} timed)")

    def keyPressEvent(self, ev: QKeyEvent):
        if self.playback:
            self.keyPressEventPlayback(ev)
        else:
            self.keyPressEventTiming(ev)

    def keyPressEventPlayback(self, ev: QKeyEvent):
        key = ev.key()

        if key == Qt.Key.Key_Escape:
            self.show_new_launcher()
        elif key == Qt.Key.Key_W:
            self.stop_playback()
        elif key == Qt.Key.Key_Left:
            self.start_playback()
            self._refresh()
        elif key == Qt.Key.Key_Down:
            self.line_next()
            self.start_playback()
            self._refresh()
        elif key == Qt.Key.Key_Up:
            self.line_prev()
            self.start_playback()
            self._refresh()
        else:
            super().keyPressEvent(ev)

    def keyPressEventTiming(self, ev: QKeyEvent):
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
                self.show_status("speed + 0.5")
                self._refresh()
            elif key == Qt.Key.Key_BracketLeft:
                self.mpv.slower()
                self.lbl_speed.setText(_fmt_speed(self.mpv.speed))
                self.show_status("speed - 0.5")
                self._refresh()
            # ; / '  — seek -3s / +3s
            elif key == Qt.Key.Key_Semicolon:
                self.mpv.seek_rel(-3.0)
                self.show_status("⟵ -3s")
            elif key == Qt.Key.Key_Apostrophe:
                self.mpv.seek_rel(+3.0)
                self.show_status("⟶ +3s")

            ###############################################################
            ### Syllable timing
            ###############################################################
            # space  — end current syllable + start next syllable
            elif key == Qt.Key.Key_Space:
                self.last_t = self.mpv.get_time()
                if self.syl_start is None:
                    self._start_syl()
                    self.show_status(f"Started: {self.get_cur_tok().preview()!r}")
                else:
                    tok = self.get_cur_tok()
                    self._end_syl(advance=True)
                    self.show_status(f"✓ {tok.preview()!r}  {tok.start:.2f}–{tok.end:.2f}s")
                self._refresh()

            # N      — end current syllable, leave a gap (don't start next syllable)
            elif key == Qt.Key.Key_N:
                self.last_t = self.mpv.get_time()
                if self.syl_start is not None:
                    tok = self.get_cur_tok()
                    self._end_syl(advance=False)
                    self.token_next() or self.line_next()
                    self.show_status(f"✓ {tok.preview()!r} ended, gap …")
                self._refresh()

            # /      — redo current line
            elif key == Qt.Key.Key_Slash:
                self.syl_start = None
                if self.cur_tok > 0: self.cur_tok = 0
                elif self.cur_line > 0: self.cur_line -= 1; self.cur_tok = 0
                self.mpv.seek(self.get_cur_line().get_start())
                self.show_status(f"↩ Line {self.cur_line+1}")
                self._refresh()

            # R      — reset current line
            elif key == Qt.Key.Key_R:
                for tk in self.get_cur_line().get_syllables(): tk.timed=False; tk.start=tk.end=0.0
                self.cur_tok = 0; self.syl_start = None
                self.show_status("Line reset.")
                self._refresh()

            # S      — save .ass file
            elif key == Qt.Key.Key_S:
                self.pause()
                out_path = self.show_export_dialog(self.settings)
                if out_path:
                    out_path = export_ass(self.lines, out_path, template_file=self.settings.template_file)
                    self.show_status(f"✓ Saved → {out_path}")
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
        elif key == Qt.Key.Key_Escape:
            self.show_new_launcher()
        elif key == Qt.Key.Key_W:
            self.start_playback()
        else:
            super().keyPressEvent(ev)

    def start_playback(self):
        if self.mpv:
            self.play()
            self.cur_tok = 0
            if self.get_cur_line().get_start():
                self.show_status("starting playback")
                self.mpv.seek(self.get_cur_line().get_start())
                self.playback = True

    def stop_playback(self):
        self.show_status("stopping playback")
        self.playback = False

    def play(self):
        self.mpv.play()
        self.playing = True

    def pause(self):
        self.mpv.pause()
        self.playing = False

    def get_cur_tok(self):
        return self.lines[self.cur_line].get_syllable(self.cur_tok)

    def get_cur_line(self):
        return self.lines[self.cur_line]

    def token_prev(self):
        while self.cur_tok > 0:
            self.cur_tok -= 1
            if self.get_cur_tok().mode != 'skip':
                return True
        return False

    def token_next(self):
        while self.cur_tok < len(self.get_cur_line().get_syllables())-1:
            self.cur_tok += 1
            if self.get_cur_tok().mode != 'skip':
                return True
        return False

    # TODO: need to gracefully handle cases when advancing to the next line and the first character is punctuation (skip)
    # or going to the previous line and the last character is punctuation
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
        self.cur_tok = len(self.get_cur_line().get_syllables())-1
        return True

    def closeEvent(self, ev):
        if self.mpv:
            self.mpv.close()
        super().closeEvent(ev)

    def show_export_dialog(self, settings: Settings):
        path, _ = QFileDialog.getSaveFileName(
            self, 'Select output file', settings.default_out_path,
            'Subtitle files (*.ass)')

        if not path:
            return None

        path = Path(path)
        if path.suffix != '.ass':
            return path.with_suffix(path.suffix + '.ass')
        else:
            return path

    def show_new_launcher(self):
        new_settings = show_launcher_dialog()
        if new_settings:
            launch_main_window(new_settings)


def load_raw_lyrics(path: str) -> list[str]:
    line = []
    with open(path, encoding='utf-8') as f:
        for raw in f:
            raw = raw.strip()
            if raw:
                line.append(raw)
    return line


# Globals
app = None
mpv = None
window = None

def cleanup(*args):
    global mpv

    if mpv:
        try:
            print('Stopping mpv...')
            mpv.close()
        except Exception:
            print('Error stopping mpv')
    print('Exiting...')
    sys.exit(0)


def main():
    global app

    app = QApplication(sys.argv)

    # Start QTimer to handle Control-C from Python thread
    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(200)

    # Run cleanup on Qt exit handler
    app.aboutToQuit.connect(cleanup)

    # Run cleanup on SIGINT handler
    signal.signal(signal.SIGINT, cleanup)

    # If no CLI arguments provided, show the launcher dialog
    if len(sys.argv) <= 1:
        settings = show_launcher_dialog()
        if not settings:
            sys.exit(0)

    else:
        import argparse

        parser = argparse.ArgumentParser(description='Karaoke syllable timer')
        parser.add_argument('lyrics', help='Lyrics file (.txt) or subtitles file (.ass)')
        parser.add_argument('media', nargs='?', help='Audio/video file for mpv')
        parser.add_argument('--tokenize', choices=['none', 'jp', 'mecab', 'kakasi', 'pykakasi', 'romaji', 'chinese_pinyin', 'taigi_tailo'], default=None,
                            help='none=no special parsing. split by CJK characters and Latin alphabet words; jp/mecab/kakasi=use MeCab/kakasi to generate furigana/readings for Japanese text')
        parser.add_argument('--convert-romaji', '-r', action='store_true',
                            help='convert romaji (best if used with --tokenize mecab')
        parser.add_argument('--template', '-t', default=DEFAULT_TEMPLATE_FILE,
                            help='template file for generate .ass file (default: %(default)s)') # )
        parser.add_argument('--out', '-o', default=None,
                            help='path to export generated .ass file')

        args = parser.parse_args()

        settings = Settings(
            lyrics_file=args.lyrics,
            media_file=args.media,
            tokenize=args.tokenize,
            out_path=args.out,
            convert_romaji=args.convert_romaji,
        )

    launch_main_window(settings)


def show_launcher_dialog():
    dlg = LauncherDialog()
    if dlg.exec() != QDialog.DialogCode.Accepted or dlg.result is None:
        return None
    else:
        return dlg.result


def launch_main_window(settings):
    global app
    global mpv
    global window

    lyrics_file, media_file, tokenize, convert_romaji = attrgetter("lyrics_file", "media_file", "tokenize", "convert_romaji")(settings)

    if settings.is_existing_sub():
        print('Loading existing subs')
        lines = read_ass_file(settings.lyrics_file)
    else:
        print('Loading lyrics file')
        raw_lines = load_raw_lyrics(lyrics_file)
        if tokenize in ('jp', 'mecab'):
            print('Tokenizing with MeCab' + (' and converting to romaji' if convert_romaji else ''))
            tokenizer = japanese_tokenizer(FugashiParser(), convert_romaji)
        elif tokenize in ('kakasi', 'pykakasi'):
            print('Tokenizing with pykakasi' + (' and converting to romaji' if convert_romaji else ''))
            tokenizer = japanese_tokenizer(PykakasiParser(), convert_romaji)
        elif tokenize == 'romaji':
            print('Tokenizing romaji')
            tokenizer = romaji_tokenizer()
        elif tokenize == 'chinese_pinyin':
            print('Tokenizing Chinese')
            tokenizer = chinese_tokenizer()
        elif tokenize == 'taigi_tailo':
            print('Tokenizing Taiwanese 台語')
            tokenizer = taigi_tokenizer()
        else:
            print('Using generic tokenizer')
            tokenizer = generic_tokenizer

        lines = tokenize_lyrics(raw_lines, tokenizer)

    if not lines:
        print(f"No lines found in {lyrics_file}")
        sys.exit(1)

    mpv = MpvIPC(media_file) if media_file else None

    # If launched from an existing window, we have to close and free the existing one first
    if window:
        existing_window = True
        window.close()
        window.deleteLater()
    else:
        existing_window = False

    window = MainWindow(lines, mpv, settings)
    window.show()

    if not existing_window:
        sys.exit(app.exec())

if __name__ == '__main__':
    main()
