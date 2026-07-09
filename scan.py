#!/usr/bin/env python3
from argparse import ArgumentParser
from datetime import datetime
import csv
import gzip
import os
import pwd
import queue
import threading
import time
import time

FIELDNAMES = ["path", "size_bytes", "owner", "uid", "mtime", "error"]


def get_username(uid):
    try:
        return pwd.getpwuid(uid).pw_name
    except KeyError:
        return str(uid)


def scan(root, writer, n_workers, progress_every=100_000):
    dir_q = queue.Queue()
    dir_q.put(root)

    write_lock = threading.Lock()
    counter = [0]
    counter_lock = threading.Lock()

    def worker():
        while True:
            try:
                current = dir_q.get(timeout=1)
            except queue.Empty:
                return
            try:
                _process(current)
            finally:
                dir_q.task_done()

    def _process(current):
        rows = []
        try:
            it = os.scandir(current)
        except PermissionError:
            with write_lock:
                writer.writerow({"path": current, "error": "permission_denied"})
            return
        with it:
            for entry in it:
                if entry.is_symlink():
                    continue
                try:
                    st = entry.stat(follow_symlinks=False)
                except PermissionError:
                    rows.append({"path": entry.path, "error": "permission_denied"})
                    continue
                except OSError as e:
                    rows.append({"path": entry.path, "error": str(e)})
                    continue
                if entry.is_dir(follow_symlinks=False):
                    dir_q.put(entry.path)
                elif entry.is_file(follow_symlinks=False):
                    rows.append({
                        "path": entry.path,
                        "size_bytes": st.st_size,
                        "owner": get_username(st.st_uid),
                        "uid": st.st_uid,
                        "mtime": datetime.fromtimestamp(st.st_mtime).isoformat(),
                        "error": "",
                    })

        if not rows:
            return

        n_files = sum(1 for r in rows if not r.get("error"))
        with write_lock:
            writer.writerows(rows)
        with counter_lock:
            prev = counter[0]
            counter[0] += n_files
            n = counter[0]
        if n // progress_every != prev // progress_every:
            print(f"{n:,} files scanned", flush=True)

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(n_workers)]
    for t in threads:
        t.start()

    dir_q.join()

    print(f"Done: {counter[0]:,} files total", flush=True)


def main():
    parser = ArgumentParser(description="Scan a directory and record file metadata")
    parser.add_argument("directory", help="Root directory to scan")
    parser.add_argument("output", help="Output file (.csv.gz)")
    parser.add_argument("--workers", type=int, default=os.cpu_count(), help="Number of threads (default: CPU count)")
    args = parser.parse_args()

    print(f"Scanning {args.directory} with {args.workers} workers", flush=True)

    t0 = time.perf_counter()
    with gzip.open(args.output, "wt", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, restval="")
        writer.writeheader()
        scan(args.directory, writer, args.workers)
    elapsed = time.perf_counter() - t0
    print(f"Elapsed: {elapsed / 3600:.2f} h ({elapsed:.0f} s)", flush=True)


if __name__ == "__main__":
    main()
