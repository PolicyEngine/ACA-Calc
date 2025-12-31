"""Modal deployment for ACA Calculator API."""

import modal

app = modal.App("aca-calc-api")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")
    .pip_install(
        "fastapi",
        "uvicorn",
        "pydantic",
        "cachetools",
        "anthropic",
        "numpy",
        "policyengine-us>=1.459.0",
    )
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
    from src.aca_api.api import app
    return app
