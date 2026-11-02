#!/usr/bin/env python3
"""ui_layer_gate.py — Composable 不得直连下层门禁.

口径（AGENTS.md 不变量 5；SKILL.md §47；refactor-plan-20261025.md §10.2）:
  判定对象 = `ui/**` 下文件内含 `@Composable` 的文件
  禁止 import …osc.{api,base,data,sourcedata,net}.*（及其子包）
  白名单 = *ViewModel 文件、AppBootstrap 符号

基线 `ui_layer_baseline.json` 只允许下调（--update 拒绝上调）。

用法：
  python .tools/ui_layer_gate.py            # 校验
  python .tools/ui_layer_gate.py --detail   # 逐条打印
  python .tools/ui_layer_gate.py --update [--accept-new]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _gate_common import (  # noqa: E402
    Hit,
    REPO_ROOT,
    baseline_guard,
    finish,
    read_text,
    rel,
    report,
    ui_sources,
)

BASELINE = REPO_ROOT / ".tools" / "ui_layer_baseline.json"

FORBIDDEN_PKGS = ("api", "base", "data", "sourcedata", "net")
IMPORT_RE = re.compile(
    r"^\s*import\s+com\.github\.avbox\.osc\.("
    + "|".join(FORBIDDEN_PKGS)
    + r")\.([A-Za-z0-9_.]+)(?:\s+as\s+\w+)?\s*$"
)
COMPOSABLE_RE = re.compile(r"^\s*@Composable\b")

WHITELIST_SYMBOLS = {"AppBootstrap"}


def is_whitelisted_symbol(symbol: str) -> bool:
    return symbol in WHITELIST_SYMBOLS or symbol.endswith("ViewModel")


def has_composable(text: str) -> bool:
    return any(COMPOSABLE_RE.match(line) for line in text.splitlines())


def symbol_of(import_path: str) -> str:
    return import_path.replace(".*", "").rsplit(".", 1)[-1]


def whitelisted_file(path: Path) -> bool:
    return path.stem.endswith("ViewModel")


def main() -> None:
    args = sys.argv[1:]
    detail = "--detail" in args
    update = "--update" in args
    accept_new = "--accept-new" in args

    hits: list[Hit] = []
    files_hit: set[str] = set()

    for path in ui_sources():
        if whitelisted_file(path):
            continue
        text = read_text(path)
        if not has_composable(text):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            match = IMPORT_RE.match(line)
            if not match:
                continue
            if is_whitelisted_symbol(symbol_of(match.group(2))):
                continue
            hits.append(Hit(rel(path), lineno, line.strip()))
            files_hit.add(rel(path))

    report("ui_layer_gate", hits, detail, extra=[f"files={len(files_hit)} hits={len(hits)}"])

    counts = {"files": len(files_hit), "hits": len(hits)}
    ok = baseline_guard("ui_layer_gate", counts, BASELINE, update, accept_new)
    finish(ok)


if __name__ == "__main__":
    main()
