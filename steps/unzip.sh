#!bin/sh
download=$PWD/DatasetDownload
database=$PWD/data
mkdir -p ${database}; mkdir -p ${database}/raw; mkdir -p ${database}/doc

for file in `ls ${download} | grep "**.7z"`; do
    if [ "$file" == `ls ${download} | grep "Json.7z"` ]
    then
        7za x ${download}/${file} -r -o${database}/doc
    else
        7za x ${download}/${file} -r -o${database}/raw
    fi
done

for file in `ls ${download} | grep "**.json"`; do
    cp ${download}/${file} ${database}/doc/${file}
done

for file in `ls ${database}/raw | grep "**.7z"`; do
    7za x ${database}/raw/${file} -r -o${database}/raw
    rm ${database}/raw/${file}
done
