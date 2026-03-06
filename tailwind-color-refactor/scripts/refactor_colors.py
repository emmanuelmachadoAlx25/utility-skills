#!/usr/bin/env python3
"""
tailwind-color-refactor/scripts/refactor_colors.py

Replaces hardcoded hex colors in Tailwind class attributes with CSS custom property names.
Reads @theme block from a CSS file, performs exact/fuzzy matching, and adds missing variables.
"""

import re
import os
import sys
import math
import argparse
from pathlib import Path
from collections import defaultdict

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

FUZZY_THRESHOLD = 20  # Max RGB distance to consider colors "similar"

TAILWIND_PREFIXES = [
    "text", "bg", "border", "divide", "ring",
    "placeholder", "outline", "accent", "caret",
    "fill", "stroke", "shadow", "decoration",
    "from", "via", "to",
]

# Matches: text-[#abc123], bg-[#ABC], border-[#aabbcc], etc.
# Also matches Angular: [class.text-[#abc]], [class.border-[#abc]]
HEX_PATTERN = re.compile(
    r'(\[class\.)?'                          # optional Angular [class. prefix
    r'(' + '|'.join(TAILWIND_PREFIXES) + r')'  # utility prefix
    r'-\[#([0-9a-fA-F]{3,6})\]'             # [#hex]
    r'(\])?',                                # optional closing ] for Angular
    re.IGNORECASE
)

# Matches @theme { ... } block
THEME_BLOCK_PATTERN = re.compile(r'@theme\s*\{([^}]+)\}', re.DOTALL)

# Matches --color-name: #hex;
COLOR_VAR_PATTERN = re.compile(r'--color-([a-zA-Z0-9_-]+)\s*:\s*#([0-9a-fA-F]{3,6})\s*;')


# ─────────────────────────────────────────────
# COLOR UTILITIES
# ─────────────────────────────────────────────

def expand_hex(hex_str: str) -> str:
    """Expand 3-char hex to 6-char: 'abc' → 'aabbcc'"""
    h = hex_str.lower()
    if len(h) == 3:
        return h[0]*2 + h[1]*2 + h[2]*2
    return h


def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    h = expand_hex(hex_str)
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    return r, g, b


def color_distance(hex1: str, hex2: str) -> float:
    r1, g1, b1 = hex_to_rgb(hex1)
    r2, g2, b2 = hex_to_rgb(hex2)
    return math.sqrt((r1-r2)**2 + (g1-g2)**2 + (b1-b2)**2)


# ─────────────────────────────────────────────
# CSS THEME PARSING
# ─────────────────────────────────────────────

def parse_theme(css_path: Path) -> dict[str, str]:
    """Returns {hex_value: variable_name} from @theme block."""
    content = css_path.read_text(encoding="utf-8")
    match = THEME_BLOCK_PATTERN.search(content)
    if not match:
        return {}

    color_map = {}
    for var_match in COLOR_VAR_PATTERN.finditer(match.group(1)):
        var_name = var_match.group(1)   # e.g. "primary", "cfdcdb"
        hex_val  = expand_hex(var_match.group(2))  # e.g. "a7d5d3"
        color_map[hex_val] = var_name

    return color_map


def add_color_to_theme(css_path: Path, hex_val: str) -> None:
    """Appends a new --color-HHHHHH variable inside the @theme block."""
    content = css_path.read_text(encoding="utf-8")
    hex_norm = expand_hex(hex_val)
    new_var = f"  --color-{hex_norm}: #{hex_norm};\n"

    # Insert before closing brace of @theme
    updated = re.sub(
        r'(@theme\s*\{[^}]*?)(\})',
        lambda m: m.group(1) + new_var + m.group(2),
        content,
        flags=re.DOTALL
    )

    css_path.write_text(updated, encoding="utf-8")


# ─────────────────────────────────────────────
# MATCHING LOGIC
# ─────────────────────────────────────────────

def find_replacement(
    hex_val: str,
    color_map: dict[str, str],
) -> tuple[str, str]:
    """
    Returns (variable_name, match_type) where match_type is:
      'exact'  - exact hex match
      'fuzzy'  - closest color within threshold
      'new'    - no match, must add to CSS
    """
    norm = expand_hex(hex_val)

    # Exact match
    if norm in color_map:
        return color_map[norm], "exact"

    # Fuzzy match
    best_var = None
    best_dist = float("inf")
    for mapped_hex, var_name in color_map.items():
        dist = color_distance(norm, mapped_hex)
        if dist < best_dist:
            best_dist = dist
            best_var = (var_name, mapped_hex)

    if best_dist <= FUZZY_THRESHOLD and best_var:
        return best_var[0], f"fuzzy:{best_var[1]}:{best_dist:.1f}"

    return norm, "new"


# ─────────────────────────────────────────────
# REPLACEMENT ENGINE
# ─────────────────────────────────────────────

def replace_in_content(
    content: str,
    color_map: dict[str, str],
    css_path: Path,
    dry_run: bool,
    stats: dict,
    file_path: str,
) -> str:
    def replacer(match):
        angular_open = match.group(1) or ""
        prefix       = match.group(2)
        hex_raw      = match.group(3)
        angular_close = match.group(4) or ""

        var_name, match_type = find_replacement(hex_raw, color_map)

        if match_type == "new":
            if not dry_run:
                add_color_to_theme(css_path, hex_raw)
                color_map[expand_hex(hex_raw)] = var_name  # update in-memory map
            stats["new"].append((expand_hex(hex_raw), file_path))
        elif match_type.startswith("fuzzy"):
            _, original_hex, dist = match_type.split(":")
            stats["fuzzy"].append((expand_hex(hex_raw), var_name, original_hex, float(dist), file_path))
        else:
            key = expand_hex(hex_raw)
            stats["exact"][key] = stats["exact"].get(key, {"count": 0, "files": set()})
            stats["exact"][key]["count"] += 1
            stats["exact"][key]["files"].add(file_path)

        # Build replacement class
        new_class = f"{angular_open}{prefix}-{var_name}{angular_close}"
        return new_class

    return HEX_PATTERN.sub(replacer, content)


# ─────────────────────────────────────────────
# FILE SCANNER
# ─────────────────────────────────────────────

def process_files(
    src_dir: Path,
    extensions: list[str],
    color_map: dict[str, str],
    css_path: Path,
    dry_run: bool,
) -> dict:
    stats = {
        "files_modified": 0,
        "total_replacements": 0,
        "exact": {},
        "fuzzy": [],
        "new": [],
    }

    for ext in extensions:
        for file_path in src_dir.rglob(f"*.{ext}"):
            original = file_path.read_text(encoding="utf-8")
            modified = replace_in_content(
                original, color_map, css_path, dry_run, stats, str(file_path)
            )

            if modified != original:
                stats["files_modified"] += 1
                if not dry_run:
                    file_path.write_text(modified, encoding="utf-8")
                else:
                    print(f"\n[DRY RUN] Would modify: {file_path}")
                    # Show diff lines
                    orig_lines = original.splitlines()
                    mod_lines  = modified.splitlines()
                    for i, (o, m) in enumerate(zip(orig_lines, mod_lines)):
                        if o != m:
                            print(f"  Line {i+1}:")
                            print(f"    - {o.strip()}")
                            print(f"    + {m.strip()}")

    return stats


# ─────────────────────────────────────────────
# REPORT
# ─────────────────────────────────────────────

def print_report(stats: dict, dry_run: bool) -> None:
    mode = "DRY RUN — no files changed" if dry_run else "Changes applied"
    print(f"\n{'='*55}")
    print(f"  Tailwind Color Refactor — {mode}")
    print(f"{'='*55}")

    print(f"\n📁 Files modified:      {stats['files_modified']}")

    if stats["exact"]:
        print(f"\n✅ Exact replacements:")
        for hex_val, data in stats["exact"].items():
            files = ", ".join(sorted(data["files"]))
            print(f"   #{hex_val} → {hex_val}  ({data['count']}x in: {files})")

    if stats["fuzzy"]:
        print(f"\n⚠️  Fuzzy substitutions (review manually):")
        for (hex_raw, var_used, original_hex, dist, fp) in stats["fuzzy"]:
            print(f"   #{hex_raw} ≈ #{original_hex} (dist {dist:.0f}) → {var_used}  [{fp}]")

    if stats["new"]:
        print(f"\n➕ New variables added to CSS theme:")
        for (hex_val, fp) in stats["new"]:
            print(f"   --color-{hex_val}: #{hex_val}  (from: {fp})")

    if not stats["exact"] and not stats["fuzzy"] and not stats["new"]:
        print("\n✨ No hardcoded hex colors found. Nothing to replace.")

    print(f"\n{'='*55}\n")


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Replace hardcoded hex colors in Tailwind class attributes."
    )
    parser.add_argument("--css",     required=True,  help="Path to main.css / colors.css with @theme block")
    parser.add_argument("--src",     required=True,  help="Source directory to scan")
    parser.add_argument("--ext",     default="html,jsx,tsx,ts,js", help="Comma-separated file extensions")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing files")
    args = parser.parse_args()

    css_path = Path(args.css)
    src_dir  = Path(args.src)
    extensions = [e.strip().lstrip(".") for e in args.ext.split(",")]

    if not css_path.exists():
        print(f"❌ CSS file not found: {css_path}", file=sys.stderr)
        sys.exit(1)

    if not src_dir.exists():
        print(f"❌ Source directory not found: {src_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"📂 CSS theme file : {css_path}")
    print(f"📂 Source dir     : {src_dir}")
    print(f"📄 Extensions     : {extensions}")
    print(f"🔍 Mode           : {'DRY RUN' if args.dry_run else 'APPLY'}")

    color_map = parse_theme(css_path)
    print(f"🎨 Colors in theme: {len(color_map)}")

    stats = process_files(src_dir, extensions, color_map, css_path, args.dry_run)
    print_report(stats, args.dry_run)


if __name__ == "__main__":
    main()