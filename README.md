# Sangeethapriya Search

Fetch search results from [Sangeethapriya.org](https://www.sangeethapriya.org), filter by raga/term, and save song data (download links, player URLs, and optional audio metadata) to JSON and text files.

## What it does

- Searches `https://www.sangeethapriya.org/fs_search.php` for your term (e.g. a raga name like **Kanakangi** or **Bhairavi**).
- Keeps only results whose filename contains the search term as a word (after splitting by `-`, `.`, `_`).
- Limits to the **first 10** matches.
- For each song, builds:
  - **Download URL** (fstream.php)
  - **Player URL** (playable page on pdx.ravisnet.com)
  - **Stream URL** (direct audio)
- Optionally runs **ffprobe** (from ffmpeg) per stream to get **duration**, **file size**, **artist**, and **composer** from the audio file.

Outputs:

- `sangeethapriya_<term>.json` — full structured data for all songs.
- `sangeethapriya_<term>_songs.txt` — human-readable list with album, artist, composer, duration, size, and URLs.

## Requirements

- **Python 3** (no specific minimum; uses only the standard library).
- **ffmpeg** (for **ffprobe**) — only if you want duration, size, artist, and composer. Without it, those fields are left empty.

### About `requirements.txt`

This project has **no pip dependencies**. The `requirements.txt` file only documents that and explains how to install **ffmpeg** on your system for the optional metadata. You do **not** need to run `pip install -r requirements.txt` for the script to work; use it as a reference for installing ffmpeg if you want metadata.

To install ffmpeg:

- **Ubuntu/Debian:** `sudo apt install ffmpeg`
- **Fedora/RHEL:** `sudo dnf install ffmpeg`
- **macOS:** `brew install ffmpeg`
- **Windows:** [ffmpeg.org/download.html](https://ffmpeg.org/download.html)

## How to run

1. Open a terminal in the project directory.

2. Run the script:
   ```bash
   python3 sangeethapriya_search.py
   ```

3. When prompted, enter a search term (e.g. `Kanakangi` or `Bhairavi`) and press Enter.

4. The script will:
   - Fetch and parse the search results
   - Filter and keep the first 10 matching songs
   - Optionally run ffprobe for each stream (unless disabled, see below)
   - Write `sangeethapriya_<term>.json` and `sangeethapriya_<term>_songs.txt`

### Environment variable

- **`SP_SKIP_DURATION`** — If set to `1`, `true`, or `yes`, the script skips all ffprobe calls. Duration, size, artist, and composer will be empty, but the script runs faster and does not require ffmpeg.
  ```bash
  SP_SKIP_DURATION=1 python3 sangeethapriya_search.py
  ```

### Example

```bash
$ python3 sangeethapriya_search.py
Enter search term (e.g. Kanakangi): Kanakangi
Fetching results for 'Kanakangi'...
Fetching audio metadata (duration, size, artist, composer)...
  10/10
Saved 10 songs to sangeethapriya_Kanakangi.json
Saved song list to sangeethapriya_Kanakangi_songs.txt
```

## Output format

**JSON** (`sangeethapriya_<term>.json`):

- `heading` — e.g. "59 files found for the pattern \"kanakangi\""
- `count` — number of songs (max 10)
- `songs` — list of objects with: `filename`, `album`, `album_url`, `download_url`, `player_url`, `stream_url`, `duration_seconds`, `size_bytes`, `artist`, `composer`

**Text** (`sangeethapriya_<term>_songs.txt`):

- One block per song: filename, album, artist (if present), composer (if present), duration, size, player URL, stream URL, download URL.

## License

Use and modify as you like. Data is from Sangeethapriya.org; respect their terms of service and copyright.
