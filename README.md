# SAPC: speech accessibility project competition
![photo1](https://github.com/XIUWEN-ZHENG/SAPC/assets/96778918/c7d5ac78-6096-4f97-86fd-1d2ab4a060bb)
Write something here

## Data Prepration
1. To use the SAP data, sign our data user agreement [here](https://speechaccessibilityproject.beckman.illinois.edu/conduct-research-through-the-project).

2. Download and rename the data folder into ```/DatasetDownload```.
     <details>
     
     <summary>File Structure of /DatasetDownload</summary>
     
     ```plaintext  
      ### Audio Files ###
      ┣ SpeechAccessibility_{release}_000.7z
      ┣ SpeechAccessibility_{release}_001.7z
      ┣ ...
      ┣ SpeechAccessibility_{release}_011.7z
     
      ### Json Files I (per spk) ###
      ┣ SpeechAccessibility_{release}_Only_Json.7z
     
      ### Json Files II (overall) ###
      ┣ SpeechAccessibility_{release}_Split.json
      ┣ SpeechAccessibility_{release}_Split_by_Contributors.json
      ┣ SpeechAccessibility_{release}_Dimension_Category_Description.json
     
      ### Json Files III (mismatch check) ###
      ┣ SpeechAccessibility_{release}_Check_Brackets.json
      ┣ SpeechAccessibility_{release}_Check_Normalization.json
      ┣ SpeechAccessibility_{release}_Check_Abbreviations.json
      ┣ SpeechAccessibility_{release}_Check_WordErrorRate.json
     ```
     </details>


3. Build conda environment using ```bash steps/setup.sh```.

4. Unzip the data package using ```bash steps/unzip.sh```, from ```/DatasetDownload``` into ```/data``` with the file structure as follows.
      <details>
      
      <summary>File Structure of /data</summary>
      
      ```plaintext  
      ### Raw Audio Files ###
      ┣ raw
      ┃ ┣ {spk_id_1}
      ┃ ┃ ┣ {spk_id_1}_{utt_id_1}_xxxx.wav
      ┃ ┃ ┣ {spk_id_1}_{utt_id_2}_xxxx.wav
      ┃ ┃ ┣ ...
      ┃ ┃ ┣ {spk_id_1}.json
      ┃ ┣ {spk_id_2}
      ┃ ┣ ...
      
      ### Json Files ###
      ┣ doc
      ┃ ### per spk ###
      ┃ ┣ {spk_id_1}.json
      ┃ ┣ {spk_id_2}.json
      ┃ ┣ ...
      ┃ ### per spk ###
      ┃ ┣ SpeechAccessibility_{release}_Split.json
      ┃ ┣ SpeechAccessibility_{release}_Split_by_Contributors.json
      ┃ ┣ SpeechAccessibility_{release}_Dimension_Category_Description.json
      ┃ ### per spk ###
      ┃ ┣ SpeechAccessibility_{release}_Check_Brackets.json
      ┃ ┣ SpeechAccessibility_{release}_Check_Normalization.json
      ┃ ┣ SpeechAccessibility_{release}_Check_Abbreviations.json
      ┃ ┣ SpeechAccessibility_{release}_Check_WordErrorRate.json
      ```
      </details>
  
5. Preprocess the data using ```bash steps/preprocess.sh```.
      <details>
        
      <summary>Audio Resampling</summary>
        
      ```plaintext  
      ### run stage 0: audio resampling to 16k Hz (default), with processed audio files written as follows.
      
      /data
      
      ### Raw Audio Files ###
      ┣ processed
      ┃ ┣ train
      ┃ ┃ ┣ {train_spk_id_1}_{utt_id_1}_xxxx.wav
      ┃ ┃ ┣ ...
      ┃ ┣ dev
      ┃ ┃ ┣ {dev_spk_id_1}_{utt_id_1}_xxxx.wav
      ┃ ┃ ┣ ...
      ┃ ┣ test
      ┃ ┃ ┣ {test_spk_id_1}_{utt_id_1}_xxxx.wav
      ┃ ┃ ┣ ...
      ```
      </details>
