"""Modal deployment for ACA Calculator API."""

import os
from pathlib import Path

import modal

# The live app is aca-calc-api. A preview deploy sets ACA_API_APP_NAME, say
# aca-calc-api-preview, to run a branch's backend beside it with caches of its
# own; the image carries the name, so its containers open the same caches.
APP_NAME = os.environ.get("ACA_API_APP_NAME", "aca-calc-api")
CACHE_SUFFIX = APP_NAME.removeprefix("aca-calc-api")

app = modal.App(APP_NAME)

# Persistent cache for calculation results (7-day TTL handled in application)
calculation_cache = modal.Dict.from_name(f"aca-calc-cache{CACHE_SUFFIX}", create_if_missing=True)

# Persistent cache for AI explanations
explanation_cache = modal.Dict.from_name(
    f"aca-explain-cache{CACHE_SUFFIX}", create_if_missing=True
)

# Exact package versions from the live container, so a deploy changes only this
# repo's code. Read the notes in the file before changing a pin.
REQUIREMENTS = Path(__file__).parent / "modal-requirements.txt"

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")
    .pip_install_from_requirements(str(REQUIREMENTS))
    .add_local_dir("aca_calc", "/root/aca_calc", copy=True)
    .add_local_dir("src/aca_api", "/root/src/aca_api", copy=True)
    # The commit a CI deploy came from. The API reports it, so the smoke test
    # can tell this deploy's containers from the previous version's.
    .env(
        {
            "PYTHONPATH": "/root",
            "ACA_API_COMMIT": os.environ.get("ACA_API_COMMIT", ""),
            "ACA_API_APP_NAME": APP_NAME,
        }
    )
)


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("anthropic-api-key")],
    timeout=300,
    # policyengine-us 2.x needs about 0.9 GB to load and 2.4-2.9 GB once a
    # request has run its scenarios' reforms.
    memory=4096,
)
@modal.asgi_app()
def fastapi_app():
    import sys
    sys.path.insert(0, "/root")
    from src.aca_api import api
    # Inject the persistent caches into the API module
    api.set_persistent_cache(calculation_cache, explanation_cache)
    return api.app
