"""
Converts audio files to 320k MP3s and moves them to the music directory.
"""

import os
import sys
import subprocess


DOWNLOADS_DIR = "./download"
MUSIC_DIR = os.path.expanduser("~/Music/Mia Tunes/Artists")


# find all audio files in the downloads directory
def find_audio_files(dir, audio_extensions=[".flac", ".wav", ".aiff", ".opus"]):
    audio_files = []
    for root, _, files in os.walk(dir):
        for file in files:
            if os.path.splitext(file)[1] in audio_extensions:
                audio_files.append(os.path.abspath(os.path.join(root, file)))
    return audio_files


def change_extension(file, new_extension):
    return file.replace(os.path.splitext(file)[1], new_extension)


def convert_to_mp3(file):
    ffmpeg_command = [
        "ffmpeg",
        "-i",
        file,
        "-c:a",
        "libmp3lame",
        "-b:a",
        "320k",
        "-map_metadata",
        "0",
        "-id3v2_version",
        "3",
        "-c:v",
        "copy",
        "-y",
        change_extension(file, ".mp3"),
    ]
    return subprocess.Popen(ffmpeg_command, stdout=subprocess.DEVNULL)


def main(args=[]):
    download_dir = args[0] if len(args) > 0 else DOWNLOADS_DIR
    audio_files = find_audio_files(download_dir)
    mp3s = find_audio_files(download_dir, [".mp3"])
    print(
        f"Found {len(audio_files)} audio file{'' if len(audio_files) == 1 else 's'} in {download_dir}"
    )
    if len(audio_files) == 0:
        sys.exit(1)

    process_list = []
    for file in audio_files:
        process_list.append(convert_to_mp3(file))

    for process in process_list:
        process.wait()

    # exit(0)
    for file in audio_files:
        os.remove(file)

    # import the files into the music directory
    cmd = [
        r"/Applications/MusicBrainz Picard.app/Contents/MacOS/picard-run",
        "-e",
        "CLUSTER",
        "-e",
        "LOAD",
    ]
    audio_files = [change_extension(file, ".mp3") for file in audio_files]

    cmd.extend(audio_files)
    cmd.extend(mp3s)
    subprocess.run(cmd)


if __name__ == "__main__":
    main(sys.argv[1:])
