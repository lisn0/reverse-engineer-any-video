"""Opt-in smoke test using real FFmpeg, Tesseract and a cached faster-whisper model."""
import functools
import http.server
import json
import os
from pathlib import Path
import subprocess
import struct
import sys
import tempfile
import threading
import unittest

SCRIPTS = (Path(__file__).resolve().parents[1] / "plugins/reverse-engineer-any-video/skills"
           / "reverse-engineer-any-video/scripts")


def run_script(script, *args):
    result = subprocess.run([sys.executable, "-B", str(SCRIPTS / script), *map(str, args)],
                            capture_output=True, text=True)
    if result.returncode:
        raise AssertionError(f"{script} exited {result.returncode}: {result.stderr}")
    return json.loads(result.stdout)


@unittest.skipUnless(os.environ.get("VIDEO_INTEGRATION") == "1", "requires local media tools and ASR model")
class VideoIntegration(unittest.TestCase):
    def test_index_and_search_local_and_url_video(self):
        with tempfile.TemporaryDirectory() as work:
            work = Path(work)
            voice, clip = work / "voice.wav", work / "clip.mp4"
            subprocess.run(["espeak-ng", "-v", "en-us", "-s", "145", "-w", str(voice),
                            "The copper valve is open. Turn the knob to the left."], check=True)
            subprocess.run([
                "ffmpeg", "-nostdin", "-v", "error", "-f", "lavfi", "-i",
                "color=c=0x171717:s=640x360:r=25:d=12", "-itsoffset", "1.5", "-i", str(voice),
                "-vf", "drawtext=font='DejaVu Sans':text=CALIBRATION COMPLETE:fontcolor=white:"
                "fontsize=34:x=(w-tw)/2:y=(h-th)/2:enable='between(t,6,9)'",
                "-c:v", "libx264", "-threads", "2", "-c:a", "aac", str(clip),
            ], check=True)

            index = work / "index"
            result = run_script("video.py", "index", clip, "--language", "en", "--out", index)
            self.assertEqual(result["overview"][0]["tile_times_s"], list(range(12)))
            self.assertTrue((index / result["overview"][0]["image"]).is_file())
            said = run_script("video.py", "search", "copper valve", index, "--track", "said")["results"][0]
            self.assertEqual(len(said["hits"]), 1)
            self.assertGreaterEqual(said["hits"][0]["start"], 1.5)
            self.assertLess(said["hits"][0]["end"], 4)
            shown = run_script("video.py", "search", "calibration complete", index, "--track", "shown")["results"][0]
            self.assertEqual(len(shown["hits"]), 1)
            self.assertEqual((shown["hits"][0]["first_seen"], shown["hits"][0]["last_seen"]), (6, 9))
            self.assertTrue(Path(shown["hits"][0]["image"]).is_file())

            review = work / "review"
            run_script("evidence.py", clip, "--review-at", "7", "--out", review)
            decoded = json.loads((review / "review.json").read_text())
            sheet = decoded["windows"][0]["sheets"][0]
            self.assertGreaterEqual(len(sheet["tile_times_s"]), 10)
            self.assertTrue((review / sheet["sheet"]).is_file())

            crop = work / "crop.png"
            still = run_script("video.py", "frame", index, "--at", "00:06.011",
                               "--box", "0.25,0.25,0.5,0.5", "--out", crop)
            self.assertAlmostEqual(still["frame_s"], 6.04)
            self.assertEqual(struct.unpack(">II", crop.read_bytes()[16:24]), (320, 180))

            candidate = work / "candidate.mp4"
            subprocess.run([
                "ffmpeg", "-nostdin", "-v", "error", "-t", "4", "-i", str(clip), "-f", "lavfi", "-i",
                "testsrc2=size=640x360:rate=25:duration=4",
                "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0", "-an",
                "-c:v", "libx264", "-threads", "2", str(candidate),
            ], check=True)
            candidate_index = work / "candidate-index"
            run_script("video.py", "index", candidate, "--no-transcript", "--no-ocr", "--out", candidate_index)

            candidate_data = candidate_index / "index.json"
            candidate_metadata = json.loads(candidate_data.read_text())
            untrusted_title = "</script><script>example()</script>"
            candidate_metadata["source"]["untrusted_source_text"] = {"title": untrusted_title}
            candidate_data.write_text(json.dumps(candidate_metadata))

            player = work / "exports" / "player.html"
            run_script("video.py", "view", index, "--out", player)
            report = work / "exports" / "compare.html"
            metrics = run_script("video.py", "compare", index, candidate_index, "--out", report)["metrics"]
            rows = {row["label"]: row for row in metrics}
            self.assertEqual(rows["Hard-cut calls"]["values"], ["0", "1"])
            self.assertEqual(rows["Duration (s)"]["delta"], "-4")
            self.assertEqual(rows["Integrated loudness (LUFS)"]["values"][1], "Unavailable")
            self.assertLess(float(rows["Integrated loudness (LUFS)"]["values"][0]), 0)
            for html, video_count in ((player, 1), (report, 2)):
                content = html.read_text()
                data = json.loads(content.split('id="report-data">', 1)[1].split("</script>", 1)[0])
                self.assertEqual(len(data["videos"]), video_count)
                self.assertEqual(data["videos"][0]["media"], "../clip.mp4")
                self.assertIn("CALIBRATION COMPLETE", [frame.get("text") for frame in data["videos"][0]["frames"]])
                if video_count == 2:
                    self.assertNotIn(untrusted_title, content)
                    self.assertEqual(data["videos"][1]["label"], untrusted_title)
                    self.assertEqual(data["videos"][1]["events"][0]["t"], 4.0)
                    overlay_events = data["videos"][0]["events"]
                    self.assertEqual([(event["kind"], event["t"]) for event in overlay_events],
                                     [("text", 6.0), ("text", 9.04)])

            handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=work)
            with http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
                thread = threading.Thread(target=server.serve_forever)
                thread.start()
                try:
                    url = f"http://127.0.0.1:{server.server_port}/clip.mp4"
                    result = run_script("video.py", "index", url, "--no-transcript", "--no-ocr",
                                        "--sample-every", "3", "--out", work / "download")
                finally:
                    server.shutdown()
                    thread.join()
            saved = json.loads(Path(result["index"]).read_text())
            self.assertEqual(saved["source"]["type"], "url")
            self.assertEqual(result["coverage"]["speech"], "skipped")
            self.assertEqual([frame["t"] for frame in saved["frames"]], [0, 3, 6, 9])


if __name__ == "__main__":
    unittest.main()
