#!/usr/bin/env python3
"""playstate_gate.py — PlayState 单一真源门禁.

口径（skill/review/refactor-plan-20261007.md:253）:
  对 `app/src/main` 扫描五种已废除的旧 int 状态面模式，零命中退出 0。

  1. AppPlayerView.STATE_
  2. currentPlayState
  3. curPlayState
  4. fromLegacy / toLegacy
  5. OnStateChangeListener

注意：通知用的 PlaybackStateCompat.STATE_PLAYING 不属于此判定（不带 AppPlayerView. 前缀）。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _gate_common import (  # noqa: E402
    Hit,
    app_main_root,
    finish,
    main_sources,
    read_text,
    rel,
    report,
)

PATTERNS = [
    ("AppPlayerView.STATE_", re.compile(r"AppPlayerView\.STATE_")),
    ("currentPlayState", re.compile(r"\bcurrentPlayState\b")),
    ("curPlayState", re.compile(r"\bcurPlayState\b")),
    ("fromLegacy/toLegacy", re.compile(r"\b(?:fromLegacy|toLegacy)\b")),
    ("OnStateChangeListener", re.compile(r"\bOnStateChangeListener\b")),
]


def main() -> None:
    detail = "--detail" in sys.argv
    root = app_main_root()
    if not root.exists():
        print(f"[FAIL] 找不到 app/src/main: {root}")
        finish(False)

    hits: list[Hit] = []
    for path in main_sources(skip_vendored=True):
        text = read_text(path)
        for lineno, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith("//"):
                continue
            for name, pattern in PATTERNS:
                if pattern.search(line):
                    hits.append(Hit(rel(path), lineno, f"[{name}] {line.strip()}"))

    report("playstate_gate", hits, detail)
    if hits:
        print(f"[FAIL] playstate_gate: 命中 {len(hits)} 处旧 PlayState 接口（应为 0）")
        finish(False)

    print("[PASS] playstate_gate: 零命中")
    finish(True)


if __name__ == "__main__":
    main()
