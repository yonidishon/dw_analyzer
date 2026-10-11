from pathlib import Path

import pytest

SAMPLE = Path(__file__).resolve().parents[1] / "sample_data" / "activity_24651972498.gpx"


@pytest.fixture
def sample_path():
    if not SAMPLE.exists():  # sample_data/ is kept out of the public repo
        pytest.skip(f"sample GPX not present: {SAMPLE}")
    return SAMPLE
