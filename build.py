"""Build the standalone program and the release archives (Linux and Windows).

Usage (from the project folder, with the virtualenv's Python):
    python build.py            build, smoke-test and package
    python build.py --no-deps  skip `pip install` (CI installs first)

Produces in dist/:
    anonymized-tweet-scraper[.exe]   the program (PyInstaller --onefile)
    LICENSE, THIRD_PARTY_LICENSES.txt, TERMS_OF_USE.md
    release/anonymized-tweet-scraper-v<version>-<os>-<arch>.{tar.gz|zip}
    release/anonymized-tweet-scraper-v<version>-<os>-<arch>-portable.{tar.gz|zip}

PyInstaller cannot cross-compile: build the Linux archive on Linux and the
Windows archive on Windows. Standard library only.
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
RELEASE = DIST / "release"
NAME = "anonymized-tweet-scraper"
IS_WINDOWS = os.name == "nt"
EXE = NAME + (".exe" if IS_WINDOWS else "")

README_TXT = """\
anonymized-tweet-scraper {version} ({variant})
{underline}

Collects posts from Twitter/X and Ekşi Sözlük and writes them, pseudonymized,
to CSV files for research. Full documentation:
https://github.com/OrhunTokdemir/anonymized-tweet-scraper

Start
  {start}
  On first start you are asked to accept the terms of use (TERMS_OF_USE.md).

Where files are stored
{where}
  Run `{cmd} --paths` to see the exact folders on this computer.
  Change the CSV folder in the app: Accounts & settings -> Output folder.

Keep .env private: it holds your Twitter account cookies. Never share it,
and never share accounts.db.
{extra}
Files in this folder
  {exe}   the program (no Python needed)
  LICENSE                     this project's license (MIT)
  THIRD_PARTY_LICENSES.txt    licenses of everything bundled inside the program
  TERMS_OF_USE.md             the terms you accept on first start
{marker_line}"""


def version() -> str:
    text = (ROOT / "scraper" / "__init__.py").read_text(encoding="utf-8")
    return re.search(r'__version__\s*=\s*"([^"]+)"', text).group(1)


def platform_tag() -> str:
    os_name = {"win32": "windows", "linux": "linux", "darwin": "macos"}.get(sys.platform, sys.platform)
    machine = platform.machine().lower()
    arch = {"amd64": "x86_64", "x86_64": "x86_64", "aarch64": "arm64", "arm64": "arm64"}.get(machine, machine)
    return f"{os_name}-{arch}"


def run(*cmd: str, **kw) -> subprocess.CompletedProcess:
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(cmd, check=True, **kw)


def install_deps() -> None:
    run(sys.executable, "-m", "pip", "install", "-q",
        "-r", str(ROOT / "requirements.txt"), "-r", str(ROOT / "requirements-build.txt"))


def pyinstaller() -> Path:
    sep = os.pathsep  # ":" on Linux, ";" on Windows
    data = [
        (ROOT / "scraper" / "app.tcss", "scraper"),
        (ROOT / "lexicons", "lexicons"),
        (ROOT / ".env.example", "."),
        (ROOT / "TERMS_OF_USE.md", "."),
    ]
    args = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile",
            "--name", NAME, "--distpath", str(DIST), "--workpath", str(ROOT / "build"),
            "--specpath", str(ROOT / "build")]
    for src, dest in data:
        args += ["--add-data", f"{src}{sep}{dest}"]
    args += ["--collect-data", "textual", "--collect-all", "curl_cffi", "--collect-data", "fake_useragent",
             "--collect-submodules", "eksiapi", "--collect-submodules", "textual",
             str(ROOT / "run_scraper.py")]
    run(*args)
    exe = DIST / EXE
    if not exe.is_file():
        raise SystemExit(f"PyInstaller finished but {exe} is missing")
    return exe


def license_files() -> None:
    run(sys.executable, str(ROOT / "tools" / "third_party_licenses.py"),
        str(ROOT / "requirements.txt"), str(DIST / "THIRD_PARTY_LICENSES.txt"))
    shutil.copyfile(ROOT / "LICENSE", DIST / "LICENSE")
    shutil.copyfile(ROOT / "TERMS_OF_USE.md", DIST / "TERMS_OF_USE.md")


def smoke_test(exe: Path, ver: str) -> None:
    """--version and --paths in a throwaway HOME/APPDATA, in both modes."""
    with tempfile.TemporaryDirectory() as home:
        env = dict(os.environ, HOME=home, USERPROFILE=home, APPDATA=str(Path(home, "AppData")),
                   XDG_DATA_HOME=str(Path(home, "share")), XDG_CONFIG_HOME=str(Path(home, "config")))
        out = run(str(exe), "--version", env=env, capture_output=True, text=True).stdout.strip()
        if out != f"{NAME} {ver}":
            raise SystemExit(f"smoke test: --version printed {out!r}")
        std = run(str(exe), "--paths", env=env, capture_output=True, text=True).stdout
        if "Mode:                standard" not in std or home not in std:
            raise SystemExit(f"smoke test: unexpected --paths output (standard):\n{std}")

        portable_dir = Path(home, "portable-copy")
        portable_dir.mkdir()
        copy = portable_dir / exe.name
        shutil.copy2(exe, copy)
        (portable_dir / "portable").touch()
        port = run(str(copy), "--paths", env=env, capture_output=True, text=True).stdout
        if "Mode:                portable" not in port or str(portable_dir / "data") not in port:
            raise SystemExit(f"smoke test: unexpected --paths output (portable):\n{port}")
    print("smoke test passed (version, standard and portable paths)")


def readme_text(ver: str, portable: bool) -> str:
    cmd = f".\\{EXE}" if IS_WINDOWS else f"./{EXE}"
    if portable:
        where = ("  Everything stays in this folder: .env (settings and account cookies),\n"
                 "  accounts.db, and the CSV files in data/. Move or delete the folder to\n"
                 "  move or remove everything. Keep the file named `portable`: without it\n"
                 "  the program uses the per-user folders instead.")
    elif IS_WINDOWS:
        where = ("  Settings and accounts: %APPDATA%\\anonymized-tweet-scraper\\\n"
                 "  CSV files:             <your Documents folder>\\anonymized-posts\\")
    else:
        where = ("  Settings and accounts: ~/.local/share/anonymized-tweet-scraper/\n"
                 "  CSV files:             <your Documents folder>/anonymized-posts/\n"
                 "                         (e.g. ~/Belgeler/anonymized-posts on a Turkish system)")
    if IS_WINDOWS:
        start = (f"Open Windows Terminal in this folder and run:  {cmd}\n"
                 "  (Windows 11 has it built in; on Windows 10 install \"Windows Terminal\".\n"
                 "  The old console window displays the app poorly.)")
        extra = ("\nWindows SmartScreen: the program is not code-signed, so Windows may warn\n"
                 "on first start. Click \"More info\" -> \"Run anyway\" if you trust this download\n"
                 "(check its SHA-256 checksum against SHA256SUMS.txt on the release page).\n")
    else:
        start = (f"In a terminal, in this folder:  {cmd}\n"
                 + ("" if portable else
                    f"  Optional: move it onto your PATH:  mv {EXE} ~/.local/bin/  then run `{NAME}`.\n")
                 + "  Tested on Ubuntu 26.04.1 LTS; other distributions may work but are not tested.")
        extra = ""
    variant = "portable" if portable else "standard"
    title = f"anonymized-tweet-scraper {ver} ({variant})"
    return README_TXT.format(
        version=ver, variant=variant, underline="=" * len(title), start=start, where=where,
        cmd=cmd, extra=extra, exe=EXE.ljust(25),
        marker_line="  portable                    marker file: keeps everything in this folder\n"
        if portable else "",
    )


def package(exe: Path, ver: str) -> list[Path]:
    RELEASE.mkdir(parents=True, exist_ok=True)
    made = []
    for portable in (False, True):
        stem = f"{NAME}-v{ver}-{platform_tag()}" + ("-portable" if portable else "")
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp, NAME)
            folder.mkdir()
            shutil.copy2(exe, folder / exe.name)
            for f in ("LICENSE", "THIRD_PARTY_LICENSES.txt", "TERMS_OF_USE.md"):
                shutil.copyfile(DIST / f, folder / f)
            (folder / "README.txt").write_text(readme_text(ver, portable), encoding="utf-8",
                                                newline="\r\n" if IS_WINDOWS else "\n")
            if portable:
                (folder / "portable").write_text(
                    "This file makes the program keep everything in this folder.\n", encoding="utf-8")
            if IS_WINDOWS:
                out = RELEASE / f"{stem}.zip"
                with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
                    for p in sorted(folder.rglob("*")):
                        z.write(p, p.relative_to(tmp))
            else:
                out = RELEASE / f"{stem}.tar.gz"
                with tarfile.open(out, "w:gz") as t:
                    t.add(folder, arcname=NAME)  # keeps the executable bit
        made.append(out)
        print(f"packaged {out.relative_to(ROOT)}")
    return made


def main(argv: list[str]) -> int:
    if "--no-deps" not in argv:
        install_deps()
    ver = version()
    print(f"==> Building {NAME} {ver} for {platform_tag()}")
    if RELEASE.exists():
        shutil.rmtree(RELEASE)
    exe = pyinstaller()
    license_files()
    smoke_test(exe, ver)
    package(exe, ver)
    print(f"\nDone. Release archives are in {RELEASE.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
