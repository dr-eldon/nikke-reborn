"""The Nexus Mods API v3 client (https://api.nexusmods.com/v3): the
authenticated JSON calls the ``publish`` command needs against one mod
(the mod's details, its files and their versions, its changelog, and
the create file/version and append-changelog calls) plus the multipart
upload session — the presigned part PUTs, the S3 completion, the
finalise, and the poll until the upload is ``available`` — behind one
:meth:`NexusClient.upload` call.

Every authenticated call carries the ``apikey`` header (the presigned
S3 URLs are called without it). A failed call raises
:exc:`nikke_reborn.error.PublishError`, carrying the API's problem
``detail`` where the response has one. A part's PUT is retried on
connection errors (the same bytes to the same URL are idempotent) but
never on an HTTP error, and the upload is polled to ``available`` with
exponential backoff under a 30-minute deadline."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from nikke_reborn.error import PublishError

API_URL = "https://api.nexusmods.com/v3"
USER_AGENT = "nikke-reborn"

JSON_TIMEOUT = 30
PART_TIMEOUT = 60

PART_ATTEMPTS = 4
PART_RETRY_DELAY = 5

POLL_START = 2
POLL_CAP = 10
AVAILABLE_DEADLINE = 30 * 60

CHANGELOG_PAGE_SIZE = 100


@dataclass
class ModInfo:
    """The mod page's headline fields."""

    name: str
    version: str
    status: str


@dataclass
class RemoteFile:
    """A file on the mod page."""

    name: str
    file_id: str


@dataclass
class RemoteFileVersion:
    """One of a remote file's versions (``position`` orders the
    versions; the highest is the current one)."""

    version: str
    description: str | None
    category: str
    position: float


@dataclass
class ChangelogEntry:
    """The changelog text of one mod version."""

    version: str
    entries: list[str]


@dataclass
class CreatedFileVersion:
    """The identifiers a new file version's creation returns."""

    file_id: str
    version_id: str


class _Window:
    """A read-only view over one byte range of an open file: it seeks
    the file to the range's start and hands out exactly the range's
    bytes, so a part streams to its presigned URL one chunk at a time
    (never the rest of the archive) and a retried part simply starts a
    fresh window."""

    def __init__(self, file: BinaryIO, start: int, end: int) -> None:
        self._file = file
        self._position = start
        self._end = end
        file.seek(start)

    def read(self, size: int = -1) -> bytes:
        remaining = self._end - self._position
        if remaining <= 0:
            return b""
        if size >= 0:
            remaining = min(remaining, size)
        data = self._file.read(remaining)
        self._position += len(data)
        return data


def _problem_detail(error: urllib.error.HTTPError) -> str:
    """The API's problem ``detail`` for a failed response, or the
    transport reason where the body carries none."""
    try:
        problem = json.loads(error.read().decode())
    except (ValueError, OSError):
        return str(error.reason)
    detail = problem.get("detail")
    return detail if isinstance(detail, str) else str(error.reason)


def _reason(error: object) -> str:
    return str(getattr(error, "reason", error))


class NexusClient:
    """An authenticated Nexus Mods API client bound to one mod."""

    def __init__(self, api_key: str, mod_id: str) -> None:
        self._api_key = api_key
        self._mod_id = mod_id

    def mod_details(self) -> ModInfo:
        data = self._call("GET", f"/mods/{self._mod_id}")["data"]
        return ModInfo(
            name=data["name"], version=data["version"], status=data["status"]
        )

    def files(self) -> list[RemoteFile]:
        data = self._call("GET", f"/mods/{self._mod_id}/files")["data"]
        return [
            RemoteFile(name=file["name"], file_id=file["id"])
            for file in data["mod_files"]
        ]

    def file_versions(self, file_id: str) -> list[RemoteFileVersion]:
        data = self._call("GET", f"/mod-files/{file_id}/versions")["data"]
        return [
            RemoteFileVersion(
                version=item["version"],
                description=item["description"],
                category=item["category"],
                position=float(item["position"]),
            )
            for item in data["versions"]
        ]

    def changelogs(self) -> list[ChangelogEntry]:
        entries: list[ChangelogEntry] = []
        page = 1
        while True:
            body = self._call(
                "GET",
                f"/mods/{self._mod_id}/changelogs"
                f"?page={page}&page_size={CHANGELOG_PAGE_SIZE}",
            )
            items = body["data"]
            entries.extend(
                ChangelogEntry(version=item["version"], entries=item["entries"])
                for item in items
            )
            if len(items) < CHANGELOG_PAGE_SIZE:
                break
            page += 1
        return entries

    def append_changelog(self, version: str, changelog: str) -> None:
        self._call(
            "POST",
            f"/mods/{self._mod_id}/changelogs",
            {"version": version, "changelog": changelog},
        )

    def upload(self, path: Path) -> str:
        """Upload *path* through one multipart session and wait until
        the upload is ``available``; its upload id (for the create
        file/version call) is returned."""
        file_size = path.stat().st_size
        session = self._call(
            "POST",
            "/uploads/multipart",
            {"size_bytes": file_size, "filename": path.name},
        )["data"]
        part_size = session["part_size_bytes"]
        part_urls = session["part_presigned_urls"]
        part_count = len(part_urls)
        etags = []
        with path.open("rb") as file:
            for number, url in enumerate(part_urls, start=1):
                start = (number - 1) * part_size
                end = min(file_size, start + part_size)
                etags.append(self._put_part(file, url, start, end))
                print(f"{path.name}: part {number}/{part_count}")
        self._complete(session["complete_presigned_url"], etags)
        self._call("POST", f"/uploads/{session['id']}/finalise")
        self._wait_available(session["id"])
        return session["id"]

    def create_file_version(
        self,
        upload_id: str,
        file_id: str,
        name: str,
        version: str,
        file_category: str,
        description: str,
        update_mod_version: bool,
    ) -> CreatedFileVersion:
        data = self._call(
            "POST",
            f"/mod-files/{file_id}/versions",
            {
                "upload_id": upload_id,
                "name": name,
                "version": version,
                "file_category": file_category,
                "description": description,
                "update_mod_version": update_mod_version,
            },
        )["data"]
        return CreatedFileVersion(
            file_id=data["file"]["id"], version_id=data["version"]["id"]
        )

    def create_file(
        self,
        upload_id: str,
        name: str,
        version: str,
        file_category: str,
        description: str,
        update_mod_version: bool,
    ) -> str:
        data = self._call(
            "POST",
            "/mod-files",
            {
                "upload_id": upload_id,
                "mod_id": self._mod_id,
                "name": name,
                "version": version,
                "file_category": file_category,
                "description": description,
                "update_mod_version": update_mod_version,
            },
        )["data"]
        return data["id"]

    def _call(self, method: str, path: str, body: dict | None = None) -> dict:
        url = f"{API_URL}{path}"
        payload = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(url, data=payload, method=method)
        request.add_header("apikey", self._api_key)
        request.add_header("Content-Type", "application/json")
        request.add_header("User-Agent", USER_AGENT)
        try:
            with urllib.request.urlopen(request, timeout=JSON_TIMEOUT) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as error:
            message = f"{method} {path} failed ({error.code}): {_problem_detail(error)}"
            raise PublishError(message) from error
        except (urllib.error.URLError, OSError) as error:
            message = f"{method} {path} failed: {_reason(error)}"
            raise PublishError(message) from error

    def _put_part(self, file: BinaryIO, url: str, start: int, end: int) -> str:
        for attempt in range(1, PART_ATTEMPTS + 1):
            request = urllib.request.Request(
                url, data=_Window(file, start, end), method="PUT"
            )
            request.add_header("Content-Type", "application/octet-stream")
            request.add_header("Content-Length", str(end - start))
            try:
                with urllib.request.urlopen(request, timeout=PART_TIMEOUT) as response:
                    return response.headers["ETag"].strip('"')
            except urllib.error.HTTPError as error:
                message = f"part upload failed ({error.code}): {_problem_detail(error)}"
                raise PublishError(message) from error
            except (urllib.error.URLError, OSError) as error:
                if attempt == PART_ATTEMPTS:
                    message = (
                        f"part upload failed after {PART_ATTEMPTS} attempts: "
                        f"{_reason(error)}"
                    )
                    raise PublishError(message) from error
                time.sleep(PART_RETRY_DELAY * attempt)

    def _complete(self, url: str, etags: list[str]) -> None:
        parts = "\n".join(
            f"  <Part>\n    <PartNumber>{number}</PartNumber>"
            f"\n    <ETag>{etag}</ETag>\n  </Part>"
            for number, etag in enumerate(etags, start=1)
        )
        xml = f"<CompleteMultipartUpload>\n{parts}\n</CompleteMultipartUpload>"
        request = urllib.request.Request(url, data=xml.encode(), method="POST")
        request.add_header("Content-Type", "application/xml")
        try:
            with urllib.request.urlopen(request, timeout=JSON_TIMEOUT) as response:
                response.read()
        except urllib.error.HTTPError as error:
            message = (
                f"multipart completion failed ({error.code}): "
                f"{_problem_detail(error)}"
            )
            raise PublishError(message) from error
        except (urllib.error.URLError, OSError) as error:
            message = f"multipart completion failed: {_reason(error)}"
            raise PublishError(message) from error

    def _wait_available(self, upload_id: str) -> None:
        deadline = time.monotonic() + AVAILABLE_DEADLINE
        delay = POLL_START
        while True:
            state = self._call("GET", f"/uploads/{upload_id}")["data"]["state"]
            if state == "available":
                return
            if time.monotonic() >= deadline:
                raise PublishError(
                    f"upload {upload_id} did not become available within "
                    f"{AVAILABLE_DEADLINE // 60} minutes"
                )
            time.sleep(delay)
            delay = min(delay * 2, POLL_CAP)
