"""Run the reproducible local research pipeline."""
from prepare_inputs import run as prepare
from update_analysis import main as analyze
from build_site import build

if __name__ == "__main__":
    prepare()
    analyze()
    build()