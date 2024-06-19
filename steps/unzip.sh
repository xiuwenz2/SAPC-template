#!bin/sh

stage=0
stop_stage=1


## install 7zip
if [ $stage -le 0 ] && [ $stop_stage -ge 0 ]; then
    
    pkgname=7z2406-linux-x64.tar.xz     ### replace this link according to the arch
    wget https://www.7-zip.org/a/${pkgname}
    mkdir 7zip
    tar -xvf ${pkgname} -C 7zip
    rm ${pkgname}
    
fi


## unzip dataset
if [ $stage -le 1 ] && [ $stop_stage -ge 1 ]; then

    download=$PWD/DatasetDownload
    
    for file in `ls ${download} | grep "**.7z"`; do
        if [ "$file" == `ls ${download} | grep "Json.7z"` ]
        then
            7zip/7zz x ${download}/${file} -r -odata/doc
        else
            7zip/7zz x ${download}/${file} -r -odata/raw
        fi
    done
    
    for file in `ls ${download} | grep "**.json"`; do
        cp ${download}/${file} data/doc/${file}
    done
    
    for file in `ls data/raw | grep "**.7z"`; do
        7zip/7zz x data/raw/${file} -r -odata/raw
        rm data/raw/${file}
    done

fi
