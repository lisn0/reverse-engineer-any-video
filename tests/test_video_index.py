"""Regression tests for timestamped queries against saved video indexes."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SCRIPTS = (Path(__file__).resolve().parents[1] / "plugins/reverse-engineer-any-video/skills"
           / "reverse-engineer-any-video/scripts")
sys.path.insert(0, str(SCRIPTS))
import video
import video_report


class VideoSearch(unittest.TestCase):
    def test_embedded_caption_language_alias_and_cue_timing(self):
        probe = {"streams": [
            {"index": 0, "codec_type": "audio", "tags": {"language": "eng"}},
            {"index": 2, "codec_type": "subtitle", "codec_name": "subrip",
             "tags": {"language": "eng"}, "disposition": {"default": 1}},
        ]}
        srt = """1
00:00:12,400 --> 00:00:15,800
Both poles and Adélie penguins
"""
        completed = SimpleNamespace(returncode=0, stdout=srt)
        with patch.object(video.evidence, "run", return_value=json.dumps(probe)):
            with patch.object(video.subprocess, "run", return_value=completed) as run:
                cues, language = video.embedded_captions(Path("video.mp4"), "en", 20, 2)
        self.assertEqual(run.call_args.args[0][7], "0:2")
        self.assertEqual(language, "eng")
        self.assertEqual(cues, [{"text": "Both poles and Adélie penguins", "start": 10.4, "end": 13.8}])

    def test_forced_caption_tracks_fall_back_to_transcription(self):
        probe = {"streams": [
            {"index": 0, "codec_type": "audio", "tags": {"language": "eng"}},
            {"index": 2, "codec_type": "subtitle", "codec_name": "mov_text",
             "tags": {"language": "eng"}, "disposition": {"forced": 1}},
        ]}
        with patch.object(video.evidence, "run", return_value=json.dumps(probe)):
            with patch.object(video.subprocess, "run") as run:
                self.assertEqual(video.embedded_captions(Path("video.mp4"), None, 20, 0), ([], None))
        run.assert_not_called()

    def test_caption_search_preserves_cue_timing_and_matches_diacritics(self):
        captions = [{"text": "Adélie penguins at both poles", "start": 12.4, "end": 15.8}]
        hit = video.caption_hits(captions, video.tokens("adelie penguins"))[0]
        self.assertEqual((hit["start"], hit["end"]), (12.4, 15.8))
        self.assertEqual(hit["source"], "embedded captions")
        self.assertEqual(len(video.caption_hits(captions, video.tokens("both poles"))), 1)

    def test_speech_phrase_uses_word_times_and_does_not_cross_a_long_pause(self):
        words = [
            {"word": "Copper,", "start": 1.2, "end": 1.6},
            {"word": "valve.", "start": 1.7, "end": 2.0},
            {"word": "copper", "start": 3.0, "end": 3.5},
            {"word": "valve", "start": 6.0, "end": 6.4},
        ]
        hits = video.speech_hits(words, video.tokens("COPPER valve"))
        self.assertEqual([(hit["start"], hit["end"]) for hit in hits], [(1.2, 2.0)])

    def test_screen_phrase_merges_matching_samples_and_splits_after_a_miss(self):
        frames = [
            {"t": t, "text": message, "image": f"{t}.jpg"}
            for t, message in enumerate(("Sensor 12\nCalibration complete", "Sensor 13\nCalibration complete",
                                         "Check connection", "Calibration complete"))
        ]
        hits = video.screen_hits(frames, video.tokens("Calibration complete"))
        self.assertEqual([(hit["first_seen"], hit["last_seen"], hit["image"]) for hit in hits],
                         [(0, 1, "0.jpg"), (3, 3, "3.jpg")])

    def test_substring_search_in_unspaced_japanese(self):
        frame = {"t": 0.5, "text": "現在の温度です", "image": "temp.jpg"}
        self.assertEqual(len(video.screen_hits([frame], video.tokens("温度"))), 1)
        self.assertNotEqual(video.tokens("ば"), video.tokens("は"))

    def test_relative_media_paths_escape_url_syntax(self):
        directory = Path("/review")
        self.assertEqual(video_report.relative_url(Path("/media/My clip #1?.mp4"), directory),
                         "../media/My%20clip%20%231%3F.mp4")

    def test_unavailable_metrics_are_distinct_from_zero(self):
        self.assertEqual(video_report.metric_rows([{"Text": None}, {"Text": 0}]),
                         [{"label": "Text", "values": ["Unavailable", "0"], "delta": None}])

    def test_timestamp_and_crop_box(self):
        self.assertEqual(video.timestamp("1:02:03.4"), 3723.4)
        self.assertEqual(video.crop_box("0.25,0.25,0.5,0.5"), (0.25, 0.25, 0.5, 0.5))

    def test_search_keeps_source_and_evidence_for_each_index(self):
        with tempfile.TemporaryDirectory() as work:
            first = Path(work) / "first"
            second = Path(work) / "second"
            for folder in (first, second):
                folder.mkdir()
            (first / "index.json").write_text(json.dumps({
                "coverage": {"speech": "indexed", "screen": "skipped"},
                "words": [{"word": "ready", "start": 1.0, "end": 1.4}],
                "frames": [],
            }))
            (second / "index.json").write_text(json.dumps({
                "coverage": {"speech": "no audio", "screen": "sampled"}, "words": [],
                "frames": [{"t": 0.5, "text": "Ready", "image": "frames/000001.jpg"}],
            }))
            results = video.search([first, second], "Ready", "all")["results"]
            self.assertEqual([entry["hits"][0]["track"] for entry in results], ["said", "shown"])
            self.assertEqual(results[1]["hits"][0]["image"], str(second.resolve() / "frames/000001.jpg"))
            self.assertEqual(video.search([first], "ready", "shown")["results"][0]["hits"], [])


if __name__ == "__main__":
    unittest.main()
