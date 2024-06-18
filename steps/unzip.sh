#!bin/sh
download=$PWB/DatasetDownload
database=data/raw

for file in `ls ${download} | grep "**.7z"`; do
    7za x ${download}/${file} -r -o${database}
done

for file in `ls ${download} | grep "**.json"`; do
    cp ${download}/${file} ${database}/${file}
done

for file in `ls ${database} | grep "**.7z"`; do
    7za x ${database}/${file} -r -o${database}
    rm ${database}/${file}
done

# ls -lR | grep "^d" | wc -l
