from pathlib import Path

import pytest

SAMPLE = Path(__file__).resolve().parents[1] / "sample_data" / "activity_24651972498.gpx"


@pytest.fixture
def sample_path():
    return SAMPLE
