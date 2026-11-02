#!/usr/bin/env python3
"""null_assert_gate.py — 裸 !! 门禁.

口径（SKILL.md §46；avbox-code-review-spec.md「空安全与非空断言」）:
  判定域 = app/src/main（含 Chaquopy app/src/python/java）
  判定域内裸 !! 已归零，新增即 FAIL
  libs/backdrop、quickjs、app/src/test 剔出判定域（只打印，不计 enforced）
  行级豁免 = 该行或上一行带 `// null-assert: keep`

例外形态（有可见判据）不报，但本门禁采用保守口径：
  只要出现 `!!` 且无 keep 标记即计为命中，除非该行是字符串字面量内的内容。
  `--raw` 输出 literal 与剥离字符串后两口径。

用法：
  python .tools/null_assert_gate.py            # 校验
  python .tools/null_assert_gate.py --detail
  python .tools/null_assert_gate.py --raw
  python .tools/null_assert_gate.py --update [--accept-new]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _gate_common import (  # noqa: E402
    Hit,
    REPO_ROOT,
    base_scan_roots,
    baseline_guard,
    iter_files,
    read_text,
    rel,
    report,
    strip_strings,
    finish,
)

BASELINE = REPO_ROOT / ".tools" / "null_assert_baseline.json"
KEEP_MARK = "null-assert: keep"
NOT_NULL_RE = re.compile(r"!(?!=)")


def _is_comment_line(line: str) -> bool:
    stripped = line.strip()
    return (
        stripped.startswith("//")
        or stripped.startswith("/*")
        or stripped.startswith("*")
        or stripped.endswith("*/")
    )


def scan(raw_mode: bool):
    hits: list[Hit] = []
    ignored: list[Hit] = []

    for path, enforced in base_scan_roots():
        text = read_text(path)
        lines = text.splitlines()
        in_block = False
        for lineno, line in enumerate(lines, 1):
            if in_block:
                if "*/" in line:
                    in_block = False
                continue
            stripped = line.strip()
            if stripped.startswith("/*"):
                if "*/" not in stripped:
                    in_block = True
                continue
            if _is_comment_line(line):
                continue
            code = line if raw_mode else strip_strings(line)
            if "!!" not in code:
                continue
            prev = lines[lineno - 2] if lineno >= 2 else ""
            if KEEP_MARK in line or KEEP_MARK in prev:
                continue
            hit = Hit(rel(path), lineno, line.strip())
            if enforced:
                hits.append(hit)
            else:
                ignored.append(hit)
    return hits, ignored


def main() -> None:
    args = sys.argv[1:]
    detail = "--detail" in args
    raw_mode = "--raw" in args
    update = "--update" in args
    accept_new = "--accept-new" in args

    hits, ignored = scan(raw_mode)

    enforced_files = sorted({h.path for h in hits})
    counts = {"hits": len(hits), "files": len(enforced_files)}

    report("null_assert_gate", hits, detail, extra=[f"enforced files={len(enforced_files)} hits={len(hits)}"])
    if ignored:
        print(f"[INFO] 判定域外（vendored/test）命中 {len(ignored)} 处，不计 enforced")
        if detail:
            for hit in ignored:
                print("  (ignored) " + hit.render())

    ok = baseline_guard("null_assert_gate", counts, BASELINE, update, accept_new)
    finish(ok)


if __name__ == "__main__":
    main()
