# SAPC: speech accessibility project competition
![photo1](https://github.com/XIUWEN-ZHENG/SAPC/assets/96778918/c7d5ac78-6096-4f97-86fd-1d2ab4a060bb)

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
      ┃ ### overall ###
      ┃ ┣ SpeechAccessibility_{release}_Split.json
      ┃ ┣ SpeechAccessibility_{release}_Split_by_Contributors.json
      ┃ ┣ SpeechAccessibility_{release}_Dimension_Category_Description.json
      ┃ ### mismatch check ###
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
      ### run stage 0: Resampling audio files to 16k Hz (default), with processed audio files written as follows.

      /data
      
      ### Processed Audio Files ###
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

      <details>
        
      <summary>Manifest Generation</summary>
        
      ```plaintext  
      ### run stage 1: Generating preliminary wav2vec-like manifest to /manifest, with file struction as follows.
      
      /manifest
      
      ### Manifest Files ###
      ┣ train.tsv
      ┣ train.origin.wrd
      ┣ test.tsv
      ┣ test.origin.wrd
      ┣ dev.tsv
      ┣ dev.origin.wrd
      ```
      </details>

      <details>
        
      <summary>Manifest Normalization</summary>
        
      ```plaintext  
      ### run stage 2: Normalizing manifest in a wav2vec-like manner, with file struction as follows.
      
      /manifest
      
      ### Manifest Files ###
      ┣ train.wrd
      ┣ test.wrd
      ┣ dev.wrd
      ```

      ```plaintext  
      Normalization rules are listed as follows.
      
      + change "\’" & "\‘" back to "\'".
      + process "[...]": remove words within square brackets "[...]".
      + process "{...}": change uncertain words within curly brackets "{...}" to "UNK" except keeping human-guessed ones "{g:...}".
      + remove "*", "~" before nemo_text_processing.
      + nemo_text_processing for basic text normalization, including digital numbers, abbreviations, and special punctuations.
      + update transcription manually to solve the mismatch issues caused by annotation and/or text normalization, by checking brackets, numbers, abbrevations, word error rates, and confidence scores.
      + process "(...)": remove words within brackets "(...)" except keeping ones with prefix, like "(cs:...)", "(assistant:...)".
      + remove punctuations except "\'" within words.
      + change to upper case.
      + remove extra space.
      ```
      </details>
