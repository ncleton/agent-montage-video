# Video Observer Agent

Purpose: inspect the source video and detect high-motion moments.

Inputs:

- Source video path.

Outputs:

- `work/analysis/motion_analysis.json`
- motion peaks suitable for visual accents and musical hits.

Implementation:

- Sample the video with FFmpeg.
- Convert frames to small grayscale buffers.
- Compute frame-to-frame mean absolute difference.
- Select local peaks with a minimum temporal distance.

