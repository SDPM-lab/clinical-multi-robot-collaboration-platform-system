#!/usr/bin/env python3
"""Remove Gazebo Sim runtime logs without touching Fuel model assets."""

from pathlib import Path
import shutil


def main():
    gz_root = Path.home() / ".gz"
    log_dir = gz_root / "sim" / "log"
    expected = Path.home().resolve() / ".gz" / "sim" / "log"

    # Refuse to delete anything unless the resolved target is exactly the
    # expected Gazebo Sim log directory.
    if log_dir.resolve() != expected:
        raise RuntimeError(f"Refusing to clean unexpected path: {log_dir}")

    removed = 0
    if log_dir.is_dir():
        for entry in log_dir.iterdir():
            if entry.is_dir():
                shutil.rmtree(entry)
            elif entry.is_file() or entry.is_symlink():
                entry.unlink()
            removed += 1

    auto_log = gz_root / "auto_default.log"
    if auto_log.is_file() or auto_log.is_symlink():
        auto_log.unlink()
        removed += 1

    print(f"Gazebo runtime cleanup removed {removed} log item(s)")


if __name__ == "__main__":
    main()
