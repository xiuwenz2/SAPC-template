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

See [`track1_starting_kit/README.md`](track1_starting_kit/README.md).

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


