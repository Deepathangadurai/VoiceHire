"""Upload validation: declared type + magic bytes + streamed size cap. Temp files are always removed by the caller."""
import os, tempfile
from pathlib import Path
from fastapi import UploadFile
from .errors import ServiceError

ALLOWED = {"audio/webm", "video/webm", "audio/ogg", "audio/wav", "audio/x-wav", "audio/wave", "audio/mp4", "audio/m4a", "audio/x-m4a", "audio/mpeg"}


def sniff(h: bytes) -> bool:
    return (h[:4] == b"\x1a\x45\xdf\xa3" or h[:4] == b"OggS" or (h[:4] == b"RIFF" and h[8:12] == b"WAVE")
            or h[4:8] == b"ftyp" or h[:3] == b"ID3" or (len(h) > 1 and h[0] == 0xFF and h[1] & 0xE0 == 0xE0))


async def save_upload(f: UploadFile, max_bytes: int) -> Path:
    ctype = (f.content_type or "").split(";")[0].strip().lower()
    if ctype not in ALLOWED:
        raise ServiceError("bad_audio_type", f"Unsupported audio type '{ctype or 'unknown'}'.", 415)
    fd, name = tempfile.mkstemp(prefix="vh_", suffix=".audio")
    size, first = 0, True
    try:
        with os.fdopen(fd, "wb") as out:
            while chunk := await f.read(64 * 1024):
                if first:
                    if not sniff(chunk[:16]):
                        raise ServiceError("bad_audio_content", "The file is not a recognised audio recording.", 415)
                    first = False
                size += len(chunk)
                if size > max_bytes:
                    raise ServiceError("audio_too_large", f"Recording exceeds the {max_bytes // 1_000_000} MB limit.", 413)
                out.write(chunk)
        if size == 0:
            raise ServiceError("empty_audio", "The recording was empty.", 400)
    except BaseException:
        Path(name).unlink(missing_ok=True)
        raise
    return Path(name)
