#!/usr/bin/env bash
# Runpod bootstrap for the C4 AMI study.
#
# Installs Ollama, pulls the reader, fetches this repo and the AMI transcripts,
# then runs one job. Everything lives under /workspace (the pod's persistent
# volume), so a restarted pod resumes where it stopped.
#
#   bash bootstrap.sh speedtest     # 20 probes, no gate: measures seconds per call
#   bash bootstrap.sh ami           # registered design: gate, then sweep if it passes
#
# MODEL (default qwen2.5:32b) picks the reader: MODEL=qwen2.5:14b bash bootstrap.sh ami
set -euo pipefail

JOB="${1:?usage: bootstrap.sh speedtest|ami}"
case "$JOB" in
    speedtest|ami) ;;
    *) echo "unknown job: $JOB (expected speedtest or ami)" >&2; exit 2 ;;
esac
MODEL="${MODEL:-qwen2.5:32b}"
WORK=/workspace
REPO=https://github.com/ming3465/c4-speaker-attribution.git
AMI_ZIP=https://groups.inf.ed.ac.uk/ami/AMICorpusAnnotations/ami_public_manual_1.6.2.zip
export OLLAMA_MODELS="$WORK/ollama"

mkdir -p "$WORK/results"
cd "$WORK"

command -v ollama >/dev/null || curl -fsSL https://ollama.com/install.sh | sh
if ! pgrep -x ollama >/dev/null; then
    nohup ollama serve >"$WORK/ollama.log" 2>&1 &
    for _ in $(seq 30); do curl -sf localhost:11434/api/tags >/dev/null && break; sleep 1; done
fi
ollama pull "$MODEL"

[ -d c4-speaker-attribution ] || git clone -q "$REPO"
cd c4-speaker-attribution
git pull -q --ff-only
command -v uv >/dev/null || pip install -q uv
uv sync -q

if [ ! -f data/processed/ami.jsonl ]; then
    curl -fsSL -o /tmp/ami.zip "$AMI_ZIP"
    unzip -q -o /tmp/ami.zip -d data/raw/ami
    uv run python scripts/data/convert_ami.py
fi

DESIGN=(--dataset utterances --utterances data/processed/ami.jsonl --contexts window
        --window-size 20 --window-stride 10 --min-target-words 8
        --budgets 1.0 0.5 0.25 0.1 --allocation per-message --model "$MODEL")

case "$JOB" in
    speedtest)
        PYTHONHASHSEED=0 uv run python scripts/evaluation/run_attribution_frozen.py "${DESIGN[@]}" \
            --limit 20 --skip-gate --out-dir "$WORK/results/speedtest" ;;
    ami)
        PYTHONHASHSEED=0 uv run python scripts/evaluation/run_attribution_frozen.py "${DESIGN[@]}" \
            --limit 1200 --out-dir "$WORK/results/ami" ;;
    *)
        echo "unknown job: $JOB (expected speedtest or ami)" >&2
        exit 2 ;;
esac
