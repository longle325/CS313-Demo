from __future__ import annotations

import argparse
import json
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CREDENTIALS = Path.home() / ".config" / "earthengine" / "credentials"
SCOPES = [
    "https://www.googleapis.com/auth/drive",
]


def drive_service(credentials_path: Path):
    info = json.loads(credentials_path.read_text(encoding="utf-8"))
    if "client_id" not in info or "client_secret" not in info:
        import ee.oauth

        info = {
            **info,
            "client_id": ee.oauth.CLIENT_ID,
            "client_secret": ee.oauth.CLIENT_SECRET,
        }
    credentials = Credentials.from_authorized_user_info(info, scopes=SCOPES)
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def find_folder(service, folder_name: str) -> dict:
    response = (
        service.files()
        .list(
            q=(
                "mimeType='application/vnd.google-apps.folder' "
                f"and name='{folder_name}' and trashed=false"
            ),
            fields="files(id,name,createdTime,modifiedTime)",
            pageSize=10,
        )
        .execute()
    )
    folders = response.get("files", [])
    if not folders:
        raise FileNotFoundError(f"Could not find Drive folder named {folder_name!r}")
    folders.sort(key=lambda item: item.get("modifiedTime", ""), reverse=True)
    return folders[0]


def list_folder_files(service, folder_id: str, name_prefix: str | None) -> list[dict]:
    files: list[dict] = []
    page_token = None
    while True:
        query = f"'{folder_id}' in parents and trashed=false"
        if name_prefix:
            query += f" and name contains '{name_prefix}'"
        response = (
            service.files()
            .list(
                q=query,
                fields="nextPageToken,files(id,name,size,mimeType,modifiedTime)",
                pageSize=1000,
                pageToken=page_token,
            )
            .execute()
        )
        files.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            return sorted(files, key=lambda item: item["name"])


def download_file(service, file_info: dict, output_dir: Path, force: bool) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / file_info["name"]
    expected_size = int(file_info.get("size", 0) or 0)
    if out_path.exists() and not force and (not expected_size or out_path.stat().st_size == expected_size):
        print(f"SKIP {out_path.name}")
        return out_path

    request = service.files().get_media(fileId=file_info["id"])
    with out_path.open("wb") as handle:
        downloader = MediaIoBaseDownload(handle, request, chunksize=1024 * 1024)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"  {out_path.name}: {status.progress() * 100:.1f}%")
    print(f"DOWNLOADED {out_path.name}")
    return out_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download files from a Google Drive folder using Earth Engine OAuth credentials.")
    parser.add_argument("--folder-name", required=True)
    parser.add_argument("--name-prefix", default=None)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--credentials", type=Path, default=DEFAULT_CREDENTIALS)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    service = drive_service(args.credentials)
    folder = find_folder(service, args.folder_name)
    files = list_folder_files(service, folder["id"], args.name_prefix)
    print(f"Folder {folder['name']} ({folder['id']}): {len(files)} matching file(s)")
    for file_info in files:
        download_file(service, file_info, args.output_dir, args.force)


if __name__ == "__main__":
    main()
