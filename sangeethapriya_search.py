# Sangeethapriya search: fetch results, filter by term, optional ffprobe metadata. Usage: python sangeethapriya_search.py

import base64
import json
import os
import re
import subprocess
import urllib.parse
import urllib.request

FSTREAM_BASE = "https://www.sangeethamshare.org/fstream.php"
SERVER_ROOT = "/home/data/www.sangeethamshare.org/public_html"
PLAYER_BASE = "http://pdx.ravisnet.com:8080/player2.php"
STREAM_BASE = "http://pdx.ravisnet.com:8080"
PLAYER_PATH_PREFIX = "sangeethamshare.org/public_html"
SEARCH_RESULTS_RE = re.compile(
    r'<div\s+id="searchresults">(.*?)</div>\s*</div>\s*<div\s+id="sidebar">',
    re.DOTALL,
)
LI_PATTERN = re.compile(
    r'<li>\s*([^<]+?)\s*-\s*<a\s+href="([^"]+)">([^<]*)</a>\s*</li>',
    re.IGNORECASE,
)


def _headers():
    return {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }


def _decode_response(data: bytes, resp) -> str:
    charset = resp.headers.get_content_charset()
    for enc in (charset, "utf-8", "iso-8859-1", "cp1252"):
        if enc:
            try:
                return data.decode(enc)
            except (LookupError, UnicodeDecodeError):
                pass
    return data.decode("iso-8859-1", errors="replace")


def fetch_search(query: str) -> str:
    url = f"https://www.sangeethapriya.org/fs_search.php?{urllib.parse.urlencode({'q': query})}"
    req = urllib.request.Request(url, headers=_headers())
    with urllib.request.urlopen(req, timeout=30) as resp:
        return _decode_response(resp.read(), resp)


def filename_matches_search(filename: str, search: str) -> bool:
    if not search.strip():
        return True
    q = search.strip().lower()
    return any(p.strip().lower() == q for p in re.split(r"[-._]", filename))


def _path_from_album_url(album_url: str) -> str:
    return (urllib.parse.urlparse(album_url).path or "").strip().rstrip("/").lstrip("/")


def build_fstream_download_url(album_url: str, filename: str) -> str:
    path = _path_from_album_url(album_url)
    return f"{FSTREAM_BASE}?file={urllib.parse.quote(f'{SERVER_ROOT}/{path}/{filename}', safe='/')}"


def build_player_url(album_url: str, filename: str) -> str:
    path = _path_from_album_url(album_url)
    b64_b = base64.standard_b64encode(f"{PLAYER_PATH_PREFIX}/{path}/".encode()).decode()
    b64_t = base64.standard_b64encode(filename.encode()).decode()
    return f"{PLAYER_BASE}?b={b64_b}&t={b64_t}"


def build_stream_url(album_url: str, filename: str) -> str:
    path = _path_from_album_url(album_url)
    return f"{STREAM_BASE}/{PLAYER_PATH_PREFIX}/{path}/{urllib.parse.quote(filename, safe='')}"


def get_audio_metadata(stream_url: str) -> tuple[float | None, int | None, str | None, str | None]:
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", stream_url],
            capture_output=True, timeout=30,
        )
        if r.returncode != 0:
            return None, None, None, None
        fmt = (json.loads(r.stdout.decode()).get("format") or {})
        dur = fmt.get("duration")
        size = fmt.get("size")
        tags = fmt.get("tags") or {}
        artist = (tags.get("artist") or tags.get("ARTIST") or "").strip() or None
        composer = (tags.get("composer") or tags.get("COMPOSER") or tags.get("TCOM") or "").strip() or None
        return (
            float(dur) if dur is not None else None,
            int(size) if size is not None else None,
            artist, composer,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None, None, None, None


def _fmt_duration(sec: float | None) -> str:
    if sec is None:
        return "—"
    m, s = int(sec) // 60, int(sec) % 60
    return f"{m}:{s:02d}"


def _fmt_size(n: int | None) -> str:
    if n is None:
        return "—"
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{int(n)} B" if u == "B" else f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} TB"


def scrape_song_data(html: str) -> tuple[str, list[dict]]:
    m = re.search(r'<h1>([^<]*files found for the pattern[^<]*)</h1>', html, re.I)
    heading = m.group(1).strip() if m else ""
    match = SEARCH_RESULTS_RE.search(html)
    block = match.group(1) if match else html
    songs = []
    for m in LI_PATTERN.finditer(block):
        fn, album_url, album = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
        songs.append({
            "filename": fn,
            "album": album,
            "album_url": album_url,
            "download_url": build_fstream_download_url(album_url, fn),
            "player_url": build_player_url(album_url, fn),
            "stream_url": build_stream_url(album_url, fn),
        })
    return heading, songs


def main() -> None:
    query = input("Enter search term (e.g. Kanakangi): ").strip()
    if not query:
        print("No search term entered. Exiting.")
        return
    try:
        html = fetch_search(query)
    except Exception as e:
        print(f"Error fetching data: {e}")
        return
    heading, songs = scrape_song_data(html)
    songs = [s for s in songs if filename_matches_search(s["filename"], query)][:10]

    skip_meta = os.environ.get("SP_SKIP_DURATION", "").strip().lower() in ("1", "true", "yes")
    for s in songs:
        s["duration_seconds"] = s["size_bytes"] = s["artist"] = s["composer"] = None
    if songs and not skip_meta:
        print("Fetching audio metadata (duration, size, artist, composer)...")
        for i, s in enumerate(songs):
            dur, size, artist, composer = get_audio_metadata(s["stream_url"])
            s["duration_seconds"] = round(dur, 1) if dur is not None else None
            s["size_bytes"] = size
            s["artist"] = artist
            s["composer"] = composer
            if (i + 1) % 10 == 0 or (i + 1) == len(songs):
                print(f"  {i + 1}/{len(songs)}")

    safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in query)
    base_name = f"sangeethapriya_{safe_name}"
    with open(f"{base_name}.json", "w", encoding="utf-8") as f:
        json.dump({"heading": heading, "count": len(songs), "songs": songs}, f, indent=2)
    print(f"Saved {len(songs)} songs to {base_name}.json")

    lines = [heading, ""]
    for i, s in enumerate(songs, 1):
        lines.append(f"{i}. {s['filename']}")
        lines.append(f"   Album: {s['album']}")
        if s.get("artist"):
            lines.append(f"   Artist: {s['artist']}")
        if s.get("composer"):
            lines.append(f"   Composer: {s['composer']}")
        lines.append(f"   Duration: {_fmt_duration(s.get('duration_seconds'))}")
        lines.append(f"   Size: {_fmt_size(s.get('size_bytes'))}")
        lines.append(f"   Player URL:  {s['player_url']}")
        lines.append(f"   Stream URL: {s['stream_url']}")
        lines.append(f"   Download URL: {s['download_url']}")
        lines.append("")
    with open(f"{base_name}_songs.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Saved song list to {base_name}_songs.txt")


if __name__ == "__main__":
    main()
