#!/usr/bin/env bash
# Runpod bootstrap for the C4 attribution study.
#
# Installs Ollama, pulls the reader, fetches this repo and one corpus, then
# runs one job. Everything lives under /workspace (the pod's persistent
# volume), so a restarted pod resumes where it stopped: finished CSV rows and
# cached summaries are skipped.
#
#   bash bootstrap.sh speedtest    # 20 probes, no gate: measures seconds per call
#   bash bootstrap.sh sweep        # registered design: gate, then sweep if it passes
#   bash bootstrap.sh summary      # same design, LLM-summary compressor (qwen2.5:7b summarizer)
#   bash bootstrap.sh swap         # label-swap arm alone, on every eligible probe
#
# DATASET picks the corpus (default ami): ami | icsi | elitr | supreme
# MODEL    picks the reader (default qwen2.5:32b)
# NUM_CTX  overrides the reader's context window (default: per dataset, below)
# LIMIT    overrides the probe cap (default 1200; 1000 for the swap arm)
#
#   DATASET=icsi MODEL=qwen2.5:14b bash bootstrap.sh sweep
#
# "ami" is accepted as an older name for "sweep".
set -euo pipefail

JOB="${1:?usage: bootstrap.sh speedtest|sweep|summary|swap}"
if [ "$JOB" = ami ]; then JOB=sweep; fi    # the name this script used before DATASET existed
case "$JOB" in
    speedtest|sweep|summary|swap) ;;
    *) echo "unknown job: $JOB (expected speedtest, sweep, summary or swap)" >&2; exit 2 ;;
esac

DATASET="${DATASET:-ami}"
case "$DATASET" in
    ami|icsi|elitr|supreme) ;;
    *) echo "unknown dataset: $DATASET (expected ami, icsi, elitr or supreme)" >&2; exit 2 ;;
esac

MODEL="${MODEL:-qwen2.5:32b}"
SUMMARIZER="${SUMMARIZER:-qwen2.5:7b}"
# ELITR and Supreme Court windows run long: a handful of probes pass 4,096
# tokens, and Ollama truncates from the left, taking the roster with it.
case "$DATASET" in
    elitr|supreme) NUM_CTX="${NUM_CTX:-16384}" ;;
    *)             NUM_CTX="${NUM_CTX:-8192}" ;;
esac
if [ "$JOB" = swap ]; then LIMIT="${LIMIT:-1000}"; else LIMIT="${LIMIT:-1200}"; fi

WORK="${WORK:-/workspace}"      # overridable so the script can be dry-run off-pod
REPO=https://github.com/ming3465/c4-speaker-attribution.git
SUPREME_YEARS="${SUPREME_YEARS:-2017 2018 2019}"
export OLLAMA_MODELS="$WORK/ollama"

mkdir -p "$WORK/results"
cd "$WORK"

unpack() {  # unpack <zip> <dir>; the PyTorch image does not always carry unzip
    mkdir -p "$2"
    if command -v unzip >/dev/null; then unzip -q -o "$1" -d "$2"
    else python3 -c "import sys,zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" "$1" "$2"
    fi
}

command -v ollama >/dev/null || curl -fsSL https://ollama.com/install.sh | sh
if ! pgrep -x ollama >/dev/null; then
    nohup ollama serve >"$WORK/ollama.log" 2>&1 &
    for _ in $(seq 30); do curl -sf localhost:11434/api/tags >/dev/null && break; sleep 1; done
fi
ollama pull "$MODEL"
if [ "$JOB" = summary ]; then ollama pull "$SUMMARIZER"; fi

[ -d c4-speaker-attribution ] || git clone -q "$REPO"
cd c4-speaker-attribution
git pull -q --ff-only
command -v uv >/dev/null || pip install -q uv
uv sync -q

UTTERANCES="data/processed/$DATASET.jsonl"
if [ ! -f "$UTTERANCES" ]; then
    case "$DATASET" in
        ami)
            curl -fsSL -o /tmp/ami.zip \
                https://groups.inf.ed.ac.uk/ami/AMICorpusAnnotations/ami_public_manual_1.6.2.zip
            unpack /tmp/ami.zip data/raw/ami
            uv run python scripts/data/convert_ami.py ;;
        icsi)
            curl -fsSL -o /tmp/icsi.zip \
                https://groups.inf.ed.ac.uk/ami/ICSICorpusAnnotations/ICSI_core_NXT.zip
            unpack /tmp/icsi.zip data/raw/icsi
            uv run python scripts/data/convert_icsi.py ;;
        elitr)
            # LINDAT handle 11234/1-4692. The old XMLUI bitstream URL is dead
            # after the DSpace 7 migration; this is the REST one. See data/README.md.
            curl -fsSL -o /tmp/elitr.zip \
                https://lindat.mff.cuni.cz/repository/server/api/core/bitstreams/76466f35-1bac-47bf-958b-c235b1fb4966/content
            unpack /tmp/elitr.zip data/raw/elitr
            uv run python scripts/data/convert_elitr.py ;;
        supreme)
            # ConvoKit's per-year zips stop at 2019; later years answer 404
            # with an HTML page that curl -o would happily save as a .zip.
            mkdir -p data/raw/supreme
            for year in $SUPREME_YEARS; do
                curl -fsSL -o "data/raw/supreme/supreme-$year.zip" \
                    "https://zissou.infosci.cornell.edu/convokit/datasets/supreme-corpus/supreme-$year.zip"
            done
            uv run python scripts/data/convert_supreme.py --years $SUPREME_YEARS ;;
    esac
fi

DESIGN=(--dataset utterances --utterances "$UTTERANCES" --contexts window
        --window-size 20 --window-stride 10 --min-target-words 8
        --budgets 1.0 0.5 0.25 0.1 --model "$MODEL" --num-ctx "$NUM_CTX")
OUT="$WORK/results/$JOB-$DATASET-${MODEL//:/-}"

case "$JOB" in
    speedtest)
        PYTHONHASHSEED=0 uv run python scripts/evaluation/run_attribution_frozen.py "${DESIGN[@]}" \
            --allocation per-message --limit 20 --skip-gate --out-dir "$WORK/results/speedtest-$DATASET" ;;
    sweep)
        PYTHONHASHSEED=0 uv run python scripts/evaluation/run_attribution_frozen.py "${DESIGN[@]}" \
            --allocation per-message --limit "$LIMIT" --out-dir "$OUT" ;;
    summary)
        PYTHONHASHSEED=0 uv run python scripts/evaluation/run_attribution_frozen.py "${DESIGN[@]}" \
            --compressor summary --summarizer-model "$SUMMARIZER" --limit "$LIMIT" --out-dir "$OUT" ;;
    swap)
        PYTHONHASHSEED=0 uv run python scripts/evaluation/run_attribution_frozen.py "${DESIGN[@]}" \
            --allocation per-message --swap-only --limit "$LIMIT" --out-dir "$OUT" ;;
esac
