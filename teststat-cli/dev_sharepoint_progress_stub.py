"""SharePoint progress display stub.

This script exercises the SharePoint download progress UI without Azure CLI,
Microsoft Graph, or network access.
"""

import argparse
import sys
import time
from unittest.mock import patch

from utils import RemoteSource


class FakeDownloadResponse:
    def __init__(self, total_bytes, chunk_delay):
        self.remaining = total_bytes
        self.headers = {"Content-Length": str(total_bytes)}
        self.chunk_delay = chunk_delay

    def read(self, size=-1):
        if self.remaining <= 0:
            return b""
        if size is None or size < 0:
            size = self.remaining
        count = min(size, self.remaining)
        self.remaining -= count
        if self.chunk_delay:
            time.sleep(self.chunk_delay)
        return b"x" * count

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def parse_args():
    parser = argparse.ArgumentParser(
        description="SharePoint download progress display stub"
    )
    parser.add_argument("--files", type=int, default=3, help="number of fake files")
    parser.add_argument("--size-mb", type=float, default=8.0, help="fake file size in MB")
    parser.add_argument(
        "--delay",
        type=float,
        default=0.05,
        help="delay per downloaded chunk in seconds",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    total_bytes = max(1, int(args.size_mb * 1024 * 1024))
    file_total = max(1, args.files)

    def fake_resolve_download_url(share_id, token, **kwargs):
        index = fake_resolve_download_url.calls + 1
        fake_resolve_download_url.calls = index
        return f"stub-file-{index}.xlsx", f"https://download.example/stub/{index}"

    fake_resolve_download_url.calls = 0

    def fake_urlopen(req, timeout=None):
        return FakeDownloadResponse(total_bytes, args.delay)

    config = {"cleanup": True, "timeout_sec": 60}
    with patch("utils.RemoteSource.get_access_token", return_value="stub-token"), \
            patch("utils.RemoteSource.resolve_download_url", side_effect=fake_resolve_download_url), \
            patch("utils.RemoteSource.urllib.request.urlopen", side_effect=fake_urlopen):
        with RemoteSource.RemoteFileManager(config) as manager:
            for index in range(1, file_total + 1):
                label = f"LABEL_{index}"
                url = f"https://contoso.sharepoint.com/:x:/s/stub/file-{index}"
                manager.fetch(
                    url,
                    label=label,
                    item_index=index,
                    item_total=file_total,
                    progress_stream=sys.stdout,
                )


if __name__ == "__main__":
    main()
