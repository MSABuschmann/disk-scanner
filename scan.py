#!/usr/bin/env python3
from argparse import ArgumentParser
from datetime import datetime
import csv
import logging
import os
import pwd

FIELDNAMES = ["path", "size_bytes", "owner", "uid", "mtime"]


def get_username(uid):
    try:
        return pwd.getpwuid(uid).pw_name
    except KeyError:
        return str(uid)


def scan(root, writer, log, progress_every=100_000):
    n = 0
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            it = os.scandir(current)
        except PermissionError:
            log.warning(current)
            continue
        with it:
            for entry in it:
                if entry.is_symlink():
                    continue
                try:
                    st = entry.stat(follow_symlinks=False)
                except PermissionError:
                    log.warning(entry.path)
                    continue
                except OSError as e:
                    log.warning("%s: %s", entry.path, e)
                    continue
                if entry.is_dir(follow_symlinks=False):
                    stack.append(entry.path)
                elif entry.is_file(follow_symlinks=False):
                    writer.writerow({
                        "path": entry.path,
                        "size_bytes": st.st_size,
                        "owner": get_username(st.st_uid),
                        "uid": st.st_uid,
                        "mtime": datetime.fromtimestamp(st.st_mtime).isoformat(),
                    })
                    n += 1
                    if n % progress_every == 0:
                        print(f"{n:,} files scanned", flush=True)
    print(f"Done: {n:,} files total", flush=True)


def main():
    parser = ArgumentParser(description="Scan a directory and record file metadata")
    parser.add_argument("directory", help="Root directory to scan")
    parser.add_argument("output", help="Output CSV file")
    parser.add_argument("--log", default=None, help="Log file for permission errors (default: stderr)")
    args = parser.parse_args()

    logging.basicConfig(
        filename=args.log,
        level=logging.WARNING,
        format="%(message)s",
    )
    log = logging.getLogger("scan")

    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        scan(args.directory, writer, log)


if __name__ == "__main__":
    main()
