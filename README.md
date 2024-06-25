# SAPC: speech accessibility project competition
![photo1](https://github.com/XIUWEN-ZHENG/SAPC/assets/96778918/c7d5ac78-6096-4f97-86fd-1d2ab4a060bb)
Write something here

## Data Prepration
* To use the SAP data, sign our data user agreement [here](https://speechaccessibilityproject.beckman.illinois.edu/conduct-research-through-the-project).
* Download and rename the data folder into ```/DatasetDownload```, with the file structure as follows.

```plaintext
/DatasetDownload
 ### Audio files
 ┣ SpeechAccessibility_2024-04-30_000.7z
 ┣ SpeechAccessibility_2024-04-30_001.7z
 ┣ ...
 ┣ SpeechAccessibility_2024-04-30_011.7z
 ### Json files (per spk)
 ┣ SpeechAccessibility_2024-04-30_Only_Json.7z
 ### Json files (overall)
 ┣ SpeechAccessibility_2024-04-30_Split.json
 ┣ SpeechAccessibility_2024-04-30_Split_by_Contributors.json
 ┣ SpeechAccessibility_2024-04-30_Dimension_Category_Description.json
 ### Json files (mismatch check)
 ┣ SpeechAccessibility_2024-04-30_Check_Brackets.json
 ┣ SpeechAccessibility_2024-04-30_Check_Normalization.json
 ┣ SpeechAccessibility_2024-04-30_Check_Abbreviations.json
 ┣ SpeechAccessibility_2024-04-30_Check_WordErrorRate.json
```

* Unzip the data package using ```bash steps/unzip.sh```.
* Build conda environment using ```bash steps/setup.sh```.
* Preprocess the data using ```bash steps/preprocess.sh```.
