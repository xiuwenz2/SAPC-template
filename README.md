# Template for the Speech Accessibility Project (SAP) Challenge

## Data Preparation
1. To use the SAP data (including the processed version), sign our data user agreement [here](https://speechaccessibilityproject.beckman.illinois.edu/conduct-research-through-the-project).

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
     
      ### Json Files III (mismatch check) ###
      ┣ SpeechAccessibility_{release}_Audio_Excluded.json
      ┣ SpeechAccessibility_{release}_Error_Correction.json
      ┣ SpeechAccessibility_{release}_Abbreviation_Decomposition.json
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
      ┃ ### mismatch check ###
      ┃ ┣ SpeechAccessibility_{release}_Audio_Excluded.json
      ┃ ┣ SpeechAccessibility_{release}_Error_Correction.json
      ┃ ┣ SpeechAccessibility_{release}_Abbreviation_Decomposition.json
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
      + update transcription manually to correct errors and decomposite abbreviations.
      + process "(...)": set the action attribute **--remove-parentheses** to remove words within parentheses "(...)" except keeping ones with prefix, like "(cs:...)", "(assistant:...)". Otherwise, keep everything within parentheses.
      + remove punctuations except "\'" within words.
      + change to upper case.
      + remove extra space.
      ```
      </details>
      
## Evaluation Scripts
+ The evaluation scripts are located in ```utils/```, including ```utils/evaluate.py``` and ```utils/metrics.py```. For testing purpose, use ```bert_score==0.3.13```.

## Submission Template
+ A template of the Whisper base model is provided in ```template/```. To submit correctly, modify ```template/inference.py``` and ```template/run.sh``` as needed, paying special attention to the ***TO-DOs***.
+ Make sure to include your model file! The model is not included in the template, as it is part of the Whisper package.
