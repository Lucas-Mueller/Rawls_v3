from config import ExperimentConfiguration
from utils.seed_manager import SeedManager


def load_default_config():
    return ExperimentConfiguration.from_yaml("config/default_config.yaml")


def test_generate_seed_is_deterministic(tmp_path):
    config = load_default_config()
    seed_first = SeedManager.generate_seed_from_config(config)

    # Reload config to ensure we recompute from scratch
    config_again = load_default_config()
    seed_second = SeedManager.generate_seed_from_config(config_again)

    assert seed_first == seed_second


def test_seed_manager_initialization_sets_current_seed():
    config = load_default_config()
    manager = SeedManager()
    effective_seed = manager.initialize_from_config(config)

    assert manager.current_seed == effective_seed
    assert isinstance(effective_seed, int)
