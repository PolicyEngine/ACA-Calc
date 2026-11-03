"""Modal deployment for ACA Calculator API."""

from pathlib import Path

import modal

app = modal.App("aca-calc-api")

# Persistent cache for calculation results (7-day TTL handled in application)
calculation_cache = modal.Dict.from_name("aca-calc-cache", create_if_missing=True)

# Persistent cache for AI explanations
explanation_cache = modal.Dict.from_name("aca-explain-cache", create_if_missing=True)

# Exact package versions from the live container, so a deploy changes only this
# repo's code. Read the notes in the file before changing a pin.
REQUIREMENTS = Path(__file__).parent / "modal-requirements.txt"

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")
    .pip_install_from_requirements(str(REQUIREMENTS))
    .add_local_dir("aca_calc", "/root/aca_calc", copy=True)
    .add_local_dir("src/aca_api", "/root/src/aca_api", copy=True)
    .env({"PYTHONPATH": "/root"})
)


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("anthropic-api-key")],
    timeout=300,
    memory=2048,
)
@modal.asgi_app()
def fastapi_app():
    import sys
    sys.path.insert(0, "/root")
    from src.aca_api import api
    # Inject the persistent caches into the API module
    api.set_persistent_cache(calculation_cache, explanation_cache)
    return api.app
