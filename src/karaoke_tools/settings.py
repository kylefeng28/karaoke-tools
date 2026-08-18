from dataclasses import dataclass
from pathlib import Path

DEFAULT_TEMPLATE_FILE = './templates/karaoke_mugen_template.ass'

@dataclass
class Settings:
    lyrics_file: str
    media_file: str | None
    tokenize: str
    convert_romaji: bool
    out_path: str | None = None
    template_file: str | None = None

    def __post_init__(self):
        if not self.lyrics_file:
            raise ValueError('lyrics_file cannot be null')

        if not self.template_file:
            self.template_file = DEFAULT_TEMPLATE_FILE

    def is_existing_sub(self):
        path = Path(self.lyrics_file)
        return path.suffix == '.ass'

    @property
    def default_out_path(self):
        path = Path(self.lyrics_file)
        if self.is_existing_sub():
            return str(path)
        else:
            return str(path.stem + '_timed.ass')
