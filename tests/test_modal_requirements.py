"""Check that the Modal image installs exact versions, so every deploy is repeatable."""

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
REQUIREMENTS = ROOT / "modal-requirements.txt"
COMMIT_ARCHIVE = re.compile(
    r"^https://github\.com/[\w.-]+/[\w.-]+/archive/[0-9a-f]{40}\.tar\.gz$"
)


def requirements():
    return [
        line.strip()
        for line in REQUIREMENTS.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def package_name(requirement):
    name = re.split(r"==| @ ", requirement)[0]
    return re.sub(r"[-_.]+", "-", name).lower()


def test_every_requirement_is_an_exact_version_or_commit():
    for requirement in requirements():
        if " @ " in requirement:
            # A commit archive, not a branch or tag that can move.
            url = requirement.split(" @ ", 1)[1]
            assert COMMIT_ARCHIVE.match(url), requirement
        else:
            assert re.fullmatch(r"[A-Za-z0-9_.-]+==[A-Za-z0-9_.+!-]+", requirement), (
                requirement
            )


def test_no_package_is_listed_twice():
    names = [package_name(requirement) for requirement in requirements()]
    assert len(names) == len(set(names))


def test_image_installs_from_the_pinned_file():
    source = (ROOT / "modal_app.py").read_text()
    assert '"modal-requirements.txt"' in source
    assert ".pip_install_from_requirements(str(REQUIREMENTS))" in source
    assert ".pip_install(" not in source
