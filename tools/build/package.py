"""Build a Windows ZIP from the pinned SDK using absolute project paths."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import shutil
import tempfile
from tools.story_model import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", required=True, type=Path)
    args = parser.parse_args()
    sdk = args.sdk.resolve()
    destination = ROOT / "dist"
    if os.name == "nt":
        command = [str(sdk / "lib/py3-windows-x86_64/python.exe"), str(sdk / "renpy.py")]
    else:
        command = [str(sdk / "renpy.sh")]
    # Ren'Py's dump/compile process also writes game-local persistent data.
    # Stage the release inputs to avoid author/player saves and other processes.
    with tempfile.TemporaryDirectory(prefix='rain-package-stage-') as temp:
        project = Path(temp) / 'project'
        shutil.copytree(ROOT / 'game', project / 'game', ignore=shutil.ignore_patterns('saves'))
        for name in ('old-game', 'licenses'):
            if (ROOT / name).is_dir(): shutil.copytree(ROOT / name, project / name)
        for name in ('PLAYER_README.txt', 'CREDITS.md', 'LICENSE', 'VERSION', 'icon.ico'):
            if (ROOT / name).is_file(): shutil.copy2(ROOT / name, project / name)
        command += [str(sdk / "launcher"), "distribute", str(project), "--package", "win", "--destination", str(destination)]
        environment = {**os.environ, 'RENPY_PATH_TO_SAVES': str(Path(temp) / 'user-saves')}
        subprocess.run(command, check=True, env=environment)
    version = (ROOT / "VERSION").read_text().strip()
    archive = destination / f"BeforeTheRainStops-{version}-win.zip"
    if not archive.is_file():
        raise SystemExit("Build exited without the expected Windows ZIP")
    print(archive)


if __name__ == "__main__":
    main()
