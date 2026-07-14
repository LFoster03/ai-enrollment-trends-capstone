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
