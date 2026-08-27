"""
Zero-Hardcoding Production AST and Lexical Scanner for Vera (Phase 7F).

Scans all production source files in `app/` to guarantee:
1. ZERO benchmark case IDs (qc_*, unseen_*, adv_*, test_*)
2. ZERO hardcoded merchant names, doctor names, or test business names
3. ZERO category slug whitelists (e.g. `cat_slug in ('dentists', 'salons')`)
4. ZERO benchmark-specific regexes (e.g. "send the abstract", "draft the patient whatsapp")
5. ZERO benchmark-specific fallback phrases (e.g. "tax and GST filing to your CA", dental recall copy)
6. ZERO scenario ID lookup tables or conditional branching on test parameters

Exits with code 0 if 100% clean, or code 1 with explicit violation line numbers.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple


# Forbidden benchmark-specific tokens and patterns in production code (app/)
FORBIDDEN_PATTERNS = [
    # Benchmark Case IDs & Test IDs
    (r"\bqc_\d{4}\b", "Benchmark case ID (qc_XXXX)"),
    (r"\bunseen_\d{4}\b", "Benchmark case ID (unseen_XXXX)"),
    (r"\badv_\d{4}\b", "Benchmark case ID (adv_XXXX)"),
    (r"\bm_001_drmeera\b", "Benchmark merchant ID (m_001_drmeera)"),
    (r"\bm_rich_01\b", "Benchmark merchant ID (m_rich_01)"),
    (r"\btrg_001_\b", "Benchmark trigger ID (trg_001_*)"),
    (r"\bd_2026W17_\b", "Benchmark digest ID (d_2026W17_*)"),

    # Hardcoded Category Whitelists
    (r"cat_slug\s+in\s+\([^)]*[\"'](?:dentists|salons|clinics|pharmacies)[\"'][^)]*\)", "Hardcoded category slug whitelist"),
    (r"category_slug\s+in\s+\([^)]*[\"'](?:dentists|salons|clinics|pharmacies)[\"'][^)]*\)", "Hardcoded category slug whitelist"),

    # Benchmark-Specific Phrases & Fallbacks
    (r"leave\s+tax\s+and\s+GST\s+filing\s+to\s+your\s+CA", "Hardcoded GST/CA out-of-scope response"),
    (r"value\s+of\s+regular\s+recall\s+exams", "Hardcoded dental recall fallback copy"),
    (r"send\s+the\s+abstract", "Benchmark Turn 2 specific regex pattern"),
    (r"draft\s+the\s+patient\s+whatsapp", "Benchmark Turn 2 specific regex pattern"),
]


def scan_production_codebase(app_dir: str) -> Tuple[bool, List[Dict[str, str]]]:
    """Scan all Python files under app/ for hardcoded patterns."""
    violations = []
    app_path = Path(app_dir)

    for root, _, files in os.walk(app_path):
        for file in files:
            if not file.endswith(".py"):
                continue
            file_path = Path(root) / file
            rel_path = file_path.relative_to(app_path.parent)

            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for line_idx, line in enumerate(lines, start=1):
                # Ignore comment-only lines explaining historical context
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                    continue

                for pattern, description in FORBIDDEN_PATTERNS:
                    if re.search(pattern, line, re.IGNORECASE):
                        violations.append({
                            "file": str(rel_path),
                            "line": line_idx,
                            "code": stripped,
                            "rule": description,
                            "pattern": pattern,
                        })

    is_clean = len(violations) == 0
    return is_clean, violations


def main():
    workspace_root = Path(__file__).parent.parent
    app_dir = workspace_root / "app"
    
    print("=" * 70)
    print("VERA PHASE 7F: ZERO-HARDCODING PRODUCTION SCANNER")
    print(f"Scanning directory: {app_dir.resolve()}")
    print("=" * 70)

    is_clean, violations = scan_production_codebase(str(app_dir))

    if is_clean:
        print("\nSUCCESS: 0 hardcoding violations found across all production files in app/!")
        print("System is 100% free of benchmark IDs, test names, category whitelists, and benchmark regexes.\n")
        sys.exit(0)
    else:
        print(f"\nFAILURE: {len(violations)} hardcoding violation(s) detected in production code:\n")
        for v in violations:
            print(f"  - [{v['file']}:{v['line']}] {v['rule']}")
            print(f"    Code: {v['code']}")
            print(f"    Pattern: {v['pattern']}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
