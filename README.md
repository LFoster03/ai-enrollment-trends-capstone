## ISU Registrar Data Cleaning

### Overview

`scripts/clean_isu_enrollment.py` cleans a single semester's ISU Registrar
"Enrollment by Major or Department" Excel file and extracts headcount data
for a set of target undergraduate programs, split into three tiers:

- **Primary (AI-adjacent) programs** — the majors central to this project's
  hypothesis: Computer Science, Software Engineering, Electrical
  Engineering, Computer Engineering, and Cyber Security Engineering.
- **Control Group programs** — Mechanical Engineering and Civil
  Engineering, tracked as a baseline to check whether any observed shift
  is specific to AI-adjacent fields or reflects a broader engineering-wide
  trend.
- **Broad totals** — a college-level Engineering total (pulled directly
  from the file's own "Engineering Total" subtotal row) and a computed
  Computer Science total (B.A. + B.S. summed, since ISU does not publish
  a standalone CS subtotal). These broad totals are the only granularity
  level that lines up with the national NSC/CERP data used elsewhere in
  this project, since those sources report at the CIP-family level
  (e.g. "Engineering," "Computer and Information Sciences") rather than
  by individual major.

### Source data

Files are downloaded manually from the [ISU Office of the Registrar's
Enrollment by Major or Department
page](https://www.registrar.iastate.edu/faculty-staff/data-systems/enrollment-stats/major-dept)
and saved into `data/raw/`. This project uses **Fall semesters only**
(Fall 2019–Fall 2025), since the national comparison sources (NSC, CERP)
report on a Fall-term basis, and combining Fall and Spring into a blended
year would break that comparison.

### File structure notes (found through trial and error)

These reports are multi-sheet workbooks, not single flat tables:

- `Total` — a small summary sheet (Male/Female/Total by student level).
  **Not used** by this script.
- `UG` — undergraduate enrollment by program, broken out by class year
  (First Year/Sophomore/Junior/Senior/Non-Degree) and sex, with a Grand
  Total column. **This is the sheet the script reads.**
- `VM` — veterinary medicine students. Not used.
- `Grad` — graduate student enrollment. Not used.

Within the `UG` sheet:
- Real column headers ("College," "Program of Study," etc.) start
  several rows down, below a title block. The script locates this row
  dynamically by searching for a cell that equals "College," rather than
  assuming a fixed row number, since header position has been observed to
  shift slightly between years.
- "Grand Total" is stored as a header cell containing a literal line
  break (`Grand\nTotal`), so searches for exact phrases in header text
  need to tolerate embedded whitespace/newlines.
- Program-level rows have the department name in the **Program of Study**
  column (column 1) and the college name only on the *first* row of each
  college's block (subsequent rows leave College blank).
- **College-level subtotal rows** (e.g. "Engineering Total," "Business
  Total," "Grand Total") are structured differently than program rows:
  the label appears in the **College** column (column 0), and the
  Program of Study column (column 1) is blank. The script checks for
  these subtotal labels before checking Program of Study, so they are
  correctly captured (in the case of "Engineering Total") or skipped
  (all other subtotals), rather than being dropped silently or mismatched.

### Usage

```powershell
python scripts\clean_isu_enrollment.py "data\raw\ISU_Fall2025.xlsx" "Fall 2025"
```

Run once per Fall semester (2019–2025), swapping the filename and
semester label each time. Output is saved automatically to
`data/cleaned/`:

- `ISU_<Semester>_granular.csv` — one row per matched program, tagged
  with its tier (Primary/Control) and headcount.
- `ISU_<Semester>_broad.csv` — the two broad totals (Engineering,
  Computer Science) for that semester.

### Logging

Every run is automatically logged to `project.log` at the repo root via
`scripts/project_logger.py`, recording the timestamp, file processed,
and a summary of how many programs matched. No manual logging is
required — just run the cleaning script as usual.

### Known limitations

- Column position assumptions (Program of Study = column 1, College =
  column 0, Grand Total = last column) were confirmed against the Fall
  2025 file specifically. If a given year's report has a different
  number of columns or a reordered layout, the script may need minor
  adjustment — run `scripts/inspect_file.py` on that file first to check
  before assuming the cleaning script will work unmodified.
- "Computer Engineering" is tracked as a Primary program even though it
  was not one of the four majors named in the original department
  observation (Software Engineering, Computer Science, Electrical
  Engineering, Cybersecurity), since it sits at the intersection of the
  project's hypothesis and was judged worth tracking as a secondary line.

## Merging Semesters into One Time Series

`scripts/merge_isu_years.py` combines every per-semester file in
`data/cleaned/` into two continuous time-series files:

- **`ISU_combined_granular.csv`** — one row per (major, semester),
  sorted chronologically Fall 2019 → Fall 2025.
- **`ISU_combined_broad.csv`** — the Engineering and Computer Science
  broad totals, one row per category per semester, for comparison
  against the national NSC/CERP data.

### Usage

```powershell
python scripts\merge_isu_years.py
```

Run this after `clean_isu_enrollment.py` has been run for every target
semester. It can be safely re-run at any time (e.g. after re-cleaning a
corrected file) — see the self-referencing glob fix below for why this
wasn't always true.

## Data Quality Issues Found During Testing

The first pass at cleaning surfaced three real data-quality problems.
Each is documented here since the underlying causes (ISU's report
formatting quirks) could resurface in future semesters and are worth
knowing about rather than re-discovering from scratch.

### 1. Non-primary-major rows were being counted

The initial matching logic used a simple "does this program name
contain the target text" check. This correctly matched real programs,
but also matched rows like `Computer Science (BS) Undergraduate
Additional Major`. An "Additional Major" row represents a student whose
*primary* major is something else, who is already counted once
elsewhere in the file — including this row would double-count that
student under a category they aren't actually majoring in.

**Fix:** `tier_for()` now excludes any row containing "additional
major," "pre-major," "non-degree," or "undeclared," so only students'
primary declared major is counted.

### 2. Re-running the merge script doubled every row

`merge_isu_years.py` searches for files matching the pattern
`ISU_*_granular.csv`. That wildcard also matches the script's *own*
output file, `ISU_combined_granular.csv`. Running the merge a second
time (e.g. after re-cleaning a corrected semester) would pick up the
previous combined file — which already contained one full copy of
every semester — as an additional input, doubling every row.

**Fix:** the glob match now explicitly excludes any filename containing
"combined," so the script never treats its own prior output as a new
input.

### 3. Software Engineering is a joint program, listed under two colleges

In Fall 2019–2021 files, "Software Engineering" appeared as **two**
separate rows with different headcounts (e.g. 416 and 409 in Fall
2019) — one nested under the Engineering college block, one nested
under Liberal Arts and Sciences. This is not duplicate data: Iowa
State's Software Engineering B.S. is a joint program between the
College of Engineering and the College of Liberal Arts and Sciences,
so students are administratively split across both colleges in the
Registrar's own report, even though they share one major. (Reports
from Fall 2022 onward list Software Engineering under a single college
only, suggesting ISU changed how this joint listing is reported partway
through the project's date range — worth keeping in mind when
interpreting the Software Engineering trend line, since pre- and
post-2022 figures may not be perfectly like-for-like.)

**Fix:** `clean_isu_file()` now groups all matched rows by category,
tier, and semester, and **sums** their headcounts into a single row,
rather than leaving same-category rows split across multiple lines. A
`Source_Programs` column records exactly which raw program name(s)
contributed to each summed total, so the aggregation is fully
traceable back to the source data.

### Verified output

After all three fixes, `ISU_combined_granular.csv` contains exactly 49
rows — 7 tracked categories (Computer Science, Software Engineering,
Electrical Engineering, Computer Engineering, Cyber Security
Engineering, Mechanical Engineering, Civil Engineering) × 7 Fall
semesters (2019–2025) — with no duplicate rows and no non-primary-major
contamination.

## NSC National Data Cleaning

### Overview

`scripts/clean_nsc_national.py` cleans the National Student Clearinghouse
(NSC) Research Center's "Final Fall Enrollment Trends" Data Appendix and
extracts national undergraduate 4-year enrollment totals for:

- **CIP 11** — Computer and Information Sciences and Support Services
  (labeled "Computer Science" in this project's output)
- **CIP 14** — Engineering

These are the two CIP-family categories that line up with this
project's broad Engineering and Computer Science totals from the ISU
data, since NSC reports at the CIP-family level rather than by
individual major.

### Source data

Downloaded from
[nscresearchcenter.org/final-fall-enrollment-trends](https://nscresearchcenter.org/final-fall-enrollment-trends/),
saved into `data/raw/`.

**Important:** a single appendix download covers multiple years as
side-by-side columns, not just the one year in its filename. The Fall
2025 appendix (`NSC_Fall2025_Appendix.xlsx`), for example, contains
2020 through 2025 all in one file. Only one appendix file was needed
for this project as a result, rather than one per year.

### Fall 2019 (no Data Appendix exists for this year)

NSC did not publish a downloadable Data Appendix for Fall 2019 --
only a narrative PDF report. The Fall 2019 figures used in this
project (Engineering = 595,142; Computer Science = 474,573) were
manually extracted from Table 11 (four-year institutions) of that
report, `CTEE_Report_Fall_2019.pdf`.

This PDF has been saved to `data/raw/` for documentation and
traceability, so the source of these two hardcoded numbers can be
independently verified. **The cleaning script does not read this PDF
directly** -- the two figures are hardcoded as `FALL_2019_MANUAL` at
the top of `clean_nsc_national.py`, since extracting numbers from PDF
text programmatically wasn't worth building for two data points. The
file's presence in `data/raw/` is purely for citation/audit purposes.

### Usage

```powershell
python scripts\clean_nsc_national.py "data\raw\NSC_Fall2025_Appendix.xlsx"
```

Output is saved to `data/cleaned/NSC_national_combined.csv`, containing
one row per (Category, Semester), covering Fall 2019 through Fall 2025
-- both the six years read from the appendix and the one manually
entered Fall 2019 year, combined and sorted chronologically in a
single file.

### Known data quality notes

- Enrollment figures in the appendix are non-integer NSC estimates
  (their underlying methodology involves extrapolation); the script
  rounds these to whole numbers for readability.
- A small number of states have suppressed ("*") values for some
  CIP/year combinations, presumably due to small underlying counts.
  These are excluded from the national sum (treated as missing, not
  zero), so national totals may be very slightly undercounted rather
  than overcounted.
- Comparing this appendix's figures against the standalone Fall 2019,
  2020, and 2021 PDF reports shows minor discrepancies (e.g. Fall 2021
  Computer Science: 507,492 in the original PDF vs. 513,475 in the
  Fall 2025 appendix's revised 2021 column). This is expected --
  NSC revises prior-year estimates in later report vintages -- and is
  noted here as a limitation rather than an error: the Fall 2019 figure
  used in this project comes from the original Fall 2019 PDF, while
  2020-2025 figures come from the most recent (Fall 2025) appendix's
  revised figures for those years.

## CERP Completions Data Cleaning

### Overview

`scripts/clean_cerp_completions.py` cleans two CERP (Computing Research
Association's Center for Evaluating the Research Pipeline) datasets,
derived from IPEDS, and extracts national Bachelor's-level degree
**completions** for Computer Science (CIP 11.x) and Engineering
(CIP 14.x), summed across gender and race/ethnicity.

**This is degree completions data (degrees awarded per year), not
enrollment.** It measures a fundamentally different thing than the
ISU and NSC datasets used elsewhere in this project: completions
reflect students who declared their major years earlier and are now
graduating, while enrollment reflects current, active student
headcounts. For this reason, CERP completions data is kept in its own
separate output file (`CERP_completions_combined.csv`) rather than
merged into the same time series as the ISU/NSC enrollment data. See
"Why this matters" below for why this distinction turned out to be
analytically important, not just a technicality.

### Source data

Two CSVs downloaded from CERP's Data Resources page
([cra.org/cerp/data-resources-and-reports](https://cra.org/cerp/data-resources-and-reports/)),
covering 2011-2024:

- `CERP_computing_completions.csv` (originally
  `IPEDS_nationalAwards_computing_allDemographics_allCIP_2011-2024.csv`)
- `CERP_engineering_completions.csv` (originally
  `IPEDS_nationalAwards_engineering_allDemographics_allCIP_2011-2024.csv`)

Both were renamed after download and saved into `data/raw/` for
consistency with this project's other source files.

### File structure notes

- Each row represents one (Award Level, CIP Code, Gender,
  Race/Ethnicity) combination, with one column per year (2011-2024)
  containing the completions count for that combination.
- **The "computing" file is not limited to Computer Science** -- it
  includes other related CIP families as well (e.g. CIP 10.x,
  Communications Technologies/Animation). The script filters
  specifically to CIP codes starting with `"11."`, to stay consistent
  with how Computer Science is defined elsewhere in this project
  (matching NSC's CIP 11 category).
- `awardLevel` includes multiple degree levels (Associate's,
  Bachelor's, etc.). The script filters to Bachelor's only, to match
  this project's focus on undergraduate students.
- `cipCode` combines the numeric code and a text description in a
  single field (e.g. `"11.0101 Computer and Information Sciences,
  General"`); the script matches on the numeric prefix rather than
  requiring an exact string match, since multiple specific CIP codes
  fall under each broad family.

### Usage

```powershell
python scripts\clean_cerp_completions.py "data\raw\CERP_computing_completions.csv" "data\raw\CERP_engineering_completions.csv"
```

Output is saved to `data/cleaned/CERP_completions_combined.csv`, with
one row per (Category, Year), covering 2011-2024.

### Why this matters: a completions vs. enrollment divergence

The cleaned CERP data shows Computer Science Bachelor's completions
growing every year from 2011-2024 with no exceptions (32,588 to
119,957), while Engineering completions peaked in 2020 (130,282) and
have declined every year since -- and the two lines cross for the
first time in 2024, with CS completions (119,957) overtaking
Engineering (118,009).

This is the **opposite** pattern from what the ISU and NSC enrollment
data show for the same recent years (where CS enrollment has recently
plateaued/declined while Engineering has been recovering). This isn't
a contradiction between sources -- it's consistent with a lagged
effect: a 2024 CS graduate likely declared that major years earlier
(around 2020-2021), well before AI-driven career concerns became
widely discussed, while current enrollment data reflects choices being
made right now. Comparing completions against enrollment is therefore
useful supporting evidence for the project's central hypothesis, not
just a mismatched data source -- the shift shows up first in current
enrollment/declaration behavior, and would only be expected to show up
in completions data several years later.
