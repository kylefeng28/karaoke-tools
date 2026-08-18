import os

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import (
    QButtonGroup, QCheckBox, QDialog, QFileDialog, QGroupBox, QHBoxLayout,
    QLineEdit, QPushButton, QRadioButton, QVBoxLayout, QWidget
)

TITLE = "Karaoke Syllable Timer"

_LYRICS_PATH = "launcher/lyrics_path"
_MEDIA_PATH = "launcher/media_path"
_TOKENIZER = "launcher/tokenizer"
_CONVERT_ROMAJI = "launcher/convert_romaji"

class WidgetConfig[T: QWidget | QButtonGroup]:
    def __init__(self, key: str, widget: T):
        self.key = key
        self.widget = widget

    def save(self, qsettings: QSettings):
        pass
    def restore(self, qsettings: QSettings):
        pass

class FilePathConfig(WidgetConfig[QLineEdit]):
    def value(self) -> str:
        return self.widget.text().strip()

    def save(self, qsettings: QSettings):
        qsettings.setValue(self.key, self.value())

    def restore(self, qsettings: QSettings):
        value = qsettings.value(self.key, "", type=str)
        if value and os.path.isfile(value):
            self.widget.setText(value)

class RadioConfig(WidgetConfig[QButtonGroup]):
    def value(self) -> int:
        return self.widget.checkedId()

    def save(self, qsettings: QSettings):
        qsettings.setValue(self.key, self.value())

    def restore(self, qsettings: QSettings):
        checked_id = qsettings.value(self.key, 0, type=int)
        btn = self.widget.button(checked_id)
        if btn:
            btn.setChecked(True)

class CheckboxConfig(WidgetConfig[QCheckBox]):
    def value(self):
        return self.widget.isChecked()

    def save(self, qsettings: QSettings):
        qsettings.setValue(self.key, self.value())

    def restore(self, qsettings: QSettings):
        value = qsettings.value(self.key, False, type=bool)
        self.widget.setChecked(value)

class LauncherSettings:
    def __init__(self):
        self.qsettings = QSettings("karaoke-tools", "karaoke-syncer")
        self.configs = []

    def add_config(self, config: WidgetConfig):
        self.configs.append(config)

    def save_settings(self):
        for config in self.configs:
            config.save(self.qsettings)

    def restore_settings(self):
        for config in self.configs:
            config.restore(self.qsettings)


class LauncherDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.settings = LauncherSettings()
        self.setWindowTitle(TITLE)
        self.setMinimumWidth(500)

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

        self.settings.add_config(FilePathConfig(_LYRICS_PATH, self.lyrics_path))

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

        self.settings.add_config(FilePathConfig(_MEDIA_PATH, self.media_path))

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

        self.settings.add_config(RadioConfig(_TOKENIZER, self.tok_button_group))

        # Options
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout(options_group)

        self.romaji_checkbox = QCheckBox("Convert to Romaji")
        options_layout.addWidget(self.romaji_checkbox)

        layout.addWidget(options_group)

        self.settings.add_config(CheckboxConfig(_CONVERT_ROMAJI, self.romaji_checkbox))

        # Launch button
        self.launch_btn = QPushButton("Launch")
        self.launch_btn.setDefault(True)
        self.launch_btn.setMinimumHeight(40)
        self.launch_btn.clicked.connect(self._launch)
        layout.addWidget(self.launch_btn)

        self.result = None

        # Restore cached values
        self.settings.restore_settings()

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

        self.settings.save_settings()

        self.result = {
            'lyrics': lyrics,
            'media': self.media_path.text().strip() or None,
            'tokenize': tokenize,
            'convert_romaji': convert_romaji,
        }
        self.accept()


