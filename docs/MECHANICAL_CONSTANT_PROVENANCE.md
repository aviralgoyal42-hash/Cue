# Where the model's constants come from (ESM Table S1)

Date: 2026-11-04.

- **Source file:** `docs/sources/rsos242062_si_001.pdf`, the supplement to Lister et al. 2025, figshare file 58293510. Its MD5 checksum matches the figshare record. Extracted text is in `docs/sources/rsos242062_si_001.txt`.
- **Full table, row by row:** `docs/sources/table_s1_constants.csv` (60 rows).
- **Check:** `tests/test_task1_provenance.py` compares every row with the upstream code.

## Result

| Group | Rows | Source the table cites | Species |
|---|---|---|---|
| Mechanical and flow constants (all listed in the CSV) | 35 | **Bastiaanssen et al. 1996**, *J Theor Biol* 178:113–133, for every row. No row cites anything else. | **Unconfirmed for all 34 tissue and geometry constants.** The urine density is not species-specific. |
| Volume limit, voiding thresholds, maximum urethral radius | 4 | **"New"** (Lister et al. 2025): no primary source | Not applicable |
| Kidney parameters and noise | 5 | **"New"** | Not applicable |
| Neural controller parameters | 16 | **"New"** | Not applicable |
| Curve constants written directly into the code (not in Table S1) | see below | **None given** | Unconfirmed |

## Why species stays unconfirmed

- Table S1 has no species column and no species note.
- The Bastiaanssen 1996 abstract (Wageningen record) refers to clinical urodynamic data in general and names no species. I could not get the full paper: the publisher page did not return the text.
- Lister et al. call the model "the human LUT model". That points towards human values, but it is a description of the whole model, not evidence for any single constant.
- Bastiaanssen 1996 may itself take values from earlier work, possibly including animal muscle studies. I have not seen this, so the 1996 paper is the **cited** source, not a confirmed primary measurement.

**So every tissue constant is marked: source Bastiaanssen 1996 (as cited by Lister et al.), species unconfirmed.** I have not inferred a species.

## What else the table showed

1. **All values match the code.** Each of the 60 rows agrees with the upstream code, apart from the two labelling points in items 2 and 3 below. The pressure threshold is printed rounded (5.367 × 10³, code 5.3669 × 10³).
2. **Phase shift label differs.** The table prints π/5400 rad; the code stores 2400π. They agree only if the code value is divided by 3600². The phase actually used in the sine is 2π/3 rad (8 h). This is a labelling difference with no effect on results.
3. **Symbol typo.** The table prints "A_nomS" but describes the detrusor. The code name is `A_nomD`.
4. **The numbers that set Cue's key behaviour are not from the 1996 paper.** The 500 mL limit, the 54.7 cmH₂O void trigger and the maximum urethral radius are all "New", with no primary source. So are all the neural drives, including `somatic_a`, which decides whether the SCI bladder leaks (Stage 3). V_ref = 500 mL in our criteria therefore rests on an unsourced number.
5. **Two listed constants do nothing in the code.** `h_D` and `p_theta` are never used. `c_r` (code name `C_p`) is switched off by default.
6. **Constants in the code that Table S1 does not list:**
   - the detrusor force–length curve (`sigma_lD_s`: breakpoints 0.35, 0.45, 1.1, 1.4 and its coefficients), which drives the falling pressure on over-filling (E18);
   - the sphincter force–length curve (`sigma_lS_s`: 1.73 × 10⁻⁶, 2.89 × 10⁻⁶ and the points in `points`);
   - the force–velocity curve (1.8, 0.8, 7.56);
   - the void-stop volume (10⁻⁸ m³).

   These probably come from the 1996 model, but neither the table nor the paper says so. They are marked **unconfirmed**.

## What changes in our labels

Upstream defaults stay labelled SOURCED, meaning "taken from the upstream implementation", as `config.py` already explains. SOURCED never meant validated. `fullness_reference_ml` and `reference_volume_ml` now state that Table S1 calls 500 mL "New". No value changed, and no result changes.
