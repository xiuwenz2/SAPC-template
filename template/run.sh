#!/bin/bash
'''
Note the template for remote evaluation on a private server,
so DO NOT change anything other than the TO-DOs, including
file names!!!
######## TO-DO 1: Please provide your contact information ########
(e.g.,) Email: xiuwenz2@illinois.edu
##################################################################
'''

stage=0
stop_stage=3

team_name=$1
submission_pk=$2

source ~/.bashrc
source ~/miniconda3/etc/profile.d/conda.sh
PYTHON_ENVIRONMENT=${team_name}
root=/taiga/downloads/${team_name}/${submission_pk}

######## TO-DO 2: specify your python version ########
python_version=3.9
######################################################

if [ $stage -le 0 ] && [ $stop_stage -ge 0 ]; then
    echo "Stage 0: Installing conda environment..."
    if conda info --envs | grep -q ${PYTHON_ENVIRONMENT}; then
        echo "Environment ${PYTHON_ENVIRONMENT} already exists. Deleting it..."
        conda remove --name ${PYTHON_ENVIRONMENT} --all --yes
    fi
    echo "Creating environment ${PYTHON_ENVIRONMENT}..."
    conda create --name ${PYTHON_ENVIRONMENT} python=${python_version} --yes
fi
conda activate ${PYTHON_ENVIRONMENT}

if [ $stage -le 1 ] && [ $stop_stage -ge 1 ]; then
    echo "Stage 1: Installing dependencies..."
    ######## TO-DO 3: add any dependencies needed for model inference ########
    pip install numpy==1.23.4
    pip install torch==1.12.0+cu116 torchvision==0.13.0+cu116 torchaudio==0.12.0+cu116 -f https://download.pytorch.org/whl/cu116/torch_stable.html
    pip install git+https://github.com/openai/whisper.git
    pip install tqdm
    ##########################################################################
fi

if [ $stage -le 2 ] && [ $stop_stage -ge 2 ]; then
    echo "Stage 2: Running inference..."

    splits='test1 test2'
    output_pth=${root}/inference
    mkdir -p ${output_pth}
    
    len_test1=7601
    len_test2=8043
    
    for split in ${splits}; do
        output_name=${output_pth}/${split}.hypo
        output_len="len_${split}"
        if [ -e "${output_name}" ] && [ "$(wc -l < "$output_name")" -eq "${!output_len}" ]; then
            echo "File already exists, skipping model inference..."
            
        else
        ######## TO-DO 4: change inference.py w.r.t. your model ########
            python ${root}/inference.py \
                --root ${root} \
                --split ${split} \
                --output-name ${output_name}
        ################################################################
        fi
    done
    conda deactivate
fi

if [ $stage -le 3 ] && [ $stop_stage -ge 3 ]; then
    echo "Stage 3: Evaluating results..."

    PYTHON_ENVIRONMENT=evaluate
    conda activate ${PYTHON_ENVIRONMENT}

    python3 /taiga/utils/evaluate.py \
        --submission-team-name ${team_name} \
        --submission-pk ${submission_pk}

    conda deactivate
fi
