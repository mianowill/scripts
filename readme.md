hello ! this repo is a collection of random scripts i have written for my own personal use. they are only really intended for me, so use with caution :)

### rekordbox_export.py
exports your rekordbox library to a folder. useful to get your library accessible in a platform-agnostic way (e.g. the djay app for android). non destrictive, just makes copies of your files.

### rekordbox-flac-to-mp3.py
**EDITS YOUR REKORDBOX DATABASE** to replace flac with mp3 and vice versa. allows you to export a FLAC USB for modern CDJs, then swap to mp3 and export an mp3 USB for older CDJs. does not do the conversion itself; do that yourself with something like ffmpeg. only makes changes for tracks with a flac and mp3 version in the same folder. it has a `--dry-run` option, please use it!!
