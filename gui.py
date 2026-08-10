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
                             QHBoxLayout, QLabel, QStatusBar, QDialog,
                             QPushButton, QFileDialog, QRadioButton, QCheckBox,
                             QButtonGroup, QGroupBox, QLineEdit)
from PyQt6.QtCore import Qt, QTimer, QSettings
from PyQt6.QtGui import QFont, QKeyEvent

from mpv import MpvIPC
from timing import TimedSyllable, TimedWord, Line
from nlp import FugashiParser, PykakasiParser
from tokenizer import japanese_tokenizer, romaji_tokenizer, generic_tokenizer, tokenize_lyrics


def _fmt_time(sec: float) -> str:
    if sec is None:
        sec = 0.0
    cs = round(max(0.0, sec) * 100)
    h, r = divmod(cs, 360000); mn, r = divmod(r, 6000); sc, cs = divmod(r, 100)
    return f"{h}:{mn:02}:{sc:02}.{cs:02}"

def _fmt_speed(speed: float) -> str:
    return f"{speed:02}"

TITLE = "Karaoke Syllable Timer"
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
            for tok in ln.tokens:
                for syl in tok.get_syllables():
                    if syl.timed:
                        gap = syl.start - last
                        extra = 0.0
                        if gap > 0.005:
                            text += '{\\kf%d}' % round(gap * 100)
                        text += '{\\kf%d}%s' % (round((syl.end - syl.start + extra) * 100), syl.preview())
                        last = syl.end
                    else:
                        text += syl.preview()

                # Add space between words
                if tok.get_type() == 'word':
                    text += ' '

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

        syls_preview = [s.preview() for s in tok.get_syllables()]
        if tok.preview() != ''.join(syls_preview):
            display = f'{tok.preview()} [' + ''.join(spans) + ']'
        else:
            display = ''.join(spans)


        html = '<div>' + display + '</div>'
        return (html, style)


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
    with open(path, encoding='utf-8') as f:
        for raw in f:
            raw = raw.strip()
            if raw:
                line.append(raw)
    return line


class LauncherDialog(QDialog):
    _LYRICS_PATH = "launcher/lyrics_path"
    _MEDIA_PATH = "launcher/media_path"
    _TOKENIZER = "launcher/tokenizer"
    _CONVERT_ROMAJI = "launcher/convert_romaji"

    def __init__(self):
        super().__init__()
        self.setWindowTitle(TITLE)
        self.setMinimumWidth(500)
        self.settings = QSettings("karaoke-tools", "karaoke-syncer")

        layout = QVBoxLayout(self)

        # Lyrics file picker
        lyrics_group = QGroupBox("Lyrics file (required)")
        lyrics_layout = QHBoxLayout(lyrics_group)
        self.lyrics_path = QLineEdit()
        self.lyrics_path.setPlaceholderText("Select a .txt lyrics file...")
        self.lyrics_path.setReadOnly(True)
        lyrics_btn = QPushButton("Browse...")
        lyrics_btn.clicked.connect(self._browse_lyrics)
        lyrics_layout.addWidget(self.lyrics_path)
        lyrics_layout.addWidget(lyrics_btn)
        layout.addWidget(lyrics_group)

        # Media file picker
        media_group = QGroupBox("Media file (optional)")
        media_layout = QHBoxLayout(media_group)
        self.media_path = QLineEdit()
        self.media_path.setPlaceholderText("Select an audio/video file...")
        self.media_path.setReadOnly(True)
        media_btn = QPushButton("Browse...")
        media_btn.clicked.connect(self._browse_media)
        media_clear_btn = QPushButton("Clear")
        media_clear_btn.clicked.connect(lambda: self.media_path.clear())
        media_layout.addWidget(self.media_path)
        media_layout.addWidget(media_btn)
        media_layout.addWidget(media_clear_btn)
        layout.addWidget(media_group)

        # Tokenizer radio buttons
        tok_group = QGroupBox("Tokenizer")
        tok_layout = QVBoxLayout(tok_group)
        self.tok_button_group = QButtonGroup(self)

        def add_tokenizer_option(title, id):
            radio = QRadioButton(title)
            self.tok_button_group.addButton(radio, id)
            tok_layout.addWidget(radio)

        add_tokenizer_option("None (generic)", 0)
        add_tokenizer_option("MeCab (Japanese, morphological analyzer)", 1)
        add_tokenizer_option("Kakasi (Japanese, lightweight)", 2)
        add_tokenizer_option("Japanese romaji", 3)

        layout.addWidget(tok_group)

        # Options
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout(options_group)

        self.romaji_checkbox = QCheckBox("Convert to Romaji")
        options_layout.addWidget(self.romaji_checkbox)

        layout.addWidget(options_group)

        # Launch button
        self.launch_btn = QPushButton("Launch")
        self.launch_btn.setDefault(True)
        self.launch_btn.setMinimumHeight(40)
        self.launch_btn.clicked.connect(self._launch)
        layout.addWidget(self.launch_btn)

        self.result = None

        # Restore cached values
        self._restore_settings()

    def _restore_settings(self):
        lyrics = self.settings.value(self._LYRICS_PATH, "")
        media = self.settings.value(self._MEDIA_PATH, "")
        tok_id = self.settings.value(self._TOKENIZER, 0, type=int)
        convert_romaji = self.settings.value(self._CONVERT_ROMAJI, False)

        if lyrics and os.path.isfile(lyrics):
            self.lyrics_path.setText(lyrics)
        if media and os.path.isfile(media):
            self.media_path.setText(media)

        btn = self.tok_button_group.button(tok_id)
        if btn:
            btn.setChecked(True)

        self.romaji_checkbox.setChecked(convert_romaji)

    def _save_settings(self):
        self.settings.setValue(self._LYRICS_PATH, self.lyrics_path.text().strip())
        self.settings.setValue(self._MEDIA_PATH, self.media_path.text().strip())
        self.settings.setValue(self._TOKENIZER, self.tok_button_group.checkedId())
        self.settings.setValue(self._CONVERT_ROMAJI, self.romaji_checkbox.isChecked())

    def _browse_lyrics(self):
        start_dir = os.path.dirname(self.lyrics_path.text()) if self.lyrics_path.text() else ""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Lyrics File", start_dir,
            "Text files (*.txt);;All files (*)")
        if path:
            self.lyrics_path.setText(path)

    def _browse_media(self):
        start_dir = os.path.dirname(self.media_path.text()) if self.media_path.text() else ""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Media File", start_dir,
            "Media files (*.mp4 *.mkv *.avi *.webm *.mp3 *.ogg *.flac *.wav);;All files (*)")
        if path:
            self.media_path.setText(path)

    def _launch(self):
        lyrics = self.lyrics_path.text().strip()
        if not lyrics:
            self.lyrics_path.setStyleSheet("border: 2px solid red;")
            return

        tok_id = self.tok_button_group.checkedId()
        tokenize = {0: None, 1: 'mecab', 2: 'kakasi', 3: 'romaji'}.get(tok_id)
        convert_romaji = self.romaji_checkbox.isChecked()

        self._save_settings()

        self.result = {
            'lyrics': lyrics,
            'media': self.media_path.text().strip() or None,
            'tokenize': tokenize,
            'convert_romaji': convert_romaji,
        }
        self.accept()


def main():
    app = QApplication(sys.argv)

    # If no CLI arguments provided, show the launcher dialog
    if len(sys.argv) <= 1:
        dlg = LauncherDialog()
        if dlg.exec() != QDialog.DialogCode.Accepted or dlg.result is None:
            sys.exit(0)

        lyrics_file = dlg.result['lyrics']
        media_file = dlg.result['media']
        tokenize = dlg.result['tokenize']
        out_path = os.path.splitext(lyrics_file)[0] + '_timed.ass'
        convert_romaji = dlg.result['convert_romaji']

    else:
        import argparse

        parser = argparse.ArgumentParser(description='Karaoke syllable timer')
        parser.add_argument('lyrics', help='Lyrics file (.txt)')
        parser.add_argument('media', nargs='?', help='Audio/video file for mpv')
        parser.add_argument('--tokenize', choices=['none', 'jp', 'mecab', 'kakasi', 'pykakasi', 'romaji'], default=None,
                            help='(None)=no special parsing. split by CJK characters and Latin alphabet words, jp=use MeCab to generate furigana/readings for Japanese text')
        parser.add_argument('--convert-romaji', '-r', action='store_true',
                            help='convert romaji (best if used with --tokenize mecab')
        parser.add_argument('--out', '-o', default=None,
                            help='path to export generated .ass file')

        args = parser.parse_args()

        lyrics_file = args.lyrics
        media_file = args.media
        tokenize = args.tokenize
        out_path = args.out
        convert_romaji = args.convert_romaji

        if not out_path:
            out_path = os.path.splitext(lyrics_file)[0] + '_timed.ass'

    raw_lines = load_raw_lyrics(lyrics_file)

    if tokenize in ('jp', 'mecab'):
        print('Tokenizing with MeCab' + (' and converting to romaji' if convert_romaji else ''))
        tokenizer = japanese_tokenizer(FugashiParser(), convert_romaji)
    elif tokenize in ('kakasi', 'pykakasi'):
        print('Tokenizing with pykakasi' + (' and converting to romaji' if convert_romaji else ''))
        tokenizer = japanese_tokenizer(PykakasiParser(), convert_romaji)
    elif tokenize == 'romaji':
        print('Tokenizing romaji')
        tokenizer = romaji_tokenizer
    else:
        print('Using generic tokenizer')
        tokenizer = generic_tokenizer

    lines = tokenize_lyrics(raw_lines, tokenizer)

    if not lines:
        print(f"No lines found in {lyrics_file}")
        sys.exit(1)

    mpv = MpvIPC(media_file) if media_file else None

    win = MainWindow(lines, mpv, out_path)
    win.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
