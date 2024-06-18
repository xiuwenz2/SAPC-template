#!bin/sh
base=/home/xiuwenz2/datasets/SpeechAcc
release=2024-04-30
download=${base}/DatasetDownload
database=${base}/${release}

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
