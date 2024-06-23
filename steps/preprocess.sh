#!/bin/bash

stage=1
stop_stage=1

usr=???
source /home/${usr}/.bashrc
PYTHON_VIRTUAL_ENVIRONMENT=/home/${usr}/.conda/envs/sapc
conda activate ${PYTHON_VIRTUAL_ENVIRONMENT}

cwd=$(pwd)
release=2024-04-30
# splits="train dev test"
splits="dev test"

## run stage 0
if [ $stage -le 0 ] && [ $stop_stage -ge 0 ]; then
    echo "Stage 0: resample audios to 16k..."
    mkdir -p ${cwd}/data/processed
    for split in ${splits}; do
        mkdir -p ${cwd}/data/processed/${split}
        echo "writing ${split}-16k to ${cwd}/data/processed/${split}"
        python ${cwd}/utils/resample.py \
            --split ${split} \
            --release ${release} \
            --database ${cwd}/data \
            --sr 16000
    done
fi

## run stage 1
if [ $stage -le 1 ] && [ $stop_stage -ge 1 ]; then
    echo "Stage 1: Generate .origin.tsv manifest..."
    mkdir -p ${cwd}/manifest
    for split in ${splits}; do
        echo "writing ${split}.tsv && ${split}.origin.wrd to ${cwd}/manifest"
        python ${cwd}/utils/generate_manifest.py \
            --split ${split} \
            --data-dir ${cwd}/data/processed \
            --manifest-dir ${cwd}/manifest
    done
fi

## run stage 2
if [ $stage -le 2 ] && [ $stop_stage -ge 2 ]; then
    echo "Stage 2: Generate .wrd label..."
    for split in ${splits}; do
        echo "writing ${split}.origin.wrd && ${split}.tsv to ${cwd}/manifest"
        python ${cwd}/utils/generate_origin_wrd.py \
                --split ${split} \
                --data-dir ${cwd}/data/processed \
                --manifest-dir ${cwd}/manifest
#         echo "writing ${split}.wrd to ${cwd}/manifest"
#         python ${cwd}/utils/generate_wrd.py \
#                 --tag ${split} \
#                 --data-dir ${datadest} \
#                 --manifest-dir ${cwd}/manifest/${split}
    done   
fi
