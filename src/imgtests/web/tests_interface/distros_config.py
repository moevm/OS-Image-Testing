import json
from pathlib import Path

# Default distros list
DEFAULT_DISTRIBUTIONS = [
    {
        "id": "yocto",
        "name": "yocto",
        "display_name": "Yocto Project",
        "description": "Run tests for Yocto platform",
        "url_name": "yocto",
    },
    {
        "id": "opensuse",
        "name": "opensuse",
        "display_name": "OpenSUSE",
        "description": "Run tests for OpenSUSE platform",
        "url_name": "opensuse",
    },
]

CONFIG_FILE = Path(__file__).parent / "user_distros.json"


def get_distributions() -> list[dict]:
    if CONFIG_FILE.exists():
        try:
            with Path.open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("distributions", DEFAULT_DISTRIBUTIONS.copy())
        except OSError:
            return DEFAULT_DISTRIBUTIONS.copy()
    return DEFAULT_DISTRIBUTIONS.copy()


def save_distributions(distributions: list[dict]) -> bool:
    try:
        with Path.open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"distributions": distributions}, f, indent=2, ensure_ascii=False)
    except OSError:
        return False
    else:
        return True


def get_distribution_by_id(distro_id: str) -> dict | None:
    for distro in get_distributions():
        if distro.get("id") == distro_id:
            return distro
    return None


def add_distribution(name: str, display_name: str, description: str = "") -> dict | None:
    distributions = get_distributions()

    distro_id = name.lower().replace(" ", "_")
    if any(d["id"] == distro_id for d in distributions):
        return None

    new_distro = {
        "id": distro_id,
        "name": name,
        "display_name": display_name,
        "description": description or f"Run tests for {display_name} platform",
        "url_name": distro_id,
    }

    distributions.append(new_distro)

    if save_distributions(distributions):
        return new_distro
    return None


def remove_distribution(distro_id: str) -> bool:
    distributions = get_distributions()
    original_length = len(distributions)
    distributions = [d for d in distributions if d["id"] != distro_id]

    if len(distributions) == original_length:
        return False

    return save_distributions(distributions)


def reset_to_default() -> bool:
    return save_distributions(DEFAULT_DISTRIBUTIONS.copy())
