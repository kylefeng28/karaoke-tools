import hashlib
import urllib.request
import zipfile
from pathlib import Path

URL = "https://github.com/mpv-player/mpv/releases/download/v0.41.0/mpv-v0.41.0-x86_64-pc-windows-msvc.zip"
CHECKSUM = "4e197f729f5071c6772f35fffd96e0f36e3e8a044bd9479b136bb09b7c6a80ff"
ARCHIVE_NAME = Path(URL).name
CURRENT_DIR = Path(__file__).resolve().parent

def main():
    print(f"Current directory: {CURRENT_DIR}")

    print(f"Downloading {ARCHIVE_NAME}...")
    archive_path = CURRENT_DIR / ARCHIVE_NAME
    
    # Download archive
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as response, open(archive_path, "wb") as out_file:
        out_file.write(response.read())
    print("Download complete.")

    # Verify checksum
    print(f"Verifying checksum...")
    with open(archive_path, mode="rb") as archive:
        hash = hashlib.file_digest(archive, "sha256").hexdigest()
        if hash != CHECKSUM:
            raise Exception(f"SHA-256 hash does not match! expected {CHECKSUM}, got {hash}")
    print("Checksum verified.")

    # Extract contents into the current directory
    print(f"Extracting archive into {CURRENT_DIR}...")
    with zipfile.ZipFile(archive_path, mode="r") as archive:
        archive.extractall(path=CURRENT_DIR)
    print("Extraction complete.")

    # Clean up downloaded archive
    archive_path.unlink()
    print("Archive cleaned up.")

if __name__ == "__main__":
    main()
