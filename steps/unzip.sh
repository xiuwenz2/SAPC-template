#!/bin/bash

stage=1
stop_stage=1

## unzip dataset
if [ $stage -le 1 ] && [ $stop_stage -ge 1 ]; then

    mkdir -p $PWD/data
    mkdir -p $PWD/data/raw
    
    splits="Train Dev"
    for split in ${splits}; do
        download=$PWD/SpeechAccessibility_Competition_Release/${split}

        for file in `ls ${download} | grep "**.tar"`; do
            if [ "$file" != `ls ${download} | grep "Json.tar"` ]; then
                tar -xf ${download}/${file} -C $PWD/data/raw
            fi
        done

        for file in `ls $PWD/data/raw | grep "**.tar"`; do
            tar -xf $PWD/data/raw/${file} -C $PWD/data/raw
            rm $PWD/data/raw/${file}
        done
    done

fi
