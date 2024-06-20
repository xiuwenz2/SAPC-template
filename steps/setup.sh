#!/bin/bash

stage=0
stop_stage=1

usr=???
source /home/${usr}/.bashrc
PYTHON_VIRTUAL_ENVIRONMENT=sapc

cwd=$(pwd)

if [ $stage -le 0 ] && [ $stop_stage -ge 0 ]; then
    echo "Stage 0: build conda environment..."
    
    if [ -n "```conda env list | grep -w "${PYTHON_VIRTUAL_ENVIRONMENT}"```" ]; then
        echo "Environment ${PYTHON_VIRTUAL_ENVIRONMENT} already exists."
    else
        conda create --name ${PYTHON_VIRTUAL_ENVIRONMENT} python=3.9 -y
    fi
    
fi

conda activate ${PYTHON_ENVIRONMENT_NAME}

if [ $stage -le 1 ] && [ $stop_stage -ge 1 ]; then
    echo "Stage 1: install dependencies..."
    
    python -m pip install tqdm
    python -m pip install soundfile ### soundfile==0.12.1
    python -m pip install numpy==1.23.4 scipy==1.10.1 numba==0.57.1
    python -m pip install librosa ### librosa==0.9.1
    python -m pip install nemo_text_processing ### nemo_text_processing==1.0.2
    
    cd ${cwd}
fi
