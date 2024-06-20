#!/bin/bash

stage=0
stop_stage=0

usr=???
source /home/${usr}/.bashrc
PYTHON_VIRTUAL_ENVIRONMENT=/home/${usr}/.conda/envs/sapc
conda activate ${PYTHON_VIRTUAL_ENVIRONMENT}

cwd=$(pwd)
working_dir=${cwd}
release=2024-04-30
splits="train dev test"

## run stage 0
if [ $stage -le 0 ] && [ $stop_stage -ge 0 ]; then
    echo "Stage 0: resample audios to 16k..."
    mkdir -p ${cwd}/data/processed
    for split in ${splits}; do
        mkdir -p ${cwd}/data/processed/${split}
        echo "writing ${split}-16k to ${datadest}"
        python ${cwd}/utils/resample.py \
            --tag ${split} \
            --release ${release} \
            --database ${cwd}/data \
            --datadest ${cwd}/data/processed/${split} \
            --sr 16000
    done
fi

## run stage 1
if [ $stage -le 1 ] && [ $stop_stage -ge 1 ]; then
    echo "Stage 1: Generate .tsv manifest..."
    mkdir -p ${manifest_dir}
    for split in ${splits}; do
        echo "writing ${release}-${split}.tsv to ${manifest_dir}/${splits}"
        python ${cwd}/utils/generate_tsv.py \
            --tag ${split} \
            --datadest ${datadest} \
            --manifest-dir ${manifest_dir}
    done
fi

## run stage 2
if [ $stage -le 2 ] && [ $stop_stage -ge 2 ]; then
    echo "Stage 2: Generate .wrd label..."
    for split in ${splits}; do
        echo "writing ${split}.origin.wrd to ${manifest_dir}"
        echo "prerequisite: install nemo_text_processing"
        python ${cwd}/utils/generate_wrd.py \
                --tag ${split} \
                --datadest ${datadest} \
                --manifest-dir ${manifest_dir}/${manifest_tag}
    done   
fi
