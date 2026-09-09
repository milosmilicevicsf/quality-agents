"""Build bounded, reviewable context from an exact, clean Git revision."""

import fnmatch
from pathlib import Path

from .utils import QAError, git, inside, load, redact, revision, secret_path

DEFAULT = {
    "include": ["*.py", "*.ts", "*.tsx", "*.js", "*.cs", "*.java", "*.go", "*.rb",
                "*.rs", "*.md", "*.json", "*.toml", "*.yaml", "*.yml", "*.xml"],
    "exclude": ["*lock*", "vendor/*", "node_modules/*", "dist/*", "build/*", "qa-runs/*"],
    "test_paths": ["tests/*", "test/*", "__tests__/*", "*.spec.ts", "*.test.ts", "*Tests/*.cs"],
    "focus": [],
    "max_files": 60,
    "max_file_chars": 16000,
    "max_total_chars": 160000,
    "project_context": "Describe domain, critical journeys, integrations and test commands here.",
}


def config(path=None):
    result = dict(DEFAULT)
    if path:
        custom = load(path)
        if not isinstance(custom, dict) or set(custom) - set(DEFAULT):
            raise QAError("Unknown configuration fields")
        result.update(custom)
    for key in ("include", "exclude", "test_paths", "focus"):
        if not isinstance(result[key], list) or not all(isinstance(x, str) and x for x in result[key]):
            raise QAError(f"{key} must be a list of non-empty patterns")
    for key in ("max_files", "max_file_chars", "max_total_chars"):
        if type(result[key]) is not int or not 1 <= result[key] <= 1_000_000:
            raise QAError(f"Invalid limit: {key}")
    if not isinstance(result["project_context"], str):
        raise QAError("project_context must be a string")
    return result


def matches(name, patterns):
    return any(fnmatch.fnmatchcase(name, p) for p in patterns)


def collect(repo, story_path, settings, evidence=(), base=None):
    repo = Path(repo).resolve()
    head = revision(repo)
    entries = git(repo, "ls-tree", "-r", "-z", "--full-tree", head, binary=True)
    files = []
    ignored = []
    for raw in entries.split(b"\0"):
        if not raw:
            continue
        meta, name = raw.split(b"\t", 1)
        name = name.decode("utf-8")
        mode, kind, _ = meta.decode().split()
        if kind != "blob" or mode not in ("100644", "100755"):
            ignored.append({"path": name, "reason": "symlink/submodule unsupported"})
        elif secret_path(name) or matches(name, settings["exclude"]):
            ignored.append({"path": "[excluded path]", "reason": "excluded by policy"})
        elif not matches(name, settings["include"]):
            ignored.append({"path": name, "reason": "outside include patterns"})
        else:
            files.append(name)
    changed = []
    base_sha = None
    if base:
        if base.startswith("-"):
            raise QAError("Invalid base revision")
        base_sha = git(repo, "rev-parse", "--verify", base + "^{commit}")
        changed = git(repo, "diff", "--name-only", "-z", base_sha, head, binary=True).decode().split("\0")
    files.sort(key=lambda n: (not matches(n, settings["focus"]), n not in changed,
                              not matches(n, settings["test_paths"]), n))
    selected = []
    total = 0
    for name in files:
        path = inside(repo, name)
        if path.stat().st_size > settings["max_file_chars"] * 4:
            ignored.append({"path": name, "reason": "file size limit"})
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeError:
            ignored.append({"path": name, "reason": "not UTF-8"})
            continue
        if "\x00" in content or len(content) > settings["max_file_chars"]:
            ignored.append({"path": name, "reason": "binary/file size limit"})
        elif len(selected) >= settings["max_files"] or total + len(content) > settings["max_total_chars"]:
            ignored.append({"path": name, "reason": "context budget"})
        else:
            clean = redact(content)
            if clean != content:
                ignored.append({"path": name, "reason": "sensitive content; whole file excluded"})
                continue
            total += len(content)
            selected.append({"path": name, "content": content, "lines": len(content.splitlines())})
    story = Path(story_path).read_text(encoding="utf-8")
    if len(story) > 30000:
        raise QAError("Story exceeds 30,000 characters")
    attachments = []
    for index, evidence_path in enumerate(evidence):
        text = Path(evidence_path).read_text(encoding="utf-8")
        if len(text) > 60000 or sum(len(x["content"]) for x in attachments) + len(text) > 120000:
            raise QAError("Evidence too large; provide a focused, redacted text excerpt")
        text = redact(text)
        attachments.append({"path": f"evidence/{index + 1}.txt", "content": text,
                            "lines": len(text.splitlines())})
    if not selected:
        raise QAError("No source context selected; adjust include/focus settings")
    diff = ""
    if base_sha:
        paths = [f["path"] for f in selected]
        diff = redact(git(repo, "diff", "--no-ext-diff", "--no-textconv", "--unified=3",
                          base_sha, head, "--", *paths))
    diff_truncated = len(diff) > 40000
    hints = {"pytest": "pytest", "Playwright": "playwright", "Jest": "jest",
             "Vitest": "vitest", "NUnit": "NUnit", "xUnit": "xunit",
             "JUnit": "junit", "unittest": "unittest"}
    joined = "\n".join(f["content"] for f in selected)
    frameworks = [name for name, token in hints.items() if token.lower() in joined.lower()]
    if revision(repo) != head:
        raise QAError("Repository changed while collecting context; retry on a stable revision")
    return {"repo": str(repo), "head": head, "base": base_sha,
            "selected_diff": diff[:40000], "diff_truncated": diff_truncated,
            "framework_hints": frameworks,
            "changed_paths": [p for p in changed if p and not secret_path(p)],
            "settings": {**settings, "project_context": redact(settings["project_context"])},
            "story": redact(story), "files": selected, "evidence": attachments,
            "omitted": ignored, "scope": "Selected files only; not exhaustive coverage analysis"}
