# Training on Kaggle — batch-run recipe

`make_notebook.py` writes `isih_train.ipynb` for **interactive** runs: its
credentials cell reads Kaggle Secrets. Batch (API-pushed) kernels cannot read
Secrets, so a batch run needs two things the generator does not emit.

## 1. Swap the credentials cell

Replace the Kaggle-Secrets cell with this one (credentials come from the
private dataset `jiteeshghodke/cmems-creds`, one file `cmems.json` with
`username`/`password` keys — never commit real values anywhere):

```python
import json, os, glob
# Batch kernels can't read Kaggle Secrets, so credentials come from a private
# dataset. Kaggle mounts datasets for NEW kernels under
# /kaggle/input/datasets/<owner>/<slug>/ (legacy kernels: /kaggle/input/<slug>/),
# and the layout changed under us in Nov 2026 — so search, don't hardcode.
hits = glob.glob('/kaggle/input/**/cmems.json', recursive=True)
if not hits:
    for d, _, fs in os.walk('/kaggle/input'):
        print(d, fs)
    raise FileNotFoundError('cmems.json not found anywhere under /kaggle/input')
c = json.load(open(hits[0]))
os.environ['COPERNICUSMARINE_SERVICE_USERNAME'] = c['username']
os.environ['COPERNICUSMARINE_SERVICE_PASSWORD'] = c['password']
print('creds loaded from', hits[0])
```

## 2. Push with the kernel metadata

`kernel-metadata.json` in this directory is the template. Push with the new
token scheme (`KGAT_...`); the old `KAGGLE_USERNAME`/`KAGGLE_KEY` pair does
not work with these tokens:

```bash
export KAGGLE_API_TOKEN=<your KGAT token>   # never commit it
kaggle kernels push -p <dir with notebook + kernel-metadata.json>
kaggle kernels status <owner>/<slug>
```

## Failure modes already hit (fixes are in the notebook)

- pip half-upgrading numpy over the image breaks scipy/xarray
  (`_blas_supports_fpe`): the install cell pins numpy to the image's version
  inside the same `pip install`.
- NSIDC throws transient HTTP 500s: the download cell retries 3× and writes
  to `.part` files so a failed try can't leave a corrupt `.nc`.
- A cell saved as *markdown* silently skips in batch: the 2026-08-31
  checkpoints were lost this way. Check cell types before pushing.
