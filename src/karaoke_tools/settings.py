import os
from dataclasses import dataclass

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

        if not self.out_path:
            self.out_path = os.path.splitext(self.lyrics_file)[0] + '_timed.ass'

        if not self.template_file:
            self.template_file = DEFAULT_TEMPLATE_FILE

