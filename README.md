# SAPC2 Template

## 1. Preprocess

**Preprocessed data is available on Box** and will be provided to all approved participants. If you need to run preprocessing yourself:

```bash
# Edit preprocess.sh to set CONDA_ENV_NAME, DATA_ROOT, PROJ_ROOT, then:
./preprocess.sh --start_stage 1 --stop_stage 3 --splits Train Dev
```

| Stage | What it does |
|---|---|
| 1 | Environment setup (conda + pip) |
| 2 | Extract tar files → `raw/` |
| 3 | Resample audio, copy JSONs, generate manifest CSVs, normalize refs |

Output: `DATA_ROOT/manifest/{Split}.csv` with columns `id`, `text`, `norm_text_with_disfluency`, `norm_text_without_disfluency`.

## 2. Submission Templates

| Track | Description | Starting Kit |
|---|---|---|
| Track 1 | Unconstrained ASR (accuracy) | [`track1_starting_kit/README.md`](track1_starting_kit/README.md) |
| Track 2 | Streaming ASR (accuracy + latency) | [`track2_starting_kit/README.md`](track2_starting_kit/README.md) |

## 3. Evaluation

Score ASR predictions: normalize hyp → sclite alignment → min-two-refs WER/CER.

**Input**: a hypothesis CSV (`--hyp-csv`) with at least two columns:

| Column | Description |
|---|---|
| `id` | Utterance ID (must match the manifest CSV) |
| `raw_hypos` | Raw hypothesis text (column name configurable via `--hyp-col`) |

Example:

```
id,raw_hypos
spk001_utt001,hello world
spk001_utt002,good morning
```

**Run**:

```bash
# Edit evaluate.sh to set DATA_ROOT, PROJ_ROOT, SCTK_DIR, then:
./evaluate.sh --start_stage 0 --stop_stage 2 --split Dev-all --hyp-csv /path/to/hyp.csv
```

| Stage | What it does | Run once? |
|---|---|---|
| 0 | Install SCTK (sclite) | ✓ |
| 1 | Prepare reference `.trn` files from manifest CSV | ✓ per split |
| 2 | Evaluate: normalize → sclite → compute WER/CER | per hypothesis |

**Output**: `DATA_ROOT/eval/metrics.{Split}.json` with `wer` and `cer`.

### Track 2 Latency (stage 3)

You can compute latency directly from a partial results JSON, even without `track2_bundle`.

Use the sister script `steps/eval/evaluate_latency.sh` (recommended for standalone latency).

```bash
# manifest CSV is required (must contain `id` and your MFA start-time column)
bash ./steps/eval/evaluate_latency.sh \
  --partial-json /path/to/Dev.partial_results.json \
  --manifest-csv /path/to/Dev_streaming.csv \
  --mfa-col mfa_speech_start \
  --out-json /path/to/latency.summary.json
```

Notes:
- `--manifest-csv` is required for latency evaluation.
- The CSV must include `id` and your MFA start-time column; use `--mfa-col` to specify its name (default: `mfa_speech_start`).


