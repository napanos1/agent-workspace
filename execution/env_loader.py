"""
Environment Loader - Automatically loads .env file on import.

Import this at the top of your scripts to ensure environment variables are loaded:

    from env_loader import load_env
    load_env()

Or just import it (auto-loads on import):

    import env_loader
"""

import os
from pathlib import Path


def load_env(env_path: str = None) -> dict:
    """
    Load environment variables from .env file.

    Args:
        env_path: Path to .env file. Defaults to .env in project root.

    Returns:
        Dictionary of loaded variables.
    """
    if env_path is None:
        # Find .env relative to this file's location
        env_path = Path(__file__).parent.parent / ".env"

    env_path = Path(env_path)
    loaded = {}

    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue
            # Parse key=value
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                # Remove surrounding quotes if present
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                os.environ[key] = value
                loaded[key] = value

    return loaded


# Auto-load on import
_loaded = load_env()
