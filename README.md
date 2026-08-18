# pyCOSP_full

Standalone, minimal copy of the full Cortical Silent Period (CoSP) detection app.


## Files

- `COSP.py` — entry point. Run this to launch the app.
- `ui.py` — auto-generated Qt UI code (from `ui.ui`, via pyuic5). Imported by
  `COSP.py` as `from ui import Ui_MainWindow`. Do not hand-edit; regenerate from
  `ui.ui` instead.
- `ui.ui` — Qt Designer source for the UI. Edit this in Designer, then regenerate
  `ui.py` with:
  `pyuic5 ui.ui -o ui.py`
- `requirements.txt` — Python dependencies.

## Run

```
pip install -r requirements.txt
python COSP.py
```

## What this app does

1. **Load EDF** — reads a raw EMG recording via `mne.io.read_raw_edf`.
2. **Stimulus artefact detection** (`stimulus_artefact_finder`) — band-passes near
   the Nyquist range and finds the peak per trace to locate the stimulus time.
3. **Filter** (`filter`) — applies a user-set band-pass filter (Low/High Cut
   spin boxes), then optionally:
   - **TKO** (Teager-Kaiser Operator, `TKO()`) — a nonlinear energy operator via
     `np.lib.stride_tricks.sliding_window_view`.
   - **Rectify** — full-wave rectification (`np.abs`).
4. **Detect** (`cosp_finder_moving_std`) — the core CoSP algorithm:
   - Computes a moving standard deviation over a user-set window size.
   - Thresholds it against the pre-stimulus baseline STD.
   - Finds the longest contiguous "quiet" (sub-threshold) epoch within a
     user-set detection window (`find_longest_epoch`).
   - Reports the **PCOS** duration and its offset from the stimulus, and
     annotates both plots.
5. **Backward/Forward** — step through channel traces; **X key hold + drag** —
   manually measure an epoch on the raw trace.


