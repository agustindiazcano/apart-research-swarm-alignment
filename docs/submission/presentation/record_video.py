"""Render the presentation to an MP4 with narration, frame by frame.

Chrome (headless) loads index.html in capture mode; every frame calls window.__render(t)
through the DevTools protocol and saves a screenshot. ffmpeg then joins the frames with
narration.wav (the audio starts at t = 0, the same moment as the first frame).

Usage: python record_video.py [--fps 15] [--serve-url http://localhost:8780/index.html]
Requires: websocket-client, imageio-ffmpeg, Chrome, and the presentation served over http.
"""

from __future__ import annotations

import argparse
import base64
import json
import shutil
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

import imageio_ffmpeg
import websocket

HERE = Path(__file__).resolve().parent
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fps", type=int, default=15)
    ap.add_argument("--url", default="http://localhost:8780/index.html")
    ap.add_argument("--out", default=str(HERE / "output" / "demo_video.mp4"))
    args = ap.parse_args()

    total = json.loads((HERE / "timeline.js").read_text(encoding="utf-8").split("=", 1)[1].rstrip().rstrip(";"))["total"]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    frames = out.parent / "frames"
    shutil.rmtree(frames, ignore_errors=True)
    frames.mkdir()

    profile = tempfile.mkdtemp(prefix="chrome_rec_")
    proc = subprocess.Popen(
        [CHROME, "--headless=new", "--remote-debugging-port=9333", f"--user-data-dir={profile}",
         "--window-size=1920,1080", "--hide-scrollbars", "--mute-audio", "--force-device-scale-factor=1",
         f"{args.url}?freeze=0&capture=1"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        ws_url = None
        for _ in range(60):
            try:
                tabs = json.load(urllib.request.urlopen("http://127.0.0.1:9333/json"))
                pages = [t for t in tabs if t.get("type") == "page"]
                if pages:
                    ws_url = pages[0]["webSocketDebuggerUrl"]
                    break
            except Exception:
                time.sleep(0.5)
        if not ws_url:
            raise SystemExit("could not reach Chrome DevTools")
        ws = websocket.create_connection(ws_url, max_size=None)
        mid = 0

        def call(method: str, **params):
            nonlocal mid
            mid += 1
            ws.send(json.dumps({"id": mid, "method": method, "params": params}))
            while True:
                msg = json.loads(ws.recv())
                if msg.get("id") == mid:
                    return msg.get("result", {})

        call("Emulation.setDeviceMetricsOverride", width=1920, height=1080, deviceScaleFactor=1, mobile=False)
        time.sleep(1.5)
        n = int(total * args.fps) + 1
        t0 = time.time()
        for i in range(n):
            t = i / args.fps
            call("Runtime.evaluate", expression=f"window.__render({t:.4f})")
            shot = call("Page.captureScreenshot", format="jpeg", quality=88)
            (frames / f"{i:05d}.jpg").write_bytes(base64.b64decode(shot["data"]))
            if i % 150 == 0:
                print(f"frame {i}/{n}  {time.time() - t0:.0f}s", flush=True)
        ws.close()
    finally:
        proc.terminate()
        shutil.rmtree(profile, ignore_errors=True)

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run(
        [ffmpeg, "-y", "-loglevel", "error", "-framerate", str(args.fps), "-i", str(frames / "%05d.jpg"),
         "-i", str(HERE / "narration.wav"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
         "-c:a", "aac", "-b:a", "160k", "-shortest", str(out)],
        check=True,
    )
    shutil.rmtree(frames, ignore_errors=True)
    print("video:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
