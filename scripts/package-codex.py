#!/usr/bin/env python3
"""Build one self-contained, reproducible ZIP per native Codex plugin."""
import argparse
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def package_plugins(output: Path) -> list[Path]:
    catalogue = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text())
    output.mkdir(parents=True, exist_ok=True)
    archives = []
    for entry in catalogue["plugins"]:
        package = (ROOT / entry["source"]["path"]).resolve()
        if not package.is_relative_to((ROOT / "plugins").resolve()):
            raise ValueError("Plugin source must be inside plugins/")
        manifest = json.loads((package / ".codex-plugin/plugin.json").read_text())
        name, version = manifest["name"], manifest["version"]
        if name != entry["name"] or not re.fullmatch(r"[a-z0-9-]+", name):
            raise ValueError("Invalid plugin identity")
        if not re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?", version):
            raise ValueError("Invalid plugin version")
        if output.resolve().is_relative_to(package):
            raise ValueError("Archive output must be outside the plugin")
        archive = output / f"{name}-{version}.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            for path in sorted(package.rglob("*")):
                if path.is_symlink():
                    raise ValueError(f"Plugin resources must not be symlinks: {path}")
                if not path.is_file():
                    continue
                info = zipfile.ZipInfo(path.relative_to(package).as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = (0o100000 | (path.stat().st_mode & 0o777)) << 16
                bundle.writestr(info, path.read_bytes())
        archives.append(archive)
    return archives


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Directory for the eight plugin ZIPs")
    arguments = parser.parse_args()
    for archive_path in package_plugins(arguments.output):
        print(archive_path)
