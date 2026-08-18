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

# ------------------------------------------------------------------------------
# QSettings helpers
# ------------------------------------------------------------------------------
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

# ------------------------------------------------------------------------------
# Custom widgets
# ------------------------------------------------------------------------------
class FilePicker(QGroupBox):
    def __init__(self, title: str, placeholder: str, browse_title: str, file_types: str):
        super().__init__(title)

        self.title = title
        self.placeholder = placeholder
        self.browse_title = browse_title
        self.file_types = file_types

        layout = QHBoxLayout(self)
        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText(placeholder)
        self.line_edit.setReadOnly(True)
        layout.addWidget(self.line_edit)
        browse_btn = QPushButton("Browse...", clicked=self.browse)
        layout.addWidget(browse_btn)
        clear_btn = QPushButton("Clear", clicked=self.clear)
        layout.addWidget(clear_btn)

        self.setLayout(layout)

    def clear(self):
        self.line_edit.clear()

    def browse(self):
        start_dir = os.path.dirname(self.line_edit.text()) if self.line_edit.text() else ""
        path, _ = QFileDialog.getOpenFileName(
            self.parent(), self.browse_title, start_dir,
            self.file_types)
        if path:
            self.line_edit.setText(path)

    def value(self) -> str:
        return self.line_edit.text().strip()

    def show_error(self):
        self.line_edit.setStyleSheet("border: 2px solid red;")

class RadioGroup(QGroupBox):
    def __init__(self, title: str):
        super().__init__(title)
        self.options = {}
        self.layout = QVBoxLayout(self)
        self.btn_group = QButtonGroup(self)
        self.setLayout(self.layout)

    def add_option(self, id: int, title: str, name: str):
        self.options[id] = name
        radio = QRadioButton(title)
        self.layout.addWidget(radio)
        self.btn_group.addButton(radio, id)

    def value(self) -> str:
        id = self.btn_group.checkedId()
        return self.options.get(id)

# ------------------------------------------------------------------------------
# Launcher dialog
# ------------------------------------------------------------------------------
class LauncherDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.settings = LauncherSettings()
        self.setWindowTitle(TITLE)
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)

        def addWidget(widget):
            layout.addWidget(widget)
            return widget

        self.lyrics_path = addWidget(FilePicker(
            title="Lyrics file (required)",
            placeholder="Select an .txt lyrics file...",
            browse_title="Select lyrics file",
            file_types="Text files (*.txt);;All files (*)",
        ))
        self.settings.add_config(FilePathConfig(_LYRICS_PATH, self.lyrics_path.line_edit))

        self.media_path = addWidget(FilePicker(
            title="Media file (optional)",
            placeholder="Select an audio/video file...",
            browse_title="Select media file",
            file_types="Media files (*.mp4 *.mkv *.avi *.webm *.mp3 *.ogg *.flac *.wav);;All files (*)"
        ))
        self.settings.add_config(FilePathConfig(_MEDIA_PATH, self.media_path.line_edit))

        # Tokenizer radio buttons
        self.tokenize_radio = addWidget(RadioGroup("Tokenizer"))
        self.tokenize_radio.add_option(0, "None (generic)", None)
        self.tokenize_radio.add_option(1, "MeCab (Japanese, morphological analyzer)", "mecab")
        self.tokenize_radio.add_option(2, "Kakasi (Japanese, lightweight)", "kakasi")
        self.tokenize_radio.add_option(3, "Japanese romaji", "romaji")

        self.settings.add_config(RadioConfig(_TOKENIZER, self.tokenize_radio.btn_group))

        # Options
        options_group = addWidget(QGroupBox("Options"))
        options_layout = QVBoxLayout(options_group)

        self.romaji_checkbox = QCheckBox("Convert to Romaji")
        options_layout.addWidget(self.romaji_checkbox)

        self.settings.add_config(CheckboxConfig(_CONVERT_ROMAJI, self.romaji_checkbox))

        # Launch button
        self.launch_btn = addWidget(QPushButton("Launch"))
        self.launch_btn.setDefault(True)
        self.launch_btn.setMinimumHeight(40)
        self.launch_btn.clicked.connect(self._launch)

        self.result = None

        # Restore cached values
        self.settings.restore_settings()

    def _launch(self):
        lyrics = self.lyrics_path.value()
        if not lyrics:
            self.lyrics_path.show_error()
            return

        tokenize = self.tokenize_radio.value()
        convert_romaji = self.romaji_checkbox.isChecked()

        self.settings.save_settings()

        self.result = {
            'lyrics': lyrics,
            'media': self.media_path.value() or None,
            'tokenize': tokenize,
            'convert_romaji': convert_romaji,
        }
        self.accept()


