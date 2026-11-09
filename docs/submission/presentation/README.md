# Demo presentation (3 minutes)

Self-playing HTML presentation with animations, narration timeline and black subtitle bar.

## Record the video

1. Open `index.html` in Chrome (double click, or `python -m http.server 8765` in this folder and open `http://localhost:8765/index.html`).
2. Press fullscreen (`F`), start screen recording, press Space or click Play. The run lasts about 3 minutes and stops on the last slide.
3. Merge `narration.wav` into the recording. The audio starts at the exact moment you press Play (t = 0), so align the start of the audio with the first frame of the slides.

Options: `?audio=1` plays `narration.wav` from the page itself, `?t=95` starts at 95 s, `?freeze=95` shows a single frame. Keys: `R` restart, `A` audio on/off, `F` fullscreen.

## Files

| File | Purpose |
|---|---|
| `index.html` | Slides, animations, subtitles, player |
| `narration.wav` | Voice track (Windows System.Speech, voice David, rate +1, about +10%) |
| `subtitles.srt`, `subtitles.vtt` | Subtitle files with the same timings as the on-screen bar |
| `SCRIPT_TIMINGS.md` | Narration script with start time of every sentence |
| `script.json` | Source of narration and subtitle text |
| `build_presentation.py`, `tts.ps1` | Regenerate audio, timeline and data (`python build_presentation.py`) |
| `timeline.js`, `data.js` | Generated: slide timings and numbers read from `results/campaign/analysis` |

Numbers on the slides are read from `data.js`, which is generated from the committed analysis files. Drop the official logo at `assets/apart-logo.png` to replace the text wordmark.
