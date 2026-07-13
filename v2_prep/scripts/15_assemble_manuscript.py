"""
15_assemble_manuscript.py — Word-source manuscript assembly.

Two modes:
  strip  <canonical.md> <out_placeholder.md>
      Replace each injected table block with a {{TABLE X}} token and insert
      {{FIGURE n}} before each figure caption. Used ONCE to seed the Word source.
  inject <prose.md> <out_canonical.md> <source.docx>
      Replace {{TABLE X}} tokens with v2_prep/manuscript/tables/TX.md and
      {{FIGURE n}} with the figure image; prepend a dated build stamp. Used by
      assemble.sh on every build (Word -> canonical -> render).

Placeholders (author types these in Word):
  {{TABLE 2}} {{TABLE 3}} {{TABLE 4}} {{TABLE 5}} {{TABLE 6}} {{TABLE 7}}
  {{TABLE A2}} {{TABLE A3}}   {{FIGURE 1}} {{FIGURE 2}} {{FIGURE 3}}
"""
import sys, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parents[1] / "manuscript"
TBL  = HERE / "tables"

# table token -> (start substring, end substring) for STRIP; -> tables/<file> for INJECT
TABLES = [
    ("TABLE 2",  "**Table 2. Sample descriptives",   "three five-point items (Section 3.2).",        "T2.md"),
    ("TABLE 3",  "**Table 3. The estimation ladder",  "Random exposure slopes from M2 onward.",       "T3.md"),
    ("TABLE 4",  "**Table 4. Cross-level interactions","parametric-bootstrap percentile CIs.",        "T4.md"),
    ("TABLE 5",  "**Table 5. Temporal specification", "unchanged by the temporal terms.",             "T5.md"),
    ("TABLE 6",  "**Table 6. The fear cross-section", "all refits non-singular, 23 countries.",       "T6.md"),
    ("TABLE 7",  "**Table 7. Robustness",             "not comparable across constructions.",         "T7.md"),
    ("TABLE A2", "**Table A2. NACE-section",          "no contributing NAICS-4 codes with BLS employment.", "TA2.md"),
    ("TABLE A3", "| Country | Task axis",             "assignment from median splits on the 29-country base.", "TA3.md"),
]
FIGURES = {1: ("F1_typology.png", 90), 2: ("F2_perwave_RD_slopes.png", 90), 3: ("F3_country_slopes.png", 80)}

def strip(src, out):
    text = Path(src).read_text(encoding="utf-8")
    missing = []
    for tok, start, end, _ in TABLES:
        i = text.find(start)
        j = text.find(end, i) if i >= 0 else -1
        if i < 0 or j < 0:
            missing.append(tok); continue
        text = text[:i] + "{{" + tok + "}}" + text[j + len(end):]
    for n in FIGURES:
        marker = f"**Figure {n}."
        if marker in text:
            text = text.replace(marker, "{{" + f"FIGURE {n}" + "}}\n\n" + marker, 1)
        else:
            missing.append(f"FIGURE {n}")
    Path(out).write_text(text, encoding="utf-8")
    print(f"strip -> {out}")
    if missing: print("  *** anchors NOT found (check before seeding):", ", ".join(missing))
    else: print("  all 8 table blocks + 3 figures tokenized")

def inject(prose, out, source_docx):
    text = Path(prose).read_text(encoding="utf-8")
    unresolved = []
    for tok, _, _, fname in TABLES:
        token = "{{" + tok + "}}"
        if token in text:
            text = text.replace(token, (TBL / fname).read_text(encoding="utf-8").rstrip())
        else:
            unresolved.append(tok)
    for n, (fname, w) in FIGURES.items():
        token = "{{" + f"FIGURE {n}" + "}}"
        if token in text:
            text = text.replace(token, f"![]({fname}){{width={w}%}}")
        else:
            unresolved.append(f"FIGURE {n}")
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    day = datetime.datetime.now().strftime("%Y-%m-%d")
    src = Path(source_docx)
    mt = datetime.datetime.fromtimestamp(src.stat().st_mtime).strftime("%Y-%m-%d %H:%M") if src.exists() else "unknown"
    stamp = (f"<!-- ASSEMBLED {now} from {src.name} (source modified {mt}). "
             f"GENERATED FILE — DO NOT EDIT; edit the Word source. -->\n\n"
             f"*Draft build: {day} · source: {src.name} (modified {mt}).*\n\n")
    Path(out).write_text(stamp + text, encoding="utf-8")
    print(f"inject -> {out}  (source {src.name}, mod {mt})")
    if unresolved:
        print("  *** placeholders NOT found in prose (typos in Word?):", ", ".join(unresolved))
    else:
        print("  all 8 tables + 3 figures injected")

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "strip" and len(sys.argv) == 4:
        strip(sys.argv[2], sys.argv[3])
    elif mode == "inject" and len(sys.argv) == 5:
        inject(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        sys.exit(__doc__)
