#!bin/sh
download=$PWB/DatasetDownload
database=$PWB/data
mkdir -p ${database}; mkdir -p ${database}/raw; mkdir -p ${database}/doc

for file in `ls ${download} | grep "**.7z"`; do
    echo "$file already merged"
    if [grep "Json.7z"]; then
        
    fi
    7za x ${download}/${file} -r -o${database}
done

for file in `ls ${download} | grep "**.json"`; do
    cp ${download}/${file} ${database}/doc/${file}
done

for file in `ls ${database}/raw | grep "**.7z"`; do
    7za x ${database}/raw/${file} -r -o${database}/raw
    rm ${database}/raw/${file}
done
