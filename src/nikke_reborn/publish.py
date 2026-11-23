"""Publish the ``bundles/`` archives to the NIKKE REBORN mod on Nexus
Mods (the ``publish`` command).

Every archive is set to the version of the newest ``CHANGELOG.md``
entry: files that already exist on the mod (matching the archive's
published name) get a new version — unless their current version
already carries the target version, description and category
(skip-if-current, so a fully re-run is a no-op) — and files that do
not exist are created. Updates run first, creations after, and only
the last operation updates the mod's version (every file carries the
same version string, so the mod version moves once, when the final
file succeeds). The newest entry's bullets then go to the mod's
changelog for that version, appended only when the version has no
entry yet (the API's append is additive, so re-runs never duplicate
it). Each file's description is the set's toml ``description`` plus a
quality notice derived from the archive's run-mode suffix.

Inputs: ``.env`` (``NEXUS_MOD_ID``, ``NEXUS_API_KEY``),
``CHANGELOG.md``, ``bundles/*.zip`` and ``cards/*_<set>.toml``. All
local problems are reported before any network call. ``--dry`` performs
the read-only phase and prints the plan (the skip/update/create split,
which operation bumps the mod version, and whether the changelog entry
will be appended) without uploading."""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

from nikke_reborn.config import BUNDLES_DIR, CARDS_DIR, MOD_NAME, REPO_ROOT
from nikke_reborn.error import GenerationError, PublishError
from nikke_reborn.nexus import NexusClient, RemoteFileVersion
from nikke_reborn.preset import Preset, spaced

ENV_FILE = REPO_ROOT / ".env"
CHANGELOG_FILE = REPO_ROOT / "CHANGELOG.md"

HEADING_PATTERN = re.compile(r"^# (.+)$")
VERSION_PATTERN = re.compile(r"^[a-zA-Z0-9.-]+$")
BULLET_PREFIX = "- "
DESCRIPTION_LIMIT = 255


@dataclass
class Publication:
    """One archive's publication plan: its published name, file
    category and description, and the archive it uploads from (the
    version is shared by every file and kept at the top level)."""

    path: Path
    set_name: str
    suffix: str
    published_name: str
    category: str
    description: str
    size_bytes: int


@dataclass
class Operation:
    """A publication's decision after matching against the mod's
    files: ``skip`` (already at the target), ``update`` (a new version
    for the matched file) or ``create`` (a new file), and the matched
    file's id where there is one."""

    publication: Publication
    action: str
    file_id: str | None


def run() -> None:
    """Publish the ``bundles/`` archives to the NIKKE REBORN mod."""
    args = _parse_args()

    try:
        mod_id, api_key = _environment()
        version, changelog_text = _changelog_target()
        publications = _bundle_plans()

        client = NexusClient(api_key, mod_id)
        info = client.mod_details()
        print(f"mod: {info.name} (version {info.version}, {info.status})")

        operations = _plan(client, publications, version)
        entry_present = _entry_present(client, version)
        _print_plan(operations, version, entry_present)
        if args.dry:
            return

        _execute(client, operations, version)
        appended = _append_changelog(client, version, changelog_text, entry_present)
        _print_summary(operations, version, appended)
    except (GenerationError, PublishError) as error:
        print(f"error: {error}", file=sys.stderr)
        sys.exit(1)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="publish",
        description=(
            "Publish the archives in bundles/ to the NIKKE REBORN mod on "
            "Nexus Mods: files matching an archive's published name get a "
            "new version (unless already at the target), the rest are "
            "created; every file is set to the newest CHANGELOG.md entry's "
            "version, which the last operation sets as the mod's version; "
            "the entry's bullets then go to the mod's changelog"
        ),
    )
    parser.add_argument(
        "--dry",
        action="store_true",
        help="read-only: print the plan and stop",
    )
    return parser.parse_args()


def _environment() -> tuple[str, str]:
    """The mod id and API key from ``.env``."""
    try:
        text = ENV_FILE.read_text(encoding="utf-8")
    except OSError:
        raise GenerationError(
            f"no {ENV_FILE.name} at the repo root (set NEXUS_MOD_ID and NEXUS_API_KEY)"
        )
    values = {}
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            key, separator, value = line.partition("=")
            if separator:
                values[key.strip()] = value.strip()
    missing = [
        name for name in ("NEXUS_MOD_ID", "NEXUS_API_KEY") if not values.get(name)
    ]
    if missing:
        raise GenerationError(f".env is missing {', '.join(missing)}")
    return values["NEXUS_MOD_ID"], values["NEXUS_API_KEY"]


def _changelog_target() -> tuple[str, str]:
    """The target version (the newest entry's — the first ``# <version>``
    heading) and the text appended to the mod for it (the entry's
    bullets, one line per bullet, the ``- `` marker removed)."""
    try:
        lines = CHANGELOG_FILE.read_text(encoding="utf-8").splitlines()
    except OSError:
        raise GenerationError(f"no {CHANGELOG_FILE.name} at the repo root")
    for index, line in enumerate(lines):
        match = HEADING_PATTERN.match(line)
        if not match:
            continue
        version = match.group(1)
        if not VERSION_PATTERN.fullmatch(version):
            raise GenerationError(
                f"invalid version {version!r} in {CHANGELOG_FILE.name} "
                "(expected [a-zA-Z0-9.-])"
            )
        bullets = []
        for entry_line in lines[index + 1 :]:
            if HEADING_PATTERN.match(entry_line):
                break
            if entry_line.startswith(BULLET_PREFIX):
                bullets.append(entry_line.removeprefix(BULLET_PREFIX))
        if not bullets:
            raise GenerationError(f"the {version} entry carries no bullets")
        return version, "\n".join(bullets)
    raise GenerationError(f"no version heading in {CHANGELOG_FILE.name}")


def _bundle_plans() -> list[Publication]:
    """The publication plan for every archive in ``bundles/``."""
    paths = sorted(BUNDLES_DIR.glob("*.zip"))
    if not paths:
        raise GenerationError(f"no archives in {BUNDLES_DIR.name}/")
    return [_bundle_plan(path) for path in paths]


def _bundle_plan(path: Path) -> Publication:
    """One archive's publication plan, derived from its disk name (the
    published name plus ``.zip``) and its set's toml."""
    stem = path.name.removesuffix(".zip")
    prefix = f"{MOD_NAME} - "
    if not stem.startswith(prefix):
        raise GenerationError(f"unrecognized archive name: {path.name}")
    variant = stem.removeprefix(prefix)
    base_name = Preset.strip_suffix(variant)
    suffix = variant.removeprefix(base_name)
    set_name = base_name.replace(" ", "")
    toml_path = _set_toml(set_name)
    return Publication(
        path=path,
        set_name=set_name,
        suffix=suffix,
        published_name=f"{MOD_NAME} - {spaced(set_name)}{suffix}",
        category="optional" if suffix else "main",
        description=_description(toml_path, suffix),
        size_bytes=path.stat().st_size,
    )


def _set_toml(set_name: str) -> Path:
    """The set's toml: the single ``cards/*_<set>.toml``."""
    matches = sorted(CARDS_DIR.glob(f"*_{set_name}.toml"))
    if len(matches) != 1:
        raise GenerationError(
            f"expected one toml for {set_name!r} in {CARDS_DIR.name}/, "
            f"found {len(matches)}"
        )
    return matches[0]


def _description(toml_path: Path, suffix: str) -> str:
    """The file's description: the toml's ``description``, a blank
    line, and the quality notice of the archive's run-mode suffix
    (validated against the API's 255-character limit)."""
    try:
        data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        raise GenerationError(f"cannot read {toml_path.name}")
    base = data.get("description")
    if not isinstance(base, str) or not base:
        raise GenerationError(f"no description in {toml_path.name}")
    description = f"{base}\n\n{_notice(suffix)}"
    if len(description) > DESCRIPTION_LIMIT:
        raise GenerationError(
            f"{toml_path.name}: the description is {len(description)} "
            f"characters, over the {DESCRIPTION_LIMIT} limit"
        )
    return description


def _notice(suffix: str) -> str:
    if suffix == "":
        return "Normal quality. 1024-sized textures and 60fps videos."
    if suffix == Preset.LOW.suffix:
        return "Low quality. 1024-sized textures and 720p 30fps videos."
    if suffix == Preset.ULTRA.suffix:
        return (
            "Ultra quality. 2048-sized textures and 60fps videos.\n\n"
            "Use with caution! Make sure you have plenty of VRAM."
        )
    raise GenerationError(f"unrecognized run-mode suffix: {suffix!r}")


def _plan(
    client: NexusClient,
    publications: list[Publication],
    version: str,
) -> list[Operation]:
    """Match the publications against the mod's files and decide the
    action for each: ``skip`` when the matched file's current version
    (the highest position) already carries the target version,
    description and category; ``update`` when it matches but is not at
    the target; ``create`` when there is no match."""
    file_map = {remote.name: remote.file_id for remote in client.files()}
    operations = []
    for publication in publications:
        file_id = file_map.get(publication.published_name)
        if file_id is None:
            operations.append(Operation(publication, "create", None))
            continue
        current = _current_version(client, file_id)
        at_target = (
            current.version == version
            and current.description == publication.description
            and current.category == publication.category
        )
        operations.append(
            Operation(publication, "skip" if at_target else "update", file_id)
        )
    return sorted(
        operations,
        key=lambda operation: operation.publication.published_name,
    )


def _current_version(client: NexusClient, file_id: str) -> RemoteFileVersion:
    """The file's current version: the one with the highest position."""
    versions = client.file_versions(file_id)
    if not versions:
        raise PublishError(f"file {file_id} has no versions")
    return max(versions, key=lambda current: current.position)


def _entry_present(client: NexusClient, version: str) -> bool:
    """Whether the mod's changelog already has an entry for *version*."""
    return any(entry.version == version for entry in client.changelogs())


def _ordered_operations(operations: list[Operation]) -> list[Operation]:
    """The operations in execution order: the updates, then the
    creations, each sorted by published name (the skips are not
    operations)."""

    def by_name(operation: Operation) -> str:
        return operation.publication.published_name

    updates = sorted(
        (operation for operation in operations if operation.action == "update"),
        key=by_name,
    )
    creations = sorted(
        (operation for operation in operations if operation.action == "create"),
        key=by_name,
    )
    return updates + creations


def _print_plan(operations: list[Operation], version: str, entry_present: bool) -> None:
    """The plan: each file's action, version, category and size; which
    operation bumps the mod version; whether the changelog entry will
    be appended."""
    print(f"plan (target version {version}):")
    for operation in operations:
        publication = operation.publication
        size = publication.size_bytes / 2**20
        print(
            f"  {operation.action:<6} {publication.published_name}  "
            f"{version}  {publication.category:<8} {size:8.1f} MiB"
        )
    ordered = _ordered_operations(operations)
    if ordered:
        final = ordered[-1]
        print(
            f"  the last operation ({final.publication.published_name}) "
            f"bumps the mod version to {version}"
        )
    else:
        print("  no operations; the mod version is unchanged")
    if entry_present:
        print(f"  changelog entry for {version}: already present")
    else:
        print(f"  changelog entry for {version}: will be appended")


def _execute(client: NexusClient, operations: list[Operation], version: str) -> None:
    """Run the operations in order (updates, then creations), one file
    at a time; the last one updates the mod's version."""
    ordered = _ordered_operations(operations)
    for position, operation in enumerate(ordered):
        publication = operation.publication
        update_mod_version = position == len(ordered) - 1
        upload_id = client.upload(publication.path)
        if operation.action == "update":
            created = client.create_file_version(
                upload_id=upload_id,
                file_id=operation.file_id,
                name=publication.published_name,
                version=version,
                file_category=publication.category,
                description=publication.description,
                update_mod_version=update_mod_version,
            )
            print(
                f"updated {publication.published_name}: version id {created.version_id}"
            )
        else:
            file_id = client.create_file(
                upload_id=upload_id,
                name=publication.published_name,
                version=version,
                file_category=publication.category,
                description=publication.description,
                update_mod_version=update_mod_version,
            )
            print(f"created {publication.published_name}: file id {file_id}")
        if update_mod_version:
            print(f"mod version updated to {version}")


def _append_changelog(
    client: NexusClient, version: str, text: str, present: bool
) -> bool:
    """Append the mod's changelog entry for *version* (the entry's
    bullets, one line each) when the version has no entry yet; True
    when the entry was appended."""
    if present:
        return False
    client.append_changelog(version, text)
    return True


def _print_summary(operations: list[Operation], version: str, appended: bool) -> None:
    updated = sum(1 for operation in operations if operation.action == "update")
    created = sum(1 for operation in operations if operation.action == "create")
    skipped = sum(1 for operation in operations if operation.action == "skip")
    if updated or created:
        version_text = f"mod version now {version}"
    else:
        version_text = "mod version unchanged"
    print(
        f"{updated} updated, {created} created, {skipped} skipped; "
        f"{version_text}; "
        f"changelog entry {'appended' if appended else 'already present'}"
    )
