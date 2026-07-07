import unittest

from services.character_system_service import (
    age_progression_delta,
    alignment_label,
    calculate_finisher_protection,
    calculate_gimmick_effectiveness,
    calculate_turn_impact,
    chemistry_modifier,
)


class CharacterSystemServiceTests(unittest.TestCase):
    def test_alignment_labels(self):
        self.assertEqual(alignment_label(0), "Heel")
        self.assertEqual(alignment_label(50), "Tweener")
        self.assertEqual(alignment_label(100), "Face")

    def test_turn_impact_formula_and_overness(self):
        result = calculate_turn_impact(timing_score=70, build_score=8, surprise_factor=90)
        self.assertEqual(result["impact_score"], 80)
        self.assertEqual(result["overness_change"], 20)

    def test_gimmick_effectiveness_scores_matching_archetype_highly(self):
        wrestler = {
            "brawling": 90,
            "mic": 60,
            "psychology": 70,
            "popularity": 80,
        }
        score = calculate_gimmick_effectiveness(wrestler, "monster_heel")
        self.assertGreaterEqual(score, 75)

    def test_finisher_protection(self):
        self.assertEqual(calculate_finisher_protection(9, 1), 90)
        self.assertEqual(calculate_finisher_protection(0, 0), 100)

    def test_style_chemistry_matrix(self):
        self.assertEqual(chemistry_modifier("technical", "brawler"), 5)
        self.assertEqual(chemistry_modifier("hybrid", "high_flyer"), 8)

    def test_age_progression_high_flyer_declines_speed_faster(self):
        deltas = age_progression_delta(39, "high_flyer")
        self.assertLess(deltas["speed"], deltas["technical"])
        self.assertGreaterEqual(deltas["psychology"], 1)


if __name__ == "__main__":
    unittest.main()
