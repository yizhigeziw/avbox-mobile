#!/usr/bin/env python3
"""i18n_gate.py — ui 层中文硬闸门.

口径（avbox-i18n-spec.md §4.4/§7-A；avbox-code-review-spec.md）:
  判定对象 = app/src/main/java/.../osc/ui/**（含 ui/player/**）
  命中 = 含中文字符的字符串字面量
  豁免 = 该行或上一行带 `// i18n: keep`；日志调用上下文
  ui 层必须 0 处（硬闸门），非 ui 层只报告不阻断

已知盲区：`\\uXXXX` 转义中文不命中状态机（与上游一致）。
日志豁免前缀：AppLog. / Log.[dviwe] / printStackTrace / System.out / DebugLog / logger. / LogUtils

用法：
  python .tools/i18n_gate.py            # 校验（ui 层必须 0）
  python .tools/i18n_gate.py --detail
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _gate_common import (  # noqa: E402
    Hit,
    finish,
    main_sources,
    read_text,
    rel,
    report,
    strip_line_comment,
    ui_sources,
)

KEEP_MARK = "i18n: keep"

CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")
STRING_LITERAL_RE = re.compile(r'"(?:[^"\\]|\\.)*"')

LOG_ALLOW_RE = re.compile(
    r"(AppLog\.|Log\.[dviwe]|printStackTrace|System\.out|DebugLog|logger\.|LogUtils)"
)


def scan_file(path: Path):
    hits: list[Hit] = []
    lines = read_text(path).splitlines()
    in_block = False
    for lineno, line in enumerate(lines, 1):
        raw = line
        if in_block:
            if "*/" in raw:
                in_block = False
            continue
        stripped = raw.strip()
        if stripped.startswith("/*"):
            if "*/" not in stripped:
                in_block = True
            continue
        if stripped.startswith("//") or stripped.startswith("*"):
            continue

        code = strip_line_comment(raw)
        if LOG_ALLOW_RE.search(code):
            continue

        for match in STRING_LITERAL_RE.finditer(code):
            literal = match.group(0)
            if not CJK_RE.search(literal):
                continue
            prev = lines[lineno - 2] if lineno >= 2 else ""
            if KEEP_MARK in raw or KEEP_MARK in prev:
                continue
            hits.append(Hit(rel(path), lineno, raw.strip()))
            break
    return hits


def main() -> None:
    detail = "--detail" in sys.argv
    ui_set = {str(p.resolve()) for p in ui_sources()}

    ui_hits: list[Hit] = []
    non_ui_hits: list[Hit] = []

    for path in main_sources(skip_vendored=True):
        hits = scan_file(path)
        if not hits:
            continue
        if str(path.resolve()) in ui_set:
            ui_hits.extend(hits)
        else:
            non_ui_hits.extend(hits)

    report("ui 层（硬闸门，须 0 处）", ui_hits, detail, extra=[f"hits={len(ui_hits)}"])
    report("非 ui 层（仅报告）", non_ui_hits, detail, extra=[f"hits={len(non_ui_hits)}"])

    if ui_hits:
        print(f"[FAIL] i18n_gate: ui 层中文硬闸门 {len(ui_hits)} 处（须 0）")
        finish(False)

    print(f"[PASS] i18n_gate: ui 层 0 处；非 ui 层 {len(non_ui_hits)} 处（不阻断）")
    finish(True)


if __name__ == "__main__":
    main()
