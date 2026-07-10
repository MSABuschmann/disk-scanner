#!/usr/bin/env python3
"""Strip a common path prefix from the path column of scan csv.gz files."""
from argparse import ArgumentParser
import gzip
import os

def strip_prefix(input_path, output_path, prefix):
    with gzip.open(input_path, "rt") as fin, gzip.open(output_path, "wt") as fout:
        header = next(fin)
        fout.write(header)
        path_col = header.strip().split(",").index("path")
        for line in fin:
            parts = line.split(",")
            p = parts[path_col]
            parts[path_col] = p[len(prefix):] if p.startswith(prefix) else p
            fout.write(",".join(parts))

def main():
    parser = ArgumentParser()
    parser.add_argument("files", nargs="+", help="Input .csv.gz files")
    parser.add_argument("--prefix", default="/global/scratch/projects/pc_heptheory", help="Prefix to strip")
    parser.add_argument("--inplace", action="store_true", help="Overwrite input files")
    args = parser.parse_args()

    for f in args.files:
        if args.inplace:
            tmp = f + ".tmp"
            strip_prefix(f, tmp, args.prefix)
            os.replace(tmp, f)
            print(f"Done: {f}")
        else:
            out = f.replace(".csv.gz", "_stripped.csv.gz")
            strip_prefix(f, out, args.prefix)
            print(f"Done: {out}")

if __name__ == "__main__":
    main()
