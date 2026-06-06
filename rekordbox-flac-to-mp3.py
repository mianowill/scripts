#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "mutagen>=1.47.0",
#   "pyrekordbox==0.4.4",
# ]
# ///
import os
import re
import argparse
from pyrekordbox import Rekordbox6Database
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.id3 import COMM


def main():
    parser = argparse.ArgumentParser(
        description="Toggle Rekordbox tracks between FLAC and MP3"
    )
    parser.add_argument(
        "--to",
        choices=["mp3", "flac"],
        required=True,
        help="Target format to switch to (mp3 or flac)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print changes without saving them to the database or files",
    )
    args = parser.parse_args()

    print("Opening Rekordbox 6 Database...")
    try:
        db = Rekordbox6Database()
    except Exception as e:
        print(f"Error accessing database: {e}")
        print("Make sure Rekordbox is completely closed before running the script.")
        exit(1)

    # Determine regex and replacement based on the direction we are toggling
    if args.to == "mp3":
        pattern = re.compile(r".*flac$", re.IGNORECASE)
        old_ext, new_ext = "flac", "mp3"
        target_filetype = 1  # 0 or 1 = MP3
    else:
        pattern = re.compile(r".*mp3$", re.IGNORECASE)
        old_ext, new_ext = "mp3", "flac"
        target_filetype = 5  # 5 = FLAC

    matched_count = 0
    updated_count = 0

    for track in db.get_content():
        path = track.FolderPath

        if path and pattern.search(path):
            matched_count += 1
            new_path = re.compile(f"{old_ext}$", re.IGNORECASE).sub(new_ext, path)

            if not os.path.exists(new_path):
                print(f"[WARNING] Skipping missing file: {new_path}")
                continue

            if args.dry_run:
                print(f"[DRY-RUN] Would update:\n  - Old: {path}\n  - New: {new_path}")
                continue

            # 1. Read Audio File Metadata
            try:
                if args.to == "mp3":
                    audio = MP3(new_path)

                    # Convert bps to kbps
                    track.BitRate = int(audio.info.bitrate / 1000)
                    track.SampleRate = audio.info.sample_rate
                    track.Length = int(audio.info.length)

                    # Safely handle ID3 tags (create if they don't exist)
                    if audio.tags is None:
                        audio.add_tags()
                    audio.tags.add(
                        COMM(encoding=3, lang="eng", desc="", text=["FLAC available"])
                    )
                    audio.save()

                elif args.to == "flac":
                    audio = FLAC(new_path)

                    # Calculate average kbps for FLAC: (Bytes * 8) / Seconds / 1000
                    track.BitRate = int(
                        ((os.path.getsize(new_path) * 8) / audio.info.length) / 1000
                    )
                    track.SampleRate = audio.info.sample_rate
                    track.Length = int(audio.info.length)

            except Exception as e:
                print(f"[ERROR] Failed to read audio stats for {new_path}: {e}")
                continue

            # 2. Update Core Database Entries
            track.FolderPath = new_path
            track.FileName = os.path.basename(new_path)  # Important! UI relies on this
            track.FileSize = os.path.getsize(new_path)
            track.FileType = target_filetype

            # 3. Handle Pioneer's "Commnt" Typo
            current_comment = track.Commnt or ""

            if args.to == "mp3" and "FLAC available" not in current_comment:
                new_comment = f"{current_comment} [FLAC available]".strip()
                track.Commnt = new_comment
            elif args.to == "flac" and "[FLAC available]" in current_comment:
                new_comment = current_comment.replace("[FLAC available]", "").strip()
                track.Commnt = new_comment

            updated_count += 1

    print(f"\nTotal matches found: {matched_count}")
    print(f"Total files successfully scanned and updated: {updated_count}")

    if not args.dry_run:
        if updated_count > 0:
            print("Committing changes to the database...")
            db.commit()
            print("Done! You can now open Rekordbox.")
        else:
            print("No database changes were made.")


if __name__ == "__main__":
    main()
