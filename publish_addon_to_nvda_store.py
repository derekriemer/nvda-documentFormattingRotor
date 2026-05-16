#!/usr/bin/env python3
import argparse
import json
import pathlib
import subprocess
import sys
import tempfile


TARGET_REPO = "nvaccess/addon-datastore"


def run_gh(*args: str) -> str:
    try:
        return subprocess.check_output(
            ["gh", *args],
            text=True,
            encoding="utf-8",
            stderr=subprocess.PIPE,
        ).strip()
    except FileNotFoundError:
        sys.exit("gh CLI not found")
    except subprocess.CalledProcessError as e:
        sys.exit(e.stderr.strip() or f"gh failed: {' '.join(args)}")


def load_build_vars(path: pathlib.Path) -> dict:
    if not path.exists():
        sys.exit(f"Missing {path}")

    class AddonInfo:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    def _(s):
        return s

    namespace = {
        "AddonInfo": AddonInfo,
        "_": _,
        "BrailleTables": dict,
        "SymbolDictionaries": dict,
    }

    code = path.read_text(encoding="utf-8")
    exec(code, namespace)

    info = namespace.get("addon_info")
    if info is None:
        sys.exit("buildVars.py does not define addon_info")

    if isinstance(info, dict):
        return info
    return vars(info)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("release", help="GitHub release tag/name to submit")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    repo = run_gh("repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner")
    repo_name = run_gh("repo", "view", "--json", "name", "-q", ".name")

    release_json = run_gh(
        "release",
        "view",
        args.release,
        "--repo",
        repo,
        "--json",
        "assets",
    )

    assets = json.loads(release_json)["assets"]
    addon_assets = [
        asset for asset in assets
        if asset["name"].endswith(".nvda-addon")
    ]

    if not addon_assets:
        sys.exit(f"No .nvda-addon asset found on release {args.release}")

    if len(addon_assets) > 1:
        names = ", ".join(asset["name"] for asset in addon_assets)
        sys.exit(f"More than one .nvda-addon asset found: {names}")

    download_url = addon_assets[0]["url"]

    info = load_build_vars(pathlib.Path("buildVars.py"))

    source_url = info.get("addon_sourceURL") or f"https://github.com/{repo}"
    publisher = info.get("addon_author") or ""
    channel = info.get("addon_updateChannel") or "stable"
    license_name = info.get("addon_license") or ""
    license_url = info.get("addon_licenseURL") or ""

    body = f"""### Download URL

{download_url}

### Source URL

{source_url}

### Publisher

{publisher}

### Channel

{channel}

### License Name

{license_name}

### License URL

{license_url}
"""

    title = f"[Submit add-on]: {repo_name} {args.release}"

    if args.dry_run:
        print(f"Repo: {TARGET_REPO}")
        print(f"Title: {title}")
        print()
        print(body)
        return

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".md") as f:
        f.write(body)
        body_file = f.name

    run_gh(
        "issue",
        "create",
        "--repo",
        TARGET_REPO,
        "--title",
        title,
        "--label",
        "autoSubmissionFromIssue",
        "--body-file",
        body_file,
    )


if __name__ == "__main__":
    main()
