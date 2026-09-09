"""Publish this source to the owner's private GitHub repo using their local gh login."""

import argparse
import shutil
import subprocess
from pathlib import Path

OWNER = "milosmilicevicsf"
NAME = "quality-agents"
ROOT = Path(__file__).resolve().parents[1]


def run(*args, capture=False):
    return subprocess.run(args, cwd=ROOT, check=True, text=True,
                          stdout=subprocess.PIPE if capture else None)


def main():
    p = argparse.ArgumentParser(description="Create/push the owner's private repo. Never force-pushes.")
    p.add_argument("--create", action="store_true", help="Create a new private GitHub repository")
    args = p.parse_args()
    if not shutil.which("gh") or not shutil.which("git"):
        raise SystemExit("Install Git and GitHub CLI, then run gh auth login locally first.")
    login = run("gh", "api", "user", "--jq", ".login", capture=True).stdout.strip()
    if login != OWNER:
        raise SystemExit(f"Authenticated account must be {OWNER}; no changes made.")
    if not (ROOT / ".git").exists():
        run("git", "init", "-b", "main")
        run("git", "add", ".")
        run("git", "-c", "user.name=" + OWNER, "-c", "user.email=" + OWNER + "@users.noreply.github.com",
            "-c", "commit.gpgsign=false", "commit", "-m", "Initial portable quality agents toolkit")
    if run("git", "status", "--porcelain", capture=True).stdout.strip():
        raise SystemExit("Commit local changes before publishing.")
    if args.create:
        run("gh", "repo", "create", OWNER + "/" + NAME, "--private", "--description",
            "Reusable risk mapping, test generation and failure analysis with human review")
    visibility = run("gh", "repo", "view", OWNER + "/" + NAME, "--json", "isPrivate", "--jq", ".isPrivate", capture=True).stdout.strip()
    if visibility != "true":
        raise SystemExit("Expected a private repository; no code pushed.")
    url = "https://github.com/" + OWNER + "/" + NAME + ".git"
    # Invoke gh as a credential helper only for this command; don't change global config.
    run("git", "-c", "credential.helper=", "-c", "credential.helper=!gh auth git-credential",
        "push", url, "HEAD:main")
    print("Published to https://github.com/" + OWNER + "/" + NAME)


if __name__ == "__main__":
    main()
