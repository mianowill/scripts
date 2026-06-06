#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "mutagen>=1.47.0",
#   "pyrekordbox==0.4.4",
# ]
# ///
"""
Rekordbox Playlist Exporter
----------------------------
This script exports playlists from Rekordbox into directories replicating the playlist structure to be used as a platform-agnostic backup or for use in other DJ software.
ID3 tags are updated with track title and BPM.
Very likely will not work on Windows. Tested on macOS. Pretty safe to run (though please use --dry-run first) but is like 70% vibe coded so use at your own risk.
"""

import argparse
import logging
import re
import shutil
from pathlib import Path
from typing import Any
from urllib.parse import unquote


from pyrekordbox import Rekordbox6Database
from mutagen.id3 import ID3, TIT2, TBP

# --- Configuration & Constants ---
DEFAULT_BACKUP_DIR = "/tmp/rekordboxBackup"
DEFAULT_MAX_SONGS = 500
ILLEGAL_CHARS_REGEX = re.compile(r'[\\/:*?"<>|]')


def setup_logging(log_level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(message)s",
    )


def sanitize_filename(name: str) -> str:
    return ILLEGAL_CHARS_REGEX.sub("_", name)


def update_metadata(file_path: Path, title: str, bpm: int) -> None:
    """Writes sequence-numbered title and metadata to the destination file."""
    try:
        audio = ID3(file_path)
    except Exception:
        # Create tags if they don't exist
        audio = ID3()

    audio.add(TIT2(encoding=3, text=title))
    audio.add(TBP(encoding=3, text=str(bpm)))

    audio.save(file_path)
    logging.debug(f"Updated ID3 for {file_path.name}")


def process_playlist_node(
    node: Any,
    current_path: Path,
    args: argparse.Namespace,
    require_prompt: bool,
    depth: int = 0,
    index: int = 1,
    total_siblings: int = 1,
) -> None:
    folder_pad = max(2, len(str(total_siblings)))
    safe_node_name = sanitize_filename(f"{str(index).zfill(folder_pad)} {node.Name}")
    target_dir = current_path / safe_node_name

    if require_prompt:
        ans = input(f"\nProcess root '{node.Name}'? [y/N]: ").strip().lower()
        if ans not in ("y", "yes"):
            return

    if node.Children:
        if args.dry_run:
            print(f"{'    ' * depth}📁 {safe_node_name}/")
        else:
            target_dir.mkdir(parents=True, exist_ok=True)

        sorted_children = sorted(node.Children, key=lambda x: x.Name)
        for i, child in enumerate(sorted_children, start=1):
            process_playlist_node(
                child, target_dir, args, False, depth + 1, i, len(sorted_children)
            )
        return

    songs = getattr(node, "Songs", [])
    if len(songs) >= args.max_songs or not songs:
        logging.debug(
            f"Skipping '{node.Name}' with {len(songs)} tracks (limit: {args.max_songs})"
        )
        return

    if args.dry_run:
        print(f"{'    ' * depth}🎵 {safe_node_name}/ ({len(songs)} tracks)")
    else:
        target_dir.mkdir(parents=True, exist_ok=True)

    track_pad = max(2, len(str(len(songs))))

    for idx, song in enumerate(songs, start=1):
        content = song.Content
        if not content:
            continue

        # Resolve paths
        raw_path = unquote(content.FolderPath.replace("file://localhost", ""))
        src_path = (
            Path(raw_path) / content.FileNameL
            if Path(raw_path).is_dir()
            else Path(raw_path)
        )

        if not src_path.exists() and not args.dry_run:
            logging.warning(f"File missing: {src_path}")
            continue

        seq_str = str(idx).zfill(track_pad)
        artist = content.Artist.Name if content.Artist else ""
        title = content.Title or "Unknown"
        bpm = content.BPM // 100 if content.BPM else 0

        # Format Destination
        dest_filename = sanitize_filename(
            f"{seq_str} {artist} - {title} [{bpm}]{src_path.suffix}"
        )
        dest_path = target_dir / dest_filename

        if args.dry_run:
            print(f"{'    ' * (depth + 1)} ↳ {dest_filename}")
        else:
            shutil.copy2(src_path, dest_path)
            update_metadata(dest_path, title, bpm)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path(DEFAULT_BACKUP_DIR))
    parser.add_argument("--max-songs", type=int, default=DEFAULT_MAX_SONGS)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--log-level", type=str, default="INFO")
    args = parser.parse_args()

    setup_logging(args.log_level)
    db = Rekordbox6Database()

    root_nodes = sorted(
        [p for p in db.get_playlist() if getattr(p, "ParentID", None) == "root"],
        key=lambda x: x.Name,
    )
    for i, node in enumerate(root_nodes, start=1):
        process_playlist_node(node, args.out, args, True, 0, i, len(root_nodes))


if __name__ == "__main__":
    main()
