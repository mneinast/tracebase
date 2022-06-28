# KR Infusion Data Modifications

Robert Leach
12/7/2021

## Issues & Resolutions

### `TraceBase Reference_MN_exp027e K and R infusion.xlsx`

#### Error
```
DataRepo.utils.RequiredValueError: Values in column Age are required, but some found missing
```

Age column was empty in TraceBase Reference_MN_exp027e K and R infusion.xlsx

#### Resolution

- Age filled in with `0`s

### `exp027e_pos_lowmz_corrected.xlsx`

#### Error
```
DataRepo.utils.MissingSamplesError: 25 samples are missing: exp027e_01_scan2, exp027e_02_scan2, exp027e_03_scan2, exp027e_04_scan2, exp027e_05_scan2, exp027e_06_scan2, exp027e_07_scan2, exp027e_08_scan2, exp027e_09_scan2, exp027e_10_scan2, exp027e_11_scan2, exp027e_12_scan2, exp027e_13_scan2, exp027e_14_scan2, exp027e_15_scan2, exp027e_16_scan2, exp027e_17_scan2, exp027e_18_scan2, exp027e_19_scan2, exp027e_20_scan2, exp027e_21_scan2, exp027e_22_scan2, exp027e_23_scan2, exp027e_24_scan2, exp027e_blank_scan2
```
All of the sample names in the sample table end with "_scan1", but everything in the accucor file ends with "_scan2".  However, "_scan1" exists in the highmz accucor file.

#### Resolution

- Assuming these are MSRuns on the same samples and removing the "_scan#" suffix from all files.

#### Error
```
DataRepo.utils.MissingSamplesError: 1 samples are missing: exp027e_blank
```

I had noted that the accucore file had 25 columns and the sample table had 24 sample rows, but when I saw the last one was a blank, I thought the code would skip it, but that appears to be an incorrect assumption.  So I added "exp027e_blank" under "skip_samples" in the loading.yaml file.

# Multi-tracer-label modifications

Robert Leach
6/27/2022

Previous changes re-introduced original second tracer data for each column in the sample table file.  The new multi-tracer-label template was copied in and the data was pasted and modified to meet the template requirements.