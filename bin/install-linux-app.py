#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# ///

"""
Manage standalone user applications under ~/.local.

Layout:

    ~/.local/
    ├── bin/
    │   └── foo -> ../opt/foo/current/bin/foo
    ├── opt/
    │   └── foo/
    │       ├── 1.2.0/
    │       ├── 1.3.0/
    │       └── current -> 1.3.0
    └── share/
        ├── applications/
        │   └── foo.desktop
        └── icons/
            └── foo.png

Supported payloads:

    binary
    AppImage
    .tar.gz / .tgz
    .tar.xz / .txz
    .zip

Examples:

    user-app install \
        --name foo \
        --version 1.4.2 \
        --source ~/Downloads/Foo.AppImage \
        --sha256 abc123... \
        --desktop-name "Foo" \
        --icon ~/Downloads/foo.png \
        --category Development \
        --keyword editor

    user-app rollback foo 1.3.0

    user-app list

    user-app uninstall foo
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path


LOCAL = Path.home() / ".local"
BIN_DIR = LOCAL / "bin"
OPT_DIR = LOCAL / "opt"
APPLICATION_DIR = LOCAL / "share" / "applications"
ICON_DIR = LOCAL / "share" / "icons"

SUPPORTED_TYPES = (
    "auto",
    "binary",
    "appimage",
    "tar.gz",
    "tar.xz",
    "zip",
)


class UserAppError(RuntimeError):
    pass


def info(message: str) -> None:
    print(f"==> {message}")


def warning(message: str) -> None:
    print(f"warning: {message}", file=sys.stderr)


def fail(message: str) -> None:
    raise UserAppError(message)


def ensure_directories() -> None:
    for path in (BIN_DIR, OPT_DIR, APPLICATION_DIR, ICON_DIR):
        path.mkdir(parents=True, exist_ok=True)


def validate_name(value: str) -> str:
    allowed = set(
        "abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789._-"
    )

    if not value or any(char not in allowed for char in value):
        raise argparse.ArgumentTypeError(
            "must contain only letters, numbers, '.', '_' or '-'"
        )

    return value


def validate_version(value: str) -> str:
    allowed = set(
        "abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789._+-"
    )

    if not value or any(char not in allowed for char in value):
        raise argparse.ArgumentTypeError(
            "contains unsupported characters"
        )

    return value


def is_url(source: str) -> bool:
    parsed = urllib.parse.urlparse(source)
    return parsed.scheme in {"http", "https"}


def download(source: str, destination: Path, allow_http: bool = False) -> None:
    if is_url(source):
        parsed = urllib.parse.urlparse(source)

        if parsed.scheme == "http" and not allow_http:
            fail(
                "refusing plain HTTP source; use HTTPS or explicitly "
                "pass --allow-http"
            )

        info(f"Downloading {source}")

        request = urllib.request.Request(
            source,
            headers={
                "User-Agent": "user-app/1.0",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                with destination.open("wb") as output:
                    shutil.copyfileobj(response, output)
        except Exception as exc:
            fail(f"download failed: {exc}")

        return

    source_path = Path(source).expanduser().resolve()

    if not source_path.is_file():
        fail(f"source does not exist: {source_path}")

    info(f"Using local source {source_path}")
    shutil.copy2(source_path, destination)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def verify_checksum(
    path: Path,
    expected: str | None,
    allow_unverified: bool,
) -> None:
    if expected is None:
        if not allow_unverified:
            fail(
                "SHA-256 checksum required; provide --sha256 or explicitly "
                "pass --allow-unverified"
            )

        warning("installing without checksum verification")
        return

    expected = expected.strip().lower()

    if len(expected) != 64:
        fail("SHA-256 checksum must contain exactly 64 hexadecimal characters")

    try:
        int(expected, 16)
    except ValueError:
        fail("invalid SHA-256 checksum")

    info("Verifying SHA-256")

    actual = sha256(path)

    if actual != expected:
        fail(
            "SHA-256 mismatch\n"
            f"  expected: {expected}\n"
            f"  actual:   {actual}"
        )


def detect_type(source: str) -> str:
    parsed = urllib.parse.urlparse(source)

    filename = parsed.path if parsed.scheme else source
    filename = filename.lower()

    if filename.endswith(".appimage"):
        return "appimage"

    if filename.endswith((".tar.gz", ".tgz")):
        return "tar.gz"

    if filename.endswith((".tar.xz", ".txz")):
        return "tar.xz"

    if filename.endswith(".zip"):
        return "zip"

    return "binary"


def within_directory(root: Path, target: Path) -> bool:
    root = root.resolve()
    target = target.resolve()

    try:
        target.relative_to(root)
        return True
    except ValueError:
        return False


def validate_member_path(destination: Path, member_name: str) -> None:
    target = destination / member_name

    if not within_directory(destination, target):
        fail(f"archive contains unsafe path: {member_name}")


def extract_tar(archive: Path, destination: Path) -> None:
    try:
        with tarfile.open(archive) as tar:
            for member in tar.getmembers():
                validate_member_path(destination, member.name)

                # Refuse device files/FIFOs entirely.
                if member.isdev() or member.isfifo():
                    fail(
                        f"archive contains unsupported special file: "
                        f"{member.name}"
                    )

            # Python >=3.12's data filter rejects many dangerous archive
            # constructs and normalises permissions.
            tar.extractall(
                destination,
                filter="data",
            )

    except (tarfile.TarError, OSError) as exc:
        fail(f"failed to extract tar archive: {exc}")


def zip_member_is_symlink(member: zipfile.ZipInfo) -> bool:
    unix_mode = member.external_attr >> 16
    return stat.S_ISLNK(unix_mode)


def extract_zip(archive: Path, destination: Path) -> None:
    try:
        with zipfile.ZipFile(archive) as zip_file:
            for member in zip_file.infolist():
                validate_member_path(destination, member.filename)

                if zip_member_is_symlink(member):
                    fail(
                        f"ZIP archive contains symlink: "
                        f"{member.filename}"
                    )

            zip_file.extractall(destination)

    except (zipfile.BadZipFile, OSError) as exc:
        fail(f"failed to extract ZIP archive: {exc}")


def extract(
    package_type: str,
    archive: Path,
    destination: Path,
) -> None:
    if package_type in {"tar.gz", "tar.xz"}:
        extract_tar(archive, destination)
        return

    if package_type == "zip":
        extract_zip(archive, destination)
        return

    fail(f"cannot extract package type: {package_type}")


def find_executable(
    directory: Path,
    name: str,
) -> Path | None:
    candidates: list[Path] = []

    for path in directory.rglob(name):
        if path.is_file() and os.access(path, os.X_OK):
            candidates.append(path)

    if len(candidates) == 1:
        return candidates[0]

    return None


def install_payload(
    *,
    name: str,
    version: str,
    source_file: Path,
    package_type: str,
    exec_path: str | None,
    force: bool,
) -> tuple[Path, Path]:
    app_root = OPT_DIR / name
    version_dir = app_root / version

    app_root.mkdir(parents=True, exist_ok=True)

    if version_dir.exists():
        if not force:
            fail(
                f"version already installed: {version}\n"
                "use --force to replace it"
            )

        info(f"Replacing existing {version_dir}")
        shutil.rmtree(version_dir)

    staging = app_root / f".{version}.staging"

    if staging.exists():
        shutil.rmtree(staging)

    staging.mkdir()

    try:
        if package_type in {"binary", "appimage"}:
            executable = staging / name
            shutil.copy2(source_file, executable)
            executable.chmod(0o755)

            relative_exec = Path(name)

        else:
            extract(package_type, source_file, staging)

            if exec_path:
                relative_exec = Path(exec_path)
                executable = staging / relative_exec
            else:
                executable = find_executable(staging, name)

                if executable is None:
                    fail(
                        "could not uniquely determine executable inside "
                        "archive; provide --exec-path"
                    )

                relative_exec = executable.relative_to(staging)

            if not executable.is_file():
                fail(
                    "executable does not exist inside archive: "
                    f"{relative_exec}"
                )

            executable.chmod(
                executable.stat().st_mode
                | stat.S_IXUSR
                | stat.S_IXGRP
                | stat.S_IXOTH
            )

        resolved_exec = executable.resolve()

        if not within_directory(staging, resolved_exec):
            fail("executable resolves outside installation directory")

        staging.rename(version_dir)

        return version_dir, relative_exec

    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def replace_symlink(link: Path, target: str | Path) -> None:
    temporary = link.with_name(f".{link.name}.tmp")

    temporary.unlink(missing_ok=True)
    temporary.symlink_to(target)

    os.replace(temporary, link)


def activate(
    name: str,
    version: str,
    relative_exec: Path,
) -> None:
    app_root = OPT_DIR / name
    current = app_root / "current"
    bin_link = BIN_DIR / name

    info(f"Activating {name} {version}")

    # Relative link:
    # ~/.local/opt/foo/current -> 1.4.2
    replace_symlink(current, version)

    executable = current / relative_exec

    # Relative link from ~/.local/bin improves portability if $HOME moves.
    relative_target = os.path.relpath(
        executable,
        start=BIN_DIR,
    )

    replace_symlink(bin_link, relative_target)


def install_icon(
    *,
    name: str,
    source: str | None,
    allow_http: bool,
) -> Path | None:
    if source is None:
        return None

    parsed = urllib.parse.urlparse(source)
    path = parsed.path if parsed.scheme else source

    extension = Path(path).suffix.lower()

    if extension not in {".png", ".svg", ".xpm", ".webp"}:
        extension = ".png"

    destination = ICON_DIR / f"{name}{extension}"

    info("Installing application icon")

    with tempfile.TemporaryDirectory(
        prefix="user-app-icon-"
    ) as temp:
        temporary = Path(temp) / "icon"
        download(source, temporary, allow_http)
        shutil.copy2(temporary, destination)

    destination.chmod(0o644)

    return destination


def desktop_escape_value(value: str) -> str:
    return (
        value
        .replace("\\", "\\\\")
        .replace("\n", "\\n")
    )


def desktop_exec_quote(argument: str) -> str:
    """
    Quote one argument according to the Desktop Entry Exec grammar.

    We deliberately avoid shell quoting because Exec= is not executed
    through a shell.
    """

    escaped = (
        argument
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("`", "\\`")
        .replace("$", "\\$")
    )

    return f'"{escaped}"'


def create_desktop_entry(
    *,
    name: str,
    desktop_name: str,
    comment: str | None,
    icon: Path | None,
    categories: list[str],
    keywords: list[str],
    terminal: bool,
    exec_args: list[str],
) -> Path:
    destination = APPLICATION_DIR / f"{name}.desktop"
    executable = BIN_DIR / name

    if not categories:
        categories = ["Utility"]

    categories_value = ";".join(categories) + ";"

    lines = [
        "[Desktop Entry]",
        "Version=1.0",
        "Type=Application",
        f"Name={desktop_escape_value(desktop_name)}",
    ]

    if comment:
        lines.append(
            f"Comment={desktop_escape_value(comment)}"
        )

    lines.append(
        f"TryExec={executable}"
    )

    exec_parts = [
        desktop_exec_quote(str(executable)),
        *(
            desktop_exec_quote(arg)
            for arg in exec_args
        ),
    ]

    lines.append(
        f"Exec={' '.join(exec_parts)}"
    )

    if icon:
        lines.append(
            f"Icon={icon}"
        )
    else:
        lines.append(
            "Icon=application-x-executable"
        )

    lines.extend(
        [
            f"Terminal={'true' if terminal else 'false'}",
            f"Categories={categories_value}",
        ]
    )

    if keywords:
        lines.append(
            f"Keywords={';'.join(keywords)};"
        )

    lines.append("StartupNotify=true")

    content = "\n".join(lines) + "\n"

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        prefix=f".{name}.desktop.",
        dir=APPLICATION_DIR,
        delete=False,
    ) as file:
        temporary = Path(file.name)
        file.write(content)

    try:
        validator = shutil.which("desktop-file-validate")

        if validator:
            result = subprocess.run(
                [validator, str(temporary)],
                text=True,
                capture_output=True,
            )

            if result.returncode != 0:
                fail(
                    "generated desktop entry failed validation:\n"
                    f"{result.stderr.strip()}"
                )

        temporary.chmod(0o644)
        os.replace(temporary, destination)

    finally:
        temporary.unlink(missing_ok=True)

    updater = shutil.which("update-desktop-database")

    if updater:
        subprocess.run(
            [updater, str(APPLICATION_DIR)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

    return destination


def install_command(args: argparse.Namespace) -> None:
    ensure_directories()

    package_type = args.type

    if package_type == "auto":
        package_type = detect_type(args.source)

    info(f"Package type: {package_type}")

    with tempfile.TemporaryDirectory(
        prefix=f"user-app-{args.name}-"
    ) as temp:
        temp_dir = Path(temp)
        source_file = temp_dir / "payload"

        download(
            args.source,
            source_file,
            allow_http=args.allow_http,
        )

        verify_checksum(
            source_file,
            args.sha256,
            args.allow_unverified,
        )

        version_dir, relative_exec = install_payload(
            name=args.name,
            version=args.version,
            source_file=source_file,
            package_type=package_type,
            exec_path=args.exec_path,
            force=args.force,
        )

    activate(
        args.name,
        args.version,
        relative_exec,
    )

    icon = install_icon(
        name=args.name,
        source=args.icon,
        allow_http=args.allow_http,
    )

    desktop_file = create_desktop_entry(
        name=args.name,
        desktop_name=args.desktop_name or args.name,
        comment=args.comment,
        icon=icon,
        categories=args.category,
        keywords=args.keyword,
        terminal=args.terminal,
        exec_args=args.exec_arg,
    )

    print()
    print("Installed successfully")
    print()
    print(f"  Application: {args.desktop_name or args.name}")
    print(f"  Version:     {args.version}")
    print(f"  Payload:     {version_dir}")
    print(f"  Command:     {BIN_DIR / args.name}")
    print(f"  Desktop:     {desktop_file}")
    print()
    print("Available via:")
    print()
    print(f"  {args.name}")
    print("  rofi -show drun")


def read_current_version(name: str) -> str | None:
    current = OPT_DIR / name / "current"

    if not current.is_symlink():
        return None

    return os.readlink(current)


def list_command(_: argparse.Namespace) -> None:
    ensure_directories()

    if not OPT_DIR.exists():
        return

    rows: list[tuple[str, str]] = []

    for app in sorted(OPT_DIR.iterdir()):
        if not app.is_dir():
            continue

        version = read_current_version(app.name) or "-"
        rows.append((app.name, version))

    if not rows:
        print("No user applications installed.")
        return

    width = max(len(name) for name, _ in rows)

    for name, version in rows:
        print(f"{name:<{width}}  {version}")


def rollback_command(args: argparse.Namespace) -> None:
    ensure_directories()

    app_root = OPT_DIR / args.name
    version_dir = app_root / args.version

    if not version_dir.is_dir():
        fail(
            f"{args.name} version {args.version} is not installed"
        )

    current = app_root / "current"

    if not current.is_symlink():
        fail(
            f"{args.name} does not have an active version"
        )

    current_version = os.readlink(current)
    current_dir = app_root / current_version

    bin_link = BIN_DIR / args.name

    if not bin_link.is_symlink():
        fail(
            f"cannot determine executable for {args.name}"
        )

    resolved_binary = bin_link.resolve()

    try:
        relative_exec = resolved_binary.relative_to(current_dir.resolve())
    except ValueError:
        fail(
            f"{args.name} executable is outside its application directory"
        )

    new_exec = version_dir / relative_exec

    if not new_exec.is_file():
        fail(
            f"version {args.version} does not contain executable "
            f"{relative_exec}"
        )

    activate(
        args.name,
        args.version,
        relative_exec,
    )

    print(
        f"Rolled back {args.name} "
        f"from {current_version} to {args.version}"
    )


def uninstall_command(args: argparse.Namespace) -> None:
    ensure_directories()

    app_root = OPT_DIR / args.name

    if not app_root.exists():
        fail(f"application is not installed: {args.name}")

    current_version = read_current_version(args.name)

    if args.version:
        version_dir = app_root / args.version

        if not version_dir.is_dir():
            fail(
                f"{args.name} version {args.version} is not installed"
            )

        if args.version == current_version:
            fail(
                "cannot remove the active version; rollback to another "
                "version first, or uninstall the complete application"
            )

        shutil.rmtree(version_dir)

        print(
            f"Removed {args.name} {args.version}"
        )
        return

    info(f"Removing {args.name}")

    (BIN_DIR / args.name).unlink(missing_ok=True)
    (APPLICATION_DIR / f"{args.name}.desktop").unlink(
        missing_ok=True
    )

    for icon in ICON_DIR.glob(f"{args.name}.*"):
        icon.unlink(missing_ok=True)

    shutil.rmtree(app_root)

    updater = shutil.which("update-desktop-database")

    if updater:
        subprocess.run(
            [updater, str(APPLICATION_DIR)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

    print(f"Removed {args.name}")


def versions_command(args: argparse.Namespace) -> None:
    app_root = OPT_DIR / args.name

    if not app_root.is_dir():
        fail(f"application is not installed: {args.name}")

    current = read_current_version(args.name)

    versions = sorted(
        path.name
        for path in app_root.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    )

    for version in versions:
        marker = "*" if version == current else " "
        print(f"{marker} {version}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="user-app",
        description=(
            "Manage standalone applications under ~/.local "
            "and expose them through desktop launchers."
        ),
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    install = subparsers.add_parser(
        "install",
        help="install or upgrade an application",
    )

    install.add_argument(
        "--name",
        required=True,
        type=validate_name,
        help="internal application/command name",
    )

    install.add_argument(
        "--version",
        required=True,
        type=validate_version,
    )

    install.add_argument(
        "--source",
        required=True,
        help="HTTPS URL or local file",
    )

    install.add_argument(
        "--sha256",
        help="expected SHA-256 checksum",
    )

    install.add_argument(
        "--allow-unverified",
        action="store_true",
        help="explicitly allow installation without a checksum",
    )

    install.add_argument(
        "--allow-http",
        action="store_true",
        help="explicitly permit an insecure HTTP download",
    )

    install.add_argument(
        "--type",
        choices=SUPPORTED_TYPES,
        default="auto",
        help="payload type (default: auto)",
    )

    install.add_argument(
        "--exec-path",
        help=(
            "path to executable inside an archive, "
            "e.g. bin/foo"
        ),
    )

    install.add_argument(
        "--desktop-name",
        help="display name shown in Rofi/Plasma",
    )

    install.add_argument(
        "--comment",
        help="desktop entry description",
    )

    install.add_argument(
        "--icon",
        help="HTTPS URL or local icon file",
    )

    install.add_argument(
        "--category",
        action="append",
        default=[],
        help=(
            "desktop category; may be specified multiple times"
        ),
    )

    install.add_argument(
        "--keyword",
        action="append",
        default=[],
        help=(
            "desktop search keyword; may be specified multiple times"
        ),
    )

    install.add_argument(
        "--exec-arg",
        action="append",
        default=[],
        help=(
            "argument passed by the desktop launcher; "
            "may be specified multiple times"
        ),
    )

    install.add_argument(
        "--terminal",
        action="store_true",
        help="mark application as requiring a terminal",
    )

    install.add_argument(
        "--force",
        action="store_true",
        help="replace an already installed version",
    )

    install.set_defaults(func=install_command)

    list_parser = subparsers.add_parser(
        "list",
        help="list installed applications",
    )
    list_parser.set_defaults(func=list_command)

    versions = subparsers.add_parser(
        "versions",
        help="list installed versions",
    )
    versions.add_argument(
        "name",
        type=validate_name,
    )
    versions.set_defaults(func=versions_command)

    rollback = subparsers.add_parser(
        "rollback",
        help="activate an older installed version",
    )
    rollback.add_argument(
        "name",
        type=validate_name,
    )
    rollback.add_argument(
        "version",
        type=validate_version,
    )
    rollback.set_defaults(func=rollback_command)

    uninstall = subparsers.add_parser(
        "uninstall",
        help="remove an application or old version",
    )
    uninstall.add_argument(
        "name",
        type=validate_name,
    )
    uninstall.add_argument(
        "--version",
        type=validate_version,
        help="remove only this inactive version",
    )
    uninstall.set_defaults(func=uninstall_command)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        args.func(args)
        return 0

    except UserAppError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
