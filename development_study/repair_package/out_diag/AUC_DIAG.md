# Diagnostic: ranking (AUC) against decisions (argmax) for the frozen FP16 head

Unplanned, descriptive, development data. Heads are fitted on FP16 vectors only. `AUC` is the macro one-vs-rest AUC of each class score (the class logit; the softmax probability gives the second number). `Accuracy` is the argmax decision of the same head.


## Style A (5 folds of repeat 0, mean over folds), `end` position

| Vectors given to the FP16 head | Action: accuracy | Action: AUC (logit / probability) | Sensor: accuracy | Sensor: AUC | Priority: accuracy | Priority: AUC |
|---|---|---|---|---|---|---|
| FP16 vectors (reference) | 99.2% | 0.994 / 1.000 | 76.3% | 0.902 / 0.916 | 72.0% | 0.863 / 0.878 |
| raw Q4 vectors (frozen head) | 49.8% | 0.973 / 0.958 | 39.8% | 0.793 / 0.758 | 42.8% | 0.822 / 0.799 |
| Q4 recentred (C1) | 92.8% | 0.973 / 0.993 | 61.2% | 0.793 / 0.799 | 67.7% | 0.822 / 0.834 |
| Q4 affine map (C2) | 97.9% | 0.989 / 0.999 | 74.5% | 0.893 / 0.909 | 69.9% | 0.851 / 0.867 |
| raw Q8 vectors (frozen head) | 95.4% | 0.992 / 0.999 | 71.1% | 0.901 / 0.905 | 73.1% | 0.861 / 0.875 |

## Style B (fit on all style A), `end` position

| Vectors given to the FP16 head | Action: accuracy | Action: AUC (logit / probability) | Sensor: accuracy | Sensor: AUC | Priority: accuracy | Priority: AUC |
|---|---|---|---|---|---|---|
| FP16 vectors (reference) | 90.8% | 0.963 / 0.986 | 68.3% | 0.873 / 0.881 | 72.2% | 0.858 / 0.877 |
| raw Q4 vectors (frozen head) | 39.2% | 0.918 / 0.882 | 43.3% | 0.729 / 0.735 | 34.4% | 0.842 / 0.828 |
| Q4 recentred (C1) | 82.5% | 0.918 / 0.954 | 51.7% | 0.729 / 0.724 | 67.8% | 0.842 / 0.856 |
| Q4 affine map (C2) | 90.0% | 0.954 / 0.985 | 60.0% | 0.829 / 0.835 | 71.1% | 0.854 / 0.874 |
| raw Q8 vectors (frozen head) | 88.8% | 0.963 / 0.983 | 73.3% | 0.864 / 0.870 | 74.4% | 0.852 / 0.872 |

## Style A, `prefix` position

| Vectors given to the FP16 head | Action: accuracy | Action: AUC (logit / probability) | Sensor: accuracy | Sensor: AUC | Priority: accuracy | Priority: AUC |
|---|---|---|---|---|---|---|
| FP16 vectors (reference) | 98.7% | 0.996 / 1.000 | 76.7% | 0.897 / 0.910 | 82.2% | 0.912 / 0.930 |
| raw Q4 vectors (frozen head) | 90.7% | 0.990 / 0.994 | 69.6% | 0.863 / 0.874 | 51.4% | 0.877 / 0.866 |
| Q4 recentred (C1) | 95.5% | 0.990 / 0.997 | 71.3% | 0.863 / 0.875 | 76.1% | 0.877 / 0.896 |
| Q4 affine map (C2) | 97.6% | 0.995 / 0.999 | 74.3% | 0.886 / 0.901 | 80.4% | 0.904 / 0.920 |
| raw Q8 vectors (frozen head) | 99.0% | 0.996 / 1.000 | 75.4% | 0.897 / 0.910 | 81.8% | 0.909 / 0.926 |

## Style B, `prefix` position

| Vectors given to the FP16 head | Action: accuracy | Action: AUC (logit / probability) | Sensor: accuracy | Sensor: AUC | Priority: accuracy | Priority: AUC |
|---|---|---|---|---|---|---|
| FP16 vectors (reference) | 94.2% | 0.982 / 0.993 | 70.0% | 0.881 / 0.889 | 67.8% | 0.834 / 0.845 |
| raw Q4 vectors (frozen head) | 79.2% | 0.972 / 0.976 | 63.3% | 0.831 / 0.838 | 33.9% | 0.775 / 0.748 |
| Q4 recentred (C1) | 90.5% | 0.972 / 0.987 | 63.3% | 0.831 / 0.838 | 53.3% | 0.775 / 0.778 |
| Q4 affine map (C2) | 94.2% | 0.982 / 0.992 | 64.4% | 0.869 / 0.875 | 69.4% | 0.844 / 0.856 |
| raw Q8 vectors (frozen head) | 93.5% | 0.983 / 0.992 | 72.2% | 0.883 / 0.892 | 68.9% | 0.826 / 0.839 |
