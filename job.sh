#!/bin/bash
#SBATCH --job-name=disk-scan
#SBATCH --time=24:00:00
#SBATCH --ntasks=1
#SBATCH --output=logs/scan-%j.out

directory=$1
output=$2

mkdir -p logs
mkdir -p "$(dirname "$output")"

python scan.py "$directory" "$output" \
    --workers "${SLURM_CPUS_ON_NODE:-1}" \
    --log "logs/permission_denied-$SLURM_JOB_ID.log"
