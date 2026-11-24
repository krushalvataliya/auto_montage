# Video Sequence & Duration Matching Logic

This document details the mathematical models and algorithmic rules used for numerical sorting, slow-motion timing, fair clip reuse, and millisecond-accurate duration matching.

---

## 1. Natural Numerical Sorting & Sequence Gap Detection

### The Problem
Lexicographical sorting places `vid10.mp4` before `vid2.mp4`:
$$\text{Lexical order: } [\text{"vid1"}, \text{"vid10"}, \text{"vid2"}, \text{"vid3"}]$$

### The Algorithm (`src/video_sorting.py`)
1. **Regex Extraction:** Filenames are split into prefix and numerical suffix:
   $$\text{Pattern: } \wedge(.*?)(?:[\_\-\s])?(\d+)\$$$
   For example:
   - `gfl1.mp4` $\rightarrow$ Prefix: `gfl`, Suffix: `1`
   - `travel_10.mp4` $\rightarrow$ Prefix: `travel`, Suffix: `10`
   - `outro.mp4` $\rightarrow$ Prefix: `outro`, Suffix: `None`
2. **Prefix Grouping:** Clips with the same prefix are grouped together:
   $$\text{Groups} = \{\text{"gfl"}: [1, 2, 3, 10], \text{"travel"}: [1, 2]\}$$
3. **Natural Ordering:** Items with numerical suffixes are sorted by their integer values:
   $$[1, 2, 3, 10]$$
4. **Gap Detection:** For each numerical group with min index $n_{\min}$ and max index $n_{\max}$:
   $$\text{Expected} = \{n_{\min}, n_{\min}+1, \dots, n_{\max}\}$$
   $$\text{Missing} = \text{Expected} \setminus \text{Actual}$$
   If $\text{Missing} \neq \emptyset$, the application logs a non-fatal warning:
   ```text
   Sequence gap detected in group 'gfl': missing indices [3, 5] (found 1 to 7)
   ```
5. **Fallback:** Non-numerical filenames fallback to natural alphanumeric sorting.

---

## 2. Slow-Motion Timestamp Transformation

### Theoretical Model
Let $t_{\text{in}}$ be the timestamp of an input frame and $S$ be the `slow_motion_speed` factor ($0 < S \le 1$).

The output presentation timestamp $t_{\text{out}}$ is governed by:
$$t_{\text{out}} = \frac{1}{S} \times t_{\text{in}}$$

The duration of the clip scales inversely with speed:
$$D_{\text{processed}} = \frac{D_{\text{original}}}{S}$$

### Example
For a $10.01\text{ s}$ clip at $S = 0.66$:
$$D_{\text{processed}} = \frac{10.01}{0.66} \approx 15.167\text{ s}$$

FFmpeg video filter implemented:
```text
setpts=1.515152*PTS,fps=30
```
This guarantees constant $30.0\text{ FPS}$ playback without dropped frames or stuttering.

---

## 3. Two-Stage Arrangement & Fair Random Reuse

The total footage must match the background music duration $T_{\text{music}}$ precisely.

### Stage 1: Sequential Playback
Clips are arranged in ascending numerical order:
$$C_1 \rightarrow C_2 \rightarrow C_3 \rightarrow \dots \rightarrow C_N$$

Let $T_{\text{seq}} = \sum_{i=1}^N D(C_i)$ be the total duration of the sequential pass.

- **Case A ($T_{\text{seq}} \ge T_{\text{music}}$):** Sequential clips provide sufficient footage. The sequence terminates at the clip that reaches $T_{\text{music}}$, trimming that clip. Stage 2 is skipped.
- **Case B ($T_{\text{seq}} < T_{\text{music}}$):** Additional footage is required:
  $$\Delta T = T_{\text{music}} - T_{\text{seq}}$$
  The pipeline transitions to Stage 2.

### Stage 2: Fair Random Reuse (Shuffle-Bag Algorithm)
When additional clips are required, clips are appended from available footage under three strict constraints:

1. **Non-Consecutive Constraint:**
   The newly selected clip $C_{k}$ must never equal the preceding clip $C_{k-1}$:
   $$C_k \neq C_{k-1}$$
2. **Fairness / Round-Robin Permutation:**
   Available clips are partitioned into randomized bags (permutations). All $N$ clips must be selected once in round $r$ before any clip can be selected in round $r+1$.
3. **Boundary Repeat Prevention:**
   When transitioning from bag $r$ to bag $r+1$, if the first element of bag $r+1$ matches the last element of bag $r$, it is swapped with another random element within bag $r+1$.
4. **Reproducibility:**
   An optional `random_seed` integer (e.g. `42`) can be specified in `config.yaml` to reproduce the exact same sequence layout across multiple runs.

---

## 4. Final Clip Trimming & Duration Synchronization

Let $\{S_1, S_2, \dots, S_m\}$ be the assembled sequence of clip segments with durations $\{d_1, d_2, \dots, d_m\}$.

To prevent black frames or frozen video frames, clips are accumulated until the running sum exceeds $T_{\text{music}}$ at index $m$:
$$\sum_{j=1}^{m-1} d_j < T_{\text{music}} \le \sum_{j=1}^m d_j$$

Segment $S_m$ is trimmed to:
$$d_m^* = T_{\text{music}} - \sum_{j=1}^{m-1} d_j$$

### Verification
The sum of all clip segments in the final assembly equals the background music duration:
$$\sum_{j=1}^{m-1} d_j + d_m^* \equiv T_{\text{music}}$$

This ensures millisecond-accurate alignment with the background music track.
