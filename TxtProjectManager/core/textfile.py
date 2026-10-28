"""文本文件读写：自动识别编码，按原编码回写。"""

from pathlib import Path

UTF8_BOM = b"\xef\xbb\xbf"
UTF16_BOMS = (b"\xff\xfe", b"\xfe\xff")

TEXT_SUFFIXES = {
    "", ".txt", ".text", ".md", ".markdown", ".log", ".ini", ".cfg", ".conf",
    ".json", ".csv", ".tsv", ".xml", ".yaml", ".yml", ".toml", ".html", ".htm",
    ".css", ".js", ".ts", ".py", ".java", ".c", ".h", ".cpp", ".cs", ".go",
    ".rs", ".php", ".sql", ".bat", ".cmd", ".ps1", ".sh", ".properties",
    ".gitignore", ".env", ".reg", ".srt", ".vtt", ".tex",
}

BINARY_SUFFIXES = {
    ".exe", ".dll", ".sys", ".msi", ".lib", ".obj", ".pyc", ".class", ".jar",
    ".apk", ".bin", ".dat", ".db", ".sqlite", ".png", ".jpg", ".jpeg", ".gif",
    ".bmp", ".ico", ".webp", ".tif", ".tiff", ".psd", ".pdf", ".doc", ".docx",
    ".xls", ".xlsx", ".ppt", ".pptx", ".zip", ".rar", ".7z", ".gz", ".tar",
    ".bz2", ".xz", ".mp3", ".wav", ".flac", ".aac", ".mp4", ".avi", ".mkv",
    ".mov", ".wmv", ".flv", ".woff", ".woff2", ".ttf", ".otf", ".eot",
}


def read_text(path: str) -> tuple:
    """返回 (文本内容, 实际编码)。"""
    raw = Path(path).read_bytes()
    if raw.startswith(UTF8_BOM):
        return raw.decode("utf-8-sig"), "utf-8-sig"
    if raw.startswith(UTF16_BOMS):
        try:
            return raw.decode("utf-16"), "utf-16"
        except UnicodeDecodeError:
            pass
    for encoding in ("utf-8", "gb18030", "latin-1"):
        try:
            return raw.decode(encoding), encoding
        except (UnicodeDecodeError, UnicodeError):
            continue
    return raw.decode("utf-8", errors="replace"), "utf-8"


def _text_like(text: str) -> bool:
    if not text:
        return True
    bad = sum(
        1
        for ch in text
        if (ord(ch) < 32 and ch not in "\t\n\r\f\b") or 0x7F <= ord(ch) <= 0x9F
    )
    return bad / len(text) <= 0.02


def is_text_file(path: str) -> bool:
    """判断文件是否可按文本打开编辑（用于非文本文件只读展示）。"""
    target = Path(path)
    suffix = target.suffix.lower()
    if suffix in BINARY_SUFFIXES:
        return False
    if suffix in TEXT_SUFFIXES:
        return True
    try:
        raw = target.read_bytes()[:8192]
    except OSError:
        return False
    if not raw:
        return True
    if raw.startswith(UTF16_BOMS):
        sample = raw[: len(raw) - (len(raw) % 2)]
        try:
            return _text_like(sample.decode("utf-16"))
        except UnicodeDecodeError:
            return False
    if b"\x00" in raw:
        return False
    try:
        return _text_like(raw.decode("utf-8-sig"))
    except UnicodeDecodeError:
        return _text_like(raw.decode("latin-1"))


def write_text(path: str, text: str, encoding: str) -> None:
    Path(path).write_bytes(text.encode(encoding or "utf-8"))


def describe_encoding(encoding: str) -> str:
    return {
        "utf-8-sig": "UTF-8 BOM",
        "utf-8": "UTF-8",
        "gb18030": "GBK/GB18030",
        "utf-16": "UTF-16",
        "latin-1": "ANSI/Latin-1",
    }.get(encoding, encoding.upper() if encoding else "UTF-8")
