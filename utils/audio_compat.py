"""
audio_compat.py
Drop-in AudioSegment replacement using ffmpeg/ffprobe.

Replaces pydub for Python 3.13+ compatibility (audioop was removed in 3.13).
Requires ffmpeg and ffprobe to be installed and available on PATH.
"""

import json
import os
import shutil
import subprocess
import tempfile

_tmp_dir = tempfile.mkdtemp(prefix="audio_compat_")
_counter = 0


def _next_path(suffix=".mp3"):
    global _counter
    _counter += 1
    return os.path.join(_tmp_dir, f"seg_{_counter:06d}{suffix}")


def _ffmpeg(*args):
    result = subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error"] + list(args),
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr.decode()}")


def _probe_duration_ms(path: str) -> int:
    result = subprocess.run(
        [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")
    data = json.loads(result.stdout)
    return round(float(data["format"]["duration"]) * 1000)


class AudioSegment:
    """Minimal AudioSegment shim backed by ffmpeg temp files."""

    def __init__(self, path: str | None, duration_ms: int | None = None):
        self._path = str(path) if path else None
        self._duration_ms = duration_ms

    # ------------------------------------------------------------------
    # Duration
    # ------------------------------------------------------------------

    def _get_ms(self) -> int:
        if self._duration_ms is None and self._path:
            self._duration_ms = _probe_duration_ms(self._path)
        return self._duration_ms or 0

    def __len__(self) -> int:
        return self._get_ms()

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def from_mp3(cls, path: str) -> "AudioSegment":
        return cls(path)

    @classmethod
    def silent(cls, duration: int) -> "AudioSegment":
        """Create a silent MP3 of *duration* milliseconds."""
        if duration <= 0:
            duration = 1  # ffmpeg needs at least a tiny duration
        path = _next_path()
        _ffmpeg(
            "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=stereo",
            "-t", str(duration / 1000.0),
            "-q:a", "9",
            path,
        )
        return cls(path, duration)

    @classmethod
    def empty(cls) -> "AudioSegment":
        """Return a zero-length placeholder (identity element for concatenation)."""
        inst = object.__new__(cls)
        inst._path = None
        inst._duration_ms = 0
        return inst

    # ------------------------------------------------------------------
    # Operators
    # ------------------------------------------------------------------

    def __add__(self, other: "AudioSegment | int | float") -> "AudioSegment":
        if isinstance(other, (int, float)):
            return self._apply_volume_db(other)
        return self._concat(other)

    def __radd__(self, other):
        # Supports: int + AudioSegment (shouldn't happen but guard it)
        if other == 0:
            return self
        return NotImplemented

    def __iadd__(self, other):
        return self.__add__(other)

    def __mul__(self, n: int) -> "AudioSegment":
        """Repeat this segment n times."""
        if n <= 0:
            return AudioSegment.empty()
        if n == 1 or self._path is None:
            return AudioSegment(self._path, self._duration_ms)
        result = self
        for _ in range(n - 1):
            result = result._concat(self)
        return result

    def __getitem__(self, sl: slice) -> "AudioSegment":
        """Trim by milliseconds: seg[start_ms:stop_ms]."""
        if not isinstance(sl, slice):
            raise TypeError("only slice indexing is supported")
        total = self._get_ms()
        start_ms = sl.start if sl.start is not None else 0
        stop_ms = sl.stop if sl.stop is not None else total
        duration_ms = max(0, stop_ms - start_ms)
        if duration_ms == 0 or self._path is None:
            return AudioSegment.silent(1)
        path = _next_path()
        _ffmpeg(
            "-ss", str(start_ms / 1000.0),
            "-i", self._path,
            "-t", str(duration_ms / 1000.0),
            "-c", "copy",
            path,
        )
        return AudioSegment(path, duration_ms)

    # ------------------------------------------------------------------
    # Audio operations
    # ------------------------------------------------------------------

    def _concat(self, other: "AudioSegment") -> "AudioSegment":
        if self._path is None or self._get_ms() == 0:
            return AudioSegment(other._path, other._duration_ms)
        if other._path is None or other._get_ms() == 0:
            return AudioSegment(self._path, self._duration_ms)
        concat_list = _next_path(".txt")
        out = _next_path()
        with open(concat_list, "w") as f:
            f.write(f"file '{self._path}'\n")
            f.write(f"file '{other._path}'\n")
        _ffmpeg(
            "-f", "concat", "-safe", "0",
            "-i", concat_list,
            "-c", "copy",
            out,
        )
        return AudioSegment(out)

    def _apply_volume_db(self, db: float) -> "AudioSegment":
        if self._path is None:
            return AudioSegment.empty()
        vol = 10 ** (db / 20.0)
        out = _next_path()
        _ffmpeg(
            "-i", self._path,
            "-af", f"volume={vol:.6f}",
            out,
        )
        return AudioSegment(out)

    def fade_out(self, duration: int) -> "AudioSegment":
        """Apply a fade-out of *duration* milliseconds at the end."""
        if self._path is None:
            return AudioSegment.empty()
        total_ms = self._get_ms()
        start_s = max(0.0, (total_ms - duration) / 1000.0)
        out = _next_path()
        _ffmpeg(
            "-i", self._path,
            "-af", f"afade=t=out:st={start_s:.3f}:d={duration / 1000.0:.3f}",
            out,
        )
        return AudioSegment(out, total_ms)

    def overlay(self, other: "AudioSegment") -> "AudioSegment":
        """Mix *other* on top of self (self sets the length)."""
        if self._path is None:
            return AudioSegment(other._path, other._duration_ms)
        if other._path is None:
            return AudioSegment(self._path, self._duration_ms)
        out = _next_path()
        _ffmpeg(
            "-i", self._path,
            "-i", other._path,
            "-filter_complex",
            "amix=inputs=2:duration=first:dropout_transition=0",
            out,
        )
        return AudioSegment(out)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export(self, path: str, format: str = "mp3") -> None:
        path = str(path)
        if self._path is None:
            # Export empty → 1 ms silence
            AudioSegment.silent(1).export(path, format=format)
            return
        src_ext = os.path.splitext(self._path)[1].lstrip(".")
        if src_ext == format:
            shutil.copy2(self._path, path)
        else:
            _ffmpeg("-i", self._path, path)
