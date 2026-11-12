"""Shot confirmation on small synthetic frame sequences. Runs in seconds with numpy only.

    python3 -m unittest discover -s tests
"""
import runpy
import unittest
from pathlib import Path

import numpy as np

SCRIPT = (Path(__file__).resolve().parent.parent / "plugins/reverse-engineer-any-video/skills"
          / "reverse-engineer-any-video/scripts/evidence.py")
EV = runpy.run_path(str(SCRIPT))
FPS = 25
H, W = 54, 96


def texture(seed: int, height: int = H, width: int = W) -> np.ndarray:
    """A smooth random picture with structure at several scales."""
    rng = np.random.default_rng(seed)
    picture = np.zeros((height, width))
    for cells in (3, 6, 12):
        coarse = rng.random((cells, cells * 2))
        picture += np.kron(coarse, np.ones((-(-height // cells), -(-width // (cells * 2)))))[:height, :width]
    return (picture / picture.max() * 200 + 20).astype(np.float32)


def clip(*pictures: np.ndarray) -> tuple[np.ndarray, list[float]]:
    frames = np.stack(pictures).astype(np.float32)
    return frames, [i / FPS for i in range(len(frames))]


def shots(result: tuple[list[dict], list[dict]]) -> list[dict]:
    return [event for event in result[0] if event["kind"] == "shot"]


class ShotConfirmation(unittest.TestCase):
    def test_hard_cut_is_found_at_its_first_frame(self):
        a, b = texture(1), texture(2)
        frames, times = clip(*[a] * 50, *[b] * 50)
        found = shots(EV["confirm_shots"](frames, times, [], []))
        self.assertEqual([(e["t"], e["cue"]) for e in found], [(2.0, "cut")])

    def test_sampled_candidate_next_to_cut_merges_into_it(self):
        a, b = texture(1), texture(2)
        frames, times = clip(*[a] * 50, *[b] * 50)
        sampled = [{"t": 2.1, "kind": "shot", "changed": 0.9}]
        found = shots(EV["confirm_shots"](frames, times, sampled, []))
        self.assertEqual([e["t"] for e in found], [2.0])

    def test_white_flash_returning_to_the_same_view_is_not_a_cut(self):
        a = texture(3)
        white = np.full((H, W), 255.0, np.float32)
        frames, times = clip(*[a] * 50, *[white] * 4, *[a] * 46)
        sampled = [{"t": 2.0, "kind": "shot", "changed": 0.9}, {"t": 2.2, "kind": "shot", "changed": 0.9}]
        events, review = EV["confirm_shots"](frames, times, sampled, [])
        self.assertEqual(shots((events, review)), [])
        self.assertTrue(review)

    def test_exposure_change_on_one_view_is_not_a_cut(self):
        a = texture(4)
        frames, times = clip(*[a] * 50, *[np.clip(a * 0.4 + 120, 0, 255)] * 50)
        sampled = [{"t": 2.0, "kind": "shot", "changed": 0.9}]
        self.assertEqual(shots(EV["confirm_shots"](frames, times, sampled, [])), [])

    def test_pan_is_not_a_cut_but_the_cut_inside_it_is(self):
        wide_a, wide_b = texture(5, H, W + 100), texture(6, H, W + 100)
        pan_a = [wide_a[:, x:x + W] for x in range(0, 50)]
        pan_b = [wide_b[:, x:x + W] for x in range(0, 50)]
        frames, times = clip(*pan_a, *pan_b)
        found = shots(EV["confirm_shots"](frames, times, [], []))
        self.assertEqual([e["t"] for e in found], [2.0])

    def test_dissolve_candidate_is_a_gradual_shot(self):
        a, b = texture(7), texture(8)
        blend = [a + (b - a) * k / 12 for k in range(1, 12)]
        frames, times = clip(*[a] * 50, *blend, *[b] * 50)
        sampled = [{"t": 2.2, "kind": "shot", "changed": 0.3}]
        found = shots(EV["confirm_shots"](frames, times, sampled, []))
        self.assertEqual([e["cue"] for e in found], ["gradual"])

    def test_uncertain_dissolve_is_promoted(self):
        a, b = texture(7), texture(8)
        blend = [a + (b - a) * k / 12 for k in range(1, 12)]
        frames, times = clip(*[a] * 50, *blend, *[b] * 50)
        found = shots(EV["confirm_shots"](frames, times, [], [{"t": 2.2, "changed": 0.3}]))
        self.assertEqual([e["t"] for e in found], [2.2])

    def test_candidate_inside_one_steady_view_goes_to_review(self):
        a = texture(9)
        moving = []
        for i in range(100):
            frame = a.copy()
            frame[20:30, (i % 80):(i % 80) + 10] = 255  # a small object crossing
            moving.append(frame)
        frames, times = clip(*moving)
        events, review = EV["confirm_shots"](frames, times, [{"t": 2.0, "kind": "shot", "changed": 0.2}], [])
        self.assertEqual(shots((events, review)), [])
        self.assertEqual([r["t"] for r in review], [2.0])

    def test_candidate_at_the_end_cannot_be_confirmed(self):
        a, b = texture(1), texture(2)
        blend = [a + (b - a) * k / 6 for k in range(1, 6)]
        frames, times = clip(*[a] * 50, *blend, *[b] * 3)
        events, review = EV["confirm_shots"](frames, times, [{"t": 2.1, "kind": "shot", "changed": 0.3}], [])
        self.assertEqual(shots((events, review)), [])
        self.assertIn("ends", review[0]["why"])

    def test_non_shot_events_pass_through(self):
        a = texture(1)
        frames, times = clip(*[a] * 60)
        text = {"t": 1.0, "kind": "text", "changed": 0.05}
        events, review = EV["confirm_shots"](frames, times, [text], [])
        self.assertEqual(events, [text])
        self.assertEqual(review, [])


class Measures(unittest.TestCase):
    def test_correlation_ignores_brightness_and_contrast(self):
        a = texture(1)
        self.assertAlmostEqual(EV["correlation"](a, a * 0.5 + 60), 1.0, places=5)
        self.assertLess(EV["correlation"](a, texture(2)), 0.5)

    def test_flat_pictures_match_only_each_other(self):
        flat = np.full((H, W), 10.0, np.float32)
        self.assertEqual(EV["correlation"](flat, flat + 100), 1.0)
        self.assertEqual(EV["correlation"](flat, texture(1)), 0.0)

    def test_repeated_large_changes_are_not_isolated_spikes(self):
        a, b = texture(1), texture(2)
        frames, times = clip(*[a, b] * 30)
        steps = EV["structure_changes"](frames)
        self.assertEqual(EV["isolated_spikes"](steps, times, 0.15, 2.0), [])


if __name__ == "__main__":
    unittest.main()
