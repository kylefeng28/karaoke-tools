"""
merge.py: merge k-timed hiragana ASS syllables with Japanese orthography.

Algorithm (ASS-driven greedy match):
  1. Flatten JP text into a stream of (surface, hiragana_reading) tokens,
     stripping parenthetical English annotations and punctuation.
     The stream is cyclic so that repeated chorus sections in the ASS are handled.
  2. Drive iteration over the ASS syllables (authoritative source of timings/lines).
     For each hiragana syllable:
       a. Uppercase syllables (loanwords) pass through unchanged.
       b. Try to match the syllable against the current position of the current JP token.
          Normalise particle variants (わ↔は, を↔を, え↔へ) before comparing.
       c. On match: accumulate. When the full token reading is consumed, emit the
          surface+reading as a TimedWord.
       d. On mismatch: scan forward in the JP token stream (up to MAX_SKIP tokens)
          to find the next token whose reading starts with this syllable.
          Non-matching tokens in between are silently skipped (they correspond to
          lyrics phrases not timed in this ASS.
          If no match is found within MAX_SKIP, emit the syllable as-is and
          advance the JP stream by one.
  3. Token + position state carries across ASS line boundaries.
"""

import re
import unicodedata
import jaconv
import pysubs2
from dataclasses import dataclass

from subs import parse_k_timing, TimedSyllable, TimedWord
from nlp import tagger
from utils import is_kanji


# ── formatting ────────────────────────────────────────────────────────────────
def _emit(surface: str, syls: list[TimedSyllable]) -> str:
    return TimedWord(surface, syls)


# ── particle normalisation ────────────────────────────────────────────────────

_PTABLE = str.maketrans('はをへ', 'わおえ')

def _norm(s: str) -> str:
    """Normalize は→わ, を→お, へ→え so romanized particles match JP orthography."""
    return s.strip().translate(_PTABLE)


# ── JP token stream ───────────────────────────────────────────────────────────

def _jp_tokens(jp_lines: list[str]) -> list[tuple[str, str]]:
    """
    Flatten all JP text lines into (surface, hiragana_reading) pairs.
    Strips parenthetical English annotations, whitespace, and punctuation-only tokens.
    """
    tokens = []
    for line in jp_lines:
        clean = re.sub(r'\s*\([^)]*\)', '', line).strip()
        for word in tagger(clean):
            surface = word.surface
            if not surface or surface.isspace() or surface == '\u3000':
                continue
            if all(unicodedata.category(ch).startswith(('P', 'S', 'Z')) for ch in surface):
                continue
            kana = word.feature.kana
            reading = jaconv.kata2hira(kana) if kana else surface
            tokens.append((surface, reading))
    return tokens


class _PeekIter:
    """
    List-backed iterator with look-ahead, position save/restore, and wrap-around.
    """

    def __init__(self, tokens: list):
        self._tokens = tokens
        self._pos = 0

    def peek(self, offset: int = 0):
        """Return item at current_pos + offset without consuming. None if exhausted."""
        idx = self._pos + offset
        return self._tokens[idx] if idx < len(self._tokens) else None

    def pop(self):
        """Consume and return the next item. Caller must check peek() first."""
        if self._pos >= len(self._tokens):
            raise StopIteration
        item = self._tokens[self._pos]
        self._pos += 1
        return item

    def skip(self, n: int):
        """Discard the next n items."""
        self._pos = min(self._pos + n, len(self._tokens))

    def position(self) -> int:
        return self._pos

    def reset(self):
        self._pos = 0

    def seek(self, pos: int):
        self._pos = pos


@dataclass
class MergeState:
    token: str
    pos: int
    buf: list[str]

    def set_token(self, token):
        self.token = token; self.pos = 0; self.buf = []

# ── core merge ────────────────────────────────────────────────────────────────

MAX_SKIP = 5   # max JP tokens to scan ahead on a mismatch


def merge_line(syls: list[TimedSyllable], jp: _PeekIter, state: MergeState) -> str:
    """
    Merge one ASS line's syllables against the JP token stream.

    state carries in-progress token across ASS line boundaries:
      state.token  - (surface, reading) being consumed, or None
      state.pos    - chars consumed within reading
      state.buf    - TimedSyllable list accumulated for current token
    """
    result = []

    def flush():
        if state.buf and state.token:
            result.append(_emit(state.token[0], state.buf))
            state.set_token(None)

    def load():
        """Load next token from stream into state. Return False if exhausted."""
        item = jp.peek()
        if item is None:
            return False
        jp.pop()
        state.set_token(item)
        return True

    for syl in syls:
        # Uppercase = loanword, pass through
        if syl.text.isupper():
            flush()
            result.append(syl)
            continue

        # Load token if needed
        if state.token is None:
            if not load():
                result.append(syl)
                continue

        surface, reading = state.token
        remaining = _norm(reading[state.pos:])

        if remaining.startswith(_norm(syl.text)):
            # Match
            state.buf.append(syl)
            state.pos += len(syl.text)
            if state.pos >= len(reading):
                result.append(_emit(surface, state.buf))
                state.token = None; state.pos = 0; state.buf = []
        else:
            # Mismatch: flush partial buffer and scan ahead for a matching token.
            # JP lines that don't appear in the ASS (e.g. "ありがとう悲しみよ")
            # are silently skipped here.
            flush()

            # Include the current in-progress token as offset 0 in the scan
            # (it's still in state but we already confirmed it doesn't match)
            found_at = None
            for offset in range(MAX_SKIP + 1):
                candidate = jp.peek(offset)
                if candidate is None:
                    break
                _, cand_reading = candidate
                if _norm(cand_reading).startswith(_norm(syl.text)):
                    found_at = offset
                    break

            if found_at is not None:
                # Discard skipped tokens, load the matching one
                jp.skip(found_at)
                load()
                surface2, reading2 = state.token
                state.buf = [syl]
                state.pos = len(syl.text)
                if state.pos >= len(reading2):
                    result.append(_emit(surface2, state.buf))
                    state.token = None; state.pos = 0; state.pos = []
            else:
                # No match in forward window. Try resetting the stream to its start.
                # this handles chorus reprises where the ASS loops but JP doesn't.
                saved_pos = jp.position()
                jp.reset()
                found_reset = None
                for offset in range(MAX_SKIP + 1):
                    candidate = jp.peek(offset)
                    if candidate is None:
                        break
                    _, cand_reading = candidate
                    if _norm(cand_reading).startswith(_norm(syl.text)):
                        found_reset = offset
                        break
                if found_reset is not None:
                    jp.skip(found_reset)
                    load()
                    surface2, reading2 = state.token
                    state.buf = [syl]
                    state.pos = len(syl.text)
                    if state.pos >= len(reading2):
                        result.append(_emit(surface2, state.buf))
                        state.token = None; state.pos = 0; state.buf = []
                else:
                    # Truly no match: restore position and emit as-is
                    jp.seek(saved_pos)
                    result.append(_emit(syl.text, [syl]))

    return result


# ── public entry point ────────────────────────────────────────────────────────

def merge_files(ass_path: str, jp_path: str):
    """Merge a k-timed romaji .ass with a Japanese text file, print one line per ASS line."""
    ass_sub = pysubs2.load(ass_path)
    with open(jp_path, encoding='utf-8') as f:
        jp_lines = [l.rstrip('\n') for l in f if l.strip()]

    tokens = _jp_tokens(jp_lines)
    # PeekIter wraps around automatically so chorus repeats in the ASS re-use JP tokens
    jp = _PeekIter(tokens)
    state = MergeState(token=None, pos=0, buf=[])

    for ass_line in ass_sub:
        if ass_line.text.startswith('!'):
            continue

        words = parse_k_timing(ass_line.text)
        for w in words:
            w.convert_hiragana()
        syls = [s for w in words for s in w.syllables]
        merged_line = merge_line(syls, jp, state)

        for word in merged_line:
            print(word, end='\t')

        print()
