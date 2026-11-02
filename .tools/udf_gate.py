#!/usr/bin/env python3
"""udf_gate.py — 单向数据流 8 条规则门禁.

口径（AGENTS.md「单向数据流」；refactor-plan-20261024.md §3.3/§12；§555 r7 升阻断）:

  r1  EventBus.getDefault().post( / @Subscribe
  r2  VM 持有者文件中 public MutableStateFlow / MutableSharedFlow / mutableStateOf 暴露
      （PlayerUiState / MusicPlayerState 容器除外）
  r3  ui/ 包中对 *.value = 的直写（接收者剥离 this./限定符后为同文件自有属性时不计）
  r4  @Suppress("UNUSED_EXPRESSION")  —— 零容忍
  r5  接口中的 override var（Host 可变属性模式）
  r6  App.setVodInfo / App.getVodInfo 引用
  r7  ui/ 包内 scheduler.set* / scheduler.mark* 直写
  r8  VM 持有者文件中 public MutableSharedFlow 暴露

基线 udf_gate_baseline.json 只允许下调（--update 拒绝上调），行级例外登记理由。
存量已全部归零，新增即 FAIL。

用法：
  python .tools/udf_gate.py
  python .tools/udf_gate.py --detail
  python .tools/udf_gate.py --update [--accept-new]
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
    main_sources,
    read_text,
    rel,
    report,
    strip_line_comment,
    ui_sources,
)

BASELINE = REPO_ROOT / ".tools" / "udf_gate_baseline.json"

VM_STATE_CONTAINERS = {"PlayerUiState", "MusicPlayerState"}

R1 = re.compile(r"EventBus\.getDefault\(\)\.post\(|@Subscribe\b")
R2 = re.compile(
    r"(?:^|\s)(?:val|var)\s+\w+\s*[:=][^=\n]*\b(?:MutableStateFlow|MutableSharedFlow|MutableState)\b"
)
R2_EXPOSED = re.compile(
    r"^\s*(?:public\s+|internal\s+)?(?:val|var)\s+\w+\s*[:=][^=\n]*\b"
    r"(?:MutableStateFlow|MutableSharedFlow|MutableState)\b"
)
R3 = re.compile(r"\b\w+\.value\s*=(?!=)")
R4 = re.compile(r'@Suppress\(\s*"UNUSED_EXPRESSION"\s*\)')
R5 = re.compile(r"\boverride\s+var\s+\w+")
R6 = re.compile(r"\bApp\.(?:set|get)VodInfo\b")
R7 = re.compile(r"\bscheduler\.(?:set|mark)\w*\s*\(")
R8 = R2_EXPOSED

DECL_NAME_RE = re.compile(r"^\s*(?:public\s+|internal\s+|private\s+)?(?:val|var)\s+(\w+)")


def is_vm_holder(path: Path, text: str) -> bool:
    name = path.stem
    if name in VM_STATE_CONTAINERS:
        return False
    return name.endswith("ViewModel") or "ViewModel" in name


def own_property_names(text: str) -> set[str]:
    names: set[str] = set()
    for line in text.splitlines():
        match = DECL_NAME_RE.match(line)
        if match:
            names.add(match.group(1))
    return names


def scan_ui_direct_write(path: Path, text: str) -> list[Hit]:
    hits: list[Hit] = []
    own = own_property_names(text)
    is_vm = is_vm_holder(path, text)
    for lineno, line in enumerate(text.splitlines(), 1):
        code = strip_line_comment(line)
        if not R3.search(code):
            continue
        if "MutableStateFlow" in code or "mutableStateOf" in code or "MutableState" in code:
            continue
        for match in re.finditer(r"\b(\w+)\.value\s*=(?!=)", code):
            receiver = match.group(1)
            if receiver in own or receiver == "this":
                continue
            if is_vm:
                own.add(receiver)
                continue
            hits.append(Hit(rel(path), lineno, line.strip()))
            break
    return hits


def main() -> None:
    args = sys.argv[1:]
    detail = "--detail" in args
    update = "--update" in args
    accept_new = "--accept-new" in args

    per_rule: dict[str, list[Hit]] = {f"r{i}": [] for i in range(1, 9)}
    ui_set = {str(p.resolve()) for p in ui_sources()}

    for path in main_sources(skip_vendored=True):
        text = read_text(path)
        lines = text.splitlines()
        in_ui = str(path.resolve()) in ui_set
        vm_holder = is_vm_holder(path, text)

        in_block = False
        for lineno, line in enumerate(lines, 1):
            stripped = line.strip()
            if in_block:
                if "*/" in line:
                    in_block = False
                continue
            if stripped.startswith("/*"):
                if "*/" not in stripped:
                    in_block = True
                continue
            if stripped.startswith("//") or stripped.startswith("*"):
                continue

            code = strip_line_comment(line)
            hit = Hit(rel(path), lineno, stripped)

            if R1.search(code):
                per_rule["r1"].append(hit)
            if vm_holder:
                if R8.search(code):
                    per_rule["r8"].append(hit)
                elif R2_EXPOSED.search(code) and "private" not in code:
                    per_rule["r2"].append(hit)
            if R4.search(code):
                per_rule["r4"].append(hit)
            if R5.search(code):
                per_rule["r5"].append(hit)
            if R6.search(code):
                per_rule["r6"].append(hit)
            if in_ui and R7.search(code):
                per_rule["r7"].append(hit)

        if in_ui:
            per_rule["r3"].extend(scan_ui_direct_write(path, text))

    counts = {rule: len(hits) for rule, hits in per_rule.items()}
    counts["total"] = sum(counts.values())
    for rule in sorted(per_rule):
        hits = per_rule[rule]
        if hits:
            report(f"udf_gate {rule}", hits, detail, extra=[f"hits={len(hits)}"])

    ok = baseline_guard("udf_gate", counts, BASELINE, update, accept_new, primary="total")
    finish(ok)


if __name__ == "__main__":
    main()
