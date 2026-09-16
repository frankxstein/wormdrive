from __future__ import annotations

from pathlib import Path

from ..vision import VisionFeatures
from .base import BrainState


class ConnectomeBackend:
    """Placeholder for a real C. elegans connectome-driven backend.

    Intended to eventually load real connectivity data (e.g. from the
    OpenWorm project or WormAtlas) and run an actual weighted-graph
    simulation instead of the hand-designed leaky model in mock.py.

    This class deliberately does nothing yet: it does not load a graph and
    does not fabricate a simulated result. It exists as a documented
    extension point, not a working backend.
    """

    def __init__(self, dataset_path: str | None = None):
        self.dataset_path = dataset_path

    def reset(self) -> None:
        pass

    def step(self, features: VisionFeatures, imu_yaw_rate: float, dt: float) -> BrainState:
        if not self.dataset_path or not Path(self.dataset_path).exists():
            raise NotImplementedError(
                "ConnectomeBackend: no connectome dataset configured or found "
                f"at {self.dataset_path!r}. Not implemented yet."
            )
        raise NotImplementedError(
            "ConnectomeBackend: dataset found but graph loading and "
            "simulation are not implemented yet."
        )
