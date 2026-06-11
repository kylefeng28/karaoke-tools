"""
align_ass.py – Merge unsynced furiganised Japanese text with a timed romaji .ass file.

Usage:
    python align_ass.py <japanese.txt> <romaji.ass> <output.ass>

The .ass file must contain \\k-tagged karaoke lines (romaji/pinyin).
Each line in the Japanese text file is matched in order to the corresponding
karaoke event.  A warning is printed if the counts differ.

Output uses inline bracket furigana: 強[つよ]く, so Aegisub can display it
as-is, and a follow-up pass can convert to positioned ruby tags.
"""

import copy
import re
import sys
from dataclasses import dataclass

import jaconv
import pysubs2

from nlp.fugashi import is_kanji, split_okurigana, tagger


# ── Romaji normalisation ──────────────────────────────────────────────────────

def normalize_romaji(text: str) -> str:
    """Collapse romaji to bare lowercase ASCII for sequence alignment.

    We intentionally do *not* normalise romanisation-system variants (shi/si,
    tsu/tu …) here; the NW aligner tolerates small mismatches via its
    substitution score.  What matters is that both sides go through the same
    function so the strings are at least structurally comparable.
    """
    return re.sub(r"[^a-z]", "", text.lower())


# ── Japanese side ─────────────────────────────────────────────────────────────

@dataclass
class JapaneseToken:
    """One MeCab morpheme with its furigana breakdown and normalised romaji."""

    surface: str          # e.g. "強く"
    kana: str             # hiragana reading, e.g. "つよく"
    furigana_pairs: list  # from split_okurigana: [("強","つよ"), ("く",)]

    @property
    def romaji_normalized(self) -> str:
        return normalize_romaji(jaconv.kana2alphabet(self.kana))

    @property
    def display(self) -> str:
        """Inline bracket furigana: 強[つよ]く"""
        parts = []
        for pair in self.furigana_pairs:
            if len(pair) == 2:
                kanji, reading = pair
                parts.append(f"{kanji}[{reading}]")
            else:
                parts.append(pair[0])
        return "".join(parts)


@dataclass
class JapaneseLine:
    """A line of Japanese text parsed into MeCab tokens."""

    raw: str
    tokens: list[JapaneseToken]

    @classmethod
    def parse(cls, text: str) -> "JapaneseLine":
        tokens = []
        for word in tagger(text):
            surface = word.surface
            if not surface:
                continue
            if any(is_kanji(ch) for ch in surface) and word.feature.kana:
                kana = jaconv.kata2hira(word.feature.kana)
                pairs = list(split_okurigana(surface, kana))
            else:
                kana = surface
                pairs = [(surface,)]
            tokens.append(JapaneseToken(surface=surface, kana=kana, furigana_pairs=pairs))
        return cls(raw=text, tokens=tokens)

    @property
    def token_romajis(self) -> list[str]:
        """Per-token normalized romaji, context-aware for っ at morpheme boundaries.

        jaconv converts っ in isolation to 'xtsu', but in context (e.g. しった)
        it correctly produces 'shitta'.  When っ ends a token, peek at the next
        token's first consonant and replace 'xtsu' with the doubled consonant so
        the position→token mapping stays in sync with romaji_normalized.
        """
        result = []
        for i, tok in enumerate(self.tokens):
            r = normalize_romaji(jaconv.kana2alphabet(tok.kana))
            if r.endswith("xtsu") and i + 1 < len(self.tokens):
                next_r = normalize_romaji(jaconv.kana2alphabet(self.tokens[i + 1].kana))
                if next_r:
                    r = r[:-4] + next_r[0]
            result.append(r)
        return result

    @property
    def romaji_normalized(self) -> str:
        """Full-line kana→romaji conversion so っ and ん are handled in context."""
        return normalize_romaji(jaconv.kana2alphabet("".join(t.kana for t in self.tokens)))


# ── .ass side ─────────────────────────────────────────────────────────────────

# Matches {\\k30}, {\\kf30}, {\\ko30} — the three karaoke tag variants.
_K_RE = re.compile(r"\{\\k[fo]?(\d+)\}([^{]*)")


@dataclass
class KSyllable:
    """One \\k-tagged syllable from an .ass karaoke line."""

    text: str
    duration_cs: int

    @property
    def romaji_normalized(self) -> str:
        return normalize_romaji(self.text)


@dataclass
class AssLine:
    """A subtitle event broken into its constituent \\k syllables."""

    event: object           # pysubs2.SSAEvent, kept for timing/style
    syllables: list[KSyllable]

    @classmethod
    def from_event(cls, event) -> "AssLine":
        syllables = [
            KSyllable(text=m.group(2), duration_cs=int(m.group(1)))
            for m in _K_RE.finditer(event.text)
        ]
        return cls(event=event, syllables=syllables)

    @property
    def romaji_normalized(self) -> str:
        return "".join(s.romaji_normalized for s in self.syllables)


# ── Sequence alignment ────────────────────────────────────────────────────────

def _needleman_wunsch(s1: str, s2: str) -> list[tuple]:
    """
    Global pairwise character alignment (Needleman-Wunsch).
    Returns a list of (i, j) pairs where None indicates a gap.

    Scoring: match +2, mismatch -1, gap -1.
    """
    MATCH, MISMATCH, GAP = 2, -1, -1
    n, m = len(s1), len(s2)

    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = GAP * i
    for j in range(m + 1):
        dp[0][j] = GAP * j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            score = MATCH if s1[i - 1] == s2[j - 1] else MISMATCH
            dp[i][j] = max(
                dp[i - 1][j - 1] + score,
                dp[i - 1][j] + GAP,
                dp[i][j - 1] + GAP,
            )

    pairs: list[tuple] = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0:
            score = MATCH if s1[i - 1] == s2[j - 1] else MISMATCH
            if dp[i][j] == dp[i - 1][j - 1] + score:
                pairs.append((i - 1, j - 1))
                i -= 1
                j -= 1
                continue
        if i > 0 and (j == 0 or dp[i][j] == dp[i - 1][j] + GAP):
            pairs.append((i - 1, None))
            i -= 1
        else:
            pairs.append((None, j - 1))
            j -= 1

    return list(reversed(pairs))


# ── Merged result ─────────────────────────────────────────────────────────────

@dataclass
class AlignedToken:
    """A Japanese token paired with the .ass syllables it aligns to."""

    token: JapaneseToken
    syllables: list[KSyllable]

    @property
    def duration_cs(self) -> int:
        return sum(s.duration_cs for s in self.syllables)

    def to_ass_fragment(self) -> str:
        """Render as a single {\\kN}display_text fragment."""
        return f"{{\\k{self.duration_cs}}}{self.token.display}"


def align_line(jp_line: JapaneseLine, ass_line: AssLine) -> list[AlignedToken]:
    """
    Align a JapaneseLine to an AssLine via character-level romaji alignment.

    Steps:
      1. Build a flat romaji string for each side, recording which character
         position belongs to which token / syllable.
      2. Run Needleman-Wunsch on the two strings.
      3. Project the matched positions back: for each Japanese token, collect
         the set of .ass syllable indices whose characters aligned to it.
    """
    jp_rom = jp_line.romaji_normalized
    ass_rom = ass_line.romaji_normalized

    # pos → token index for the Japanese side
    # Use token_romajis (context-aware っ handling) so lengths match jp_rom.
    jp_pos_to_tok: dict[int, int] = {}
    pos = 0
    for i, tok_rom in enumerate(jp_line.token_romajis):
        for _ in tok_rom:
            jp_pos_to_tok[pos] = i
            pos += 1

    # pos → syllable index for the .ass side
    ass_pos_to_syl: dict[int, int] = {}
    pos = 0
    for i, syl in enumerate(ass_line.syllables):
        for _ in syl.romaji_normalized:
            ass_pos_to_syl[pos] = i
            pos += 1

    pairs = _needleman_wunsch(jp_rom, ass_rom)

    tok_to_syls: dict[int, set[int]] = {i: set() for i in range(len(jp_line.tokens))}
    for i, j in pairs:
        if i is not None and j is not None:
            tok_idx = jp_pos_to_tok.get(i)
            syl_idx = ass_pos_to_syl.get(j)
            if tok_idx is not None and syl_idx is not None:
                tok_to_syls[tok_idx].add(syl_idx)

    return [
        AlignedToken(
            token=tok,
            syllables=[ass_line.syllables[j] for j in sorted(tok_to_syls[i])],
        )
        for i, tok in enumerate(jp_line.tokens)
    ]


# ── Entry point ───────────────────────────────────────────────────────────────

def merge(jp_path: str, ass_path: str, out_path: str) -> None:
    with open(jp_path, encoding="utf-8") as f:
        jp_lines = [line.rstrip("\n") for line in f if line.strip()]

    subs = pysubs2.load(ass_path)
    karaoke_events = [e for e in subs.events if _K_RE.search(e.text)]

    if len(jp_lines) != len(karaoke_events):
        print(
            f"Warning: {len(jp_lines)} Japanese lines vs "
            f"{len(karaoke_events)} karaoke events — truncating to shorter list",
            file=sys.stderr,
        )

    out_subs = copy.deepcopy(subs)
    out_subs.events.clear()

    for jp_text, event in zip(jp_lines, karaoke_events):
        jp_line = JapaneseLine.parse(jp_text)
        ass_line = AssLine.from_event(event)
        aligned = align_line(jp_line, ass_line)

        new_event = copy.copy(event)
        new_event.text = "".join(a.to_ass_fragment() for a in aligned)
        out_subs.events.append(new_event)

    out_subs.save(out_path)
    print(f"Written {len(out_subs.events)} events → {out_path}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: align_ass.py <japanese.txt> <romaji.ass> <output.ass>")
        sys.exit(1)
    merge(sys.argv[1], sys.argv[2], sys.argv[3])
