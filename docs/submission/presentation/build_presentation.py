"""Build narration audio, subtitles, timeline and data files for the demo presentation.

Steps: synthesize one WAV per sentence (Windows System.Speech), measure durations,
concatenate into narration.wav, write subtitles (SRT, VTT), timeline.js and data.js.
Data shown on the slides is read from results/campaign/analysis, never typed by hand.
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ANALYSIS = ROOT / "results" / "campaign" / "analysis"
CLIPS = HERE / "clips"


def read_csv(name: str) -> list[dict[str, str]]:
    with open(ANALYSIS / name, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def synthesize(sentences: list[dict], voice: str, rate: int) -> None:
    items = [{"id": s["id"], "text": s["say"]} for s in sentences]
    tmp = HERE / "tts_input.json"
    tmp.write_text(json.dumps(items), encoding="utf-8")
    subprocess.run(
        [
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
            str(HERE / "tts.ps1"), "-Json", str(tmp), "-OutDir", str(CLIPS),
            "-Voice", voice, "-Rate", str(rate),
        ],
        check=True,
    )
    tmp.unlink()


def srt_time(t: float, sep: str) -> str:
    ms = int(round(t * 1000))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def main() -> int:
    spec = json.loads((HERE / "script.json").read_text(encoding="utf-8"))
    sentences: list[dict] = []
    for slide in spec["slides"]:
        for i, s in enumerate(slide["sentences"]):
            sentences.append({"id": f"{slide['id']}_{i}", "slide": slide["id"], **s})

    if "--skip-tts" not in sys.argv:
        synthesize(sentences, spec["voice"], spec["rate"])

    params = None
    frames: dict[str, bytes] = {}
    durations: dict[str, float] = {}
    for s in sentences:
        with wave.open(str(CLIPS / f"{s['id']}.wav"), "rb") as w:
            p = w.getparams()[:3]
            if params is None:
                params = p
            elif p != params:
                raise SystemExit(f"audio format mismatch in {s['id']}")
            n = w.getnframes()
            frames[s["id"]] = w.readframes(n)
            durations[s["id"]] = n / w.getframerate()
    assert params is not None
    nch, width, rate = params
    silence = lambda sec: b"\x00" * (int(rate * sec) * nch * width)  # noqa: E731

    t = spec["lead_in_s"]
    audio = bytearray(silence(spec["lead_in_s"]))
    cues = []
    slides_out = []
    for slide in spec["slides"]:
        first = t
        items = []
        for s in [x for x in sentences if x["slide"] == slide["id"]]:
            dur = durations[s["id"]]
            items.append({"start": round(t, 3), "end": round(t + dur, 3), "text": s["sub"]})
            cues.append((t, t + dur, s["sub"]))
            audio += frames[s["id"]] + silence(spec["gap_s"])
            t += dur + spec["gap_s"]
        slides_out.append({"id": slide["id"], "start": round(first, 3), "end": round(t, 3), "sentences": items})
    audio += silence(spec["tail_s"])
    total = t + spec["tail_s"]
    slides_out[-1]["end"] = round(total, 3)
    # slide boundaries: each slide starts when its first sentence starts (cover from 0)
    slides_out[0]["start"] = 0.0

    with wave.open(str(HERE / "narration.wav"), "wb") as out:
        out.setnchannels(nch)
        out.setsampwidth(width)
        out.setframerate(rate)
        out.writeframes(bytes(audio))

    (HERE / "timeline.js").write_text(
        "window.TIMELINE = " + json.dumps({"total": round(total, 3), "slides": slides_out}, indent=1) + ";\n",
        encoding="utf-8",
    )
    srt = []
    vtt = ["WEBVTT", ""]
    for i, (a, b, txt) in enumerate(cues, 1):
        srt += [str(i), f"{srt_time(a, ',')} --> {srt_time(b, ',')}", txt, ""]
        vtt += [f"{srt_time(a, '.')} --> {srt_time(b, '.')}", txt, ""]
    (HERE / "subtitles.srt").write_text("\n".join(srt), encoding="utf-8")
    (HERE / "subtitles.vtt").write_text("\n".join(vtt), encoding="utf-8")

    md = ["# Narration script and timings", "", f"Total length: {total:.1f} s", ""]
    for sl in slides_out:
        md.append(f"## {sl['id']} ({sl['start']:.1f} s to {sl['end']:.1f} s)")
        md.append("")
        for it in sl["sentences"]:
            md.append(f"- [{it['start']:.1f}] {it['text']}")
        md.append("")
    (HERE / "SCRIPT_TIMINGS.md").write_text("\n".join(md), encoding="utf-8")

    # data for the slides, from analysis outputs
    data = {
        "kinetics": [
            {"round": int(r["round"]), "topology": r["topology"], "harm": r["harm"], "mean": float(r["infected_mean"])}
            for r in read_csv("kinetics_a1.csv")
        ],
        "arms": [
            {
                "arm": r["arm"], "topology": r["topology"], "harm": r["harm"], "defense": r["defense"],
                "episodes": int(r["episodes"]), "exfil": int(r["observed_exfiltrations"]),
            }
            for r in read_csv("arm_summary.csv")
        ],
        "panel_a": [
            {k: r[k] for k in ("detector", "playbook", "auroc", "fpr", "negative_messages")}
            for r in read_csv("panel_a.csv")
        ],
        "paired": [
            {k: r[k] for k in ("defense", "exfiltration_reduction", "holm_p", "mcnemar_p", "utility_loss", "pairs_complete")}
            for r in read_csv("paired_comparisons.csv")
        ],
        "billing": {k: v for k, v in read_csv("billing_totals.csv")[0].items()},
        "intent_audit": json.loads((ANALYSIS / "intent_agreement.json").read_text(encoding="utf-8")),
        "protocol": {"pilot": 3, "train": 15},
    }
    (HERE / "data.js").write_text("window.DATA = " + json.dumps(data, indent=1) + ";\n", encoding="utf-8")
    print(f"total {total:.1f} s, {len(sentences)} sentences")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
