import os
import sys
import unittest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ascii_paint_to_image.controlnet import (
    ControlNetExperiment,
    default_controlnet_experiments,
)


class ControlNetTest(unittest.TestCase):
    def test_default_controlnet_experiments_has_five_seeded_prompt_variants(self) -> None:
        experiments = default_controlnet_experiments()

        self.assertEqual(len(experiments), 5)
        self.assertEqual([experiment.name for experiment in experiments], [
            "photo-object",
            "product-render",
            "watercolor",
            "iconic-poster",
            "abstract-material",
        ])
        self.assertEqual(len({experiment.seed for experiment in experiments}), 5)
        self.assertTrue(all(experiment.prompt for experiment in experiments))

    def test_experiment_slug_is_filesystem_safe(self) -> None:
        experiment = ControlNetExperiment(
            name="Photo Object!",
            prompt="a prompt",
            negative_prompt="",
            seed=1,
            steps=8,
            guidance_scale=7.0,
            controlnet_conditioning_scale=0.8,
        )

        self.assertEqual(experiment.slug(), "photo-object")


if __name__ == "__main__":
    unittest.main()
