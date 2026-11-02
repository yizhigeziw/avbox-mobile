#!/usr/bin/env python3
"""Shared scanning helpers for the .tools gates.

Reconstructed from the口径 documented in:
  AGENTS.md (交付前必跑 / 红线)
  skill/SKILL.md §46-47
  skill/review/refactor-plan-20261024.md §3.3
  skill/review/refactor-plan-20261025.md §0/§10.2
  skill/avbox-code-review-spec.md (空安全与非空断言)

Everything here is pure stdlib so the gates run on any Python 3.8+.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Iterator, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent

APP_MAIN = REPO_ROOT / "app" / "src" / "main"
APP_JAVA = APP_MAIN / "java"
APP_PYTHON_JAVA = Path("app") / "src" / "python" / "java"
UI_DIR = APP_JAVA / "com" / "github" / "avbox" / "osc" / "ui"

VENDORED_DIRS = (
    Path("libs") / "backdrop",
    Path("quickjs"),
    Path("app") / "src" / "test",
)


class Hit:
    __slots__ = ("path", "line", "text")

    def __init__(self, path: str, line: int, text: str) -> None:
        self.path = path
        self.line = line
        self.text = text

    def as_dict(self) -> dict:
        return {"path": self.path, "line": self.line, "text": self.text}

    def render(self) -> str:
        return f"{self.path}:{self.line}: {self.text}"


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def read_text(path: Path) -> str:
    for enc in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def iter_files(
    roots: Sequence[Path],
    suffixes: Tuple[str, ...] = (".kt", ".java"),
    skip_vendored: bool = False,
) -> Iterator[Path]:
    for root in roots:
        if not root.exists():
            continue
        if root.is_file():
            if root.suffix in suffixes:
                yield root
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            current = Path(dirpath)
            if skip_vendored:
                relparts = rel(current)
                if any(relparts.startswith(v.as_posix()) for v in VENDORED_DIRS):
                    dirnames[:] = []
                    continue
            dirnames[:] = [
                d for d in dirnames if d not in {"build", ".gradle", ".git", ".idea"}
            ]
            for name in filenames:
                if name.endswith(suffixes):
                    yield current / name


def app_main_root() -> Path:
    return APP_MAIN


def strip_strings(line: str) -> str:
    """Replace the contents of string/char literals with spaces.

    Keeps the literal delimiters so pattern offsets roughly stay put.
    Handles plain "..." / '...' and triple-quoted is handled per-line best-effort.
    """
    out: List[str] = []
    i = 0
    quote = ""
    while i < len(line):
        ch = line[i]
        if quote:
            if ch == "\\" and i + 1 < len(line):
                out.extend("  ")
                i += 2
                continue
            if ch == quote:
                quote = ""
                out.append(ch)
            else:
                out.append(" ")
            i += 1
            continue
        if ch in ('"', "'"):
            quote = ch
            out.append(ch)
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def base_scan_roots() -> Iterator[Tuple[Path, bool]]:
    """Yield (path, enforced) for null-assert style scans.

    enforced=True  = 判认定域（app/src/main + Chaquopy）
    enforced=False = vendored / test（只打印）
    """
    enforced_roots = [APP_JAVA]
    py = REPO_ROOT / APP_PYTHON_JAVA
    if py.exists():
        enforced_roots.append(py)
    for path in iter_files(enforced_roots, skip_vendored=False):
        yield path, True

    for vendored in VENDORED_DIRS:
        root = REPO_ROOT / vendored
        if root.exists():
            for path in iter_files([root]):
                yield path, False


def main_sources(skip_vendored: bool = True) -> List[Path]:
    roots = [APP_JAVA]
    py = REPO_ROOT / APP_PYTHON_JAVA
    if py.exists():
        roots.append(py)
    return sorted(set(iter_files(roots, skip_vendored=skip_vendored)))


def ui_sources() -> List[Path]:
    return sorted(iter_files([UI_DIR], skip_vendored=True))


def strip_line_comment(line: str) -> str:
    """Remove a trailing // comment, respecting simple string literals."""
    out: List[str] = []
    in_s = False
    in_d = False
    i = 0
    while i < len(line):
        ch = line[i]
        prev = line[i - 1] if i else ""
        if ch == '"' and not in_s and prev != "\\":
            in_d = not in_d
        elif ch == "'" and not in_d and prev != "\\":
            in_s = not in_s
        if not in_s and not in_d and ch == "/" and i + 1 < len(line) and line[i + 1] == "/":
            break
        out.append(ch)
        i += 1
    return "".join(out)


def is_comment_only(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*")


def load_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return dict(default)
    try:
        return json.loads(read_text(path))
    except json.JSONDecodeError:
        return dict(default)


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def report(title: str, hits: Sequence[Hit], detail: bool, extra: Optional[List[str]] = None) -> None:
    print(f"== {title} ==")
    if extra:
        for line in extra:
            print(line)
    if detail:
        for hit in hits:
            print("  " + hit.render())
    else:
        for hit in hits[:40]:
            print("  " + hit.render())
        if len(hits) > 40:
            print(f"  ... {len(hits) - 40} more (use --detail)")


def banner(name: str, status: str, summary: str) -> None:
    print(f"[{status}] {name}: {summary}")


def baseline_guard(
    name: str,
    counts: dict,
    baseline_path: Path,
    update: bool,
    accept_new: bool,
    primary: str = "hits",
) -> bool:
    """Compare current counts against a down-only baseline.

    `primary` 指定用于判总量的计数字段（文件数是伴随指标，不参与总量比较）。
    Returns True when the run should be considered PASS.
    """
    baseline = load_json(baseline_path, {})
    total_now = int(counts.get(primary, 0))
    total_base = int(baseline.get(primary, 0)) if baseline else None

    if update:
        if total_base is None:
            if not accept_new:
                print(f"[FAIL] {name}: 基线不存在，首冻需 --update --accept-new")
                return False
            write_json(baseline_path, counts)
            banner(name, "OK", f"首冻基线 total={total_now}")
            return True
        if total_now > total_base:
            print(
                f"[FAIL] {name}: 拒绝上调基线 (baseline={total_base} current={total_now})；"
                "基线只允许下调"
            )
            return False
        write_json(baseline_path, counts)
        banner(name, "OK", f"基线下调 total {total_base} -> {total_now}")
        return True

    if total_base is None:
        banner(name, "WARN", f"无基线文件，仅报告 total={total_now}（运行 --update --accept-new 冻结）")
        return True

    if total_now > total_base:
        print(f"[FAIL] {name}: 超过基线 (baseline={total_base} current={total_now})")
        for key, value in sorted(counts.items()):
            if int(value) > int(baseline.get(key, 0)):
                print(f"    +{key}: {baseline.get(key, 0)} -> {value}")
        return False

    banner(name, "PASS", f"total={total_now} baseline={total_base}")
    return True


def finish(ok: bool) -> None:
    sys.exit(0 if ok else 1)
