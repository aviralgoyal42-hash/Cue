# Task 8, Phase 0: what the literature says about a second bladder signal (REFERENCE ONLY)

Date: 2026-11-11. Read-only search, about 20 minutes.

**How to read this file**
- Everything below is **SOURCED**, but **from search-result summaries and abstracts only. No full text was read.** Treat every figure as unverified until someone reads the paper.
- **Nothing here was used to set any Task 8 value.** The sensor B grid in `docs/TASK8_PLAN.md` is ASSUMED and was fixed without reference to these figures.
- None of this says that any real device meets the requirement that Task 8 computes. The simulation cannot say that either.
- Sensor B in Task 8 is abstract. It is not a model of any technology or product below.

## 1. Near-infrared light through the skin

| Point | Source (summary only) |
|---|---|
| A 2023 narrative review found only a handful of studies of wearable near-infrared bladder-volume monitors, and proposed a standard gel phantom for bench testing, because validation methods differ between groups | *Transl Androl Urol* 2023, narrative review, PubMed 38106685 |
| A 2012 review attributes slow adoption of near-infrared monitoring in urology to limits of the technique, doubt about what the signal measures, weak early algorithms and unrealistic expectations of reproducibility | Macnab and colleagues, 2012 review |
| A 2025 review reports over 85% sensitivity for detecting detrusor overactivity, in small trials. That is a detection figure, not a volume error | *Int Neurourol J* 2025 review |

**Error range found for volume: none.** The summaries gave no volume error in mL or percent.
**Failure modes named:** unclear what is measured; poor reproducibility; lack of standard validation. Effects of skin and fat thickness, movement and person-to-person calibration were **not** found in the summaries and would need the full papers.

## 2. Implanted sensors

| Point | Source (summary only) |
|---|---|
| A wireless pressure monitor implanted in the bladder wall of large animals kept working long term and detected bladder compressions with an average correlation of 0.90; the implant site caused problems | 2021 large-animal report, PubMed 34012497 |
| Implanted pressure sensors suffer long-term offset drift from atmospheric changes, moisture in the package, posture, implant shift and tissue overgrowth | Engineering report on a low-power implantable bladder pressure sensor |
| Pressure measured under the bladder lining correlates with bladder pressure but can differ because of forces on the implant (calf study, 6 implants) | Calf study, PubMed Central 5218553 |
| Devices eroded through tissue in ambulatory animal studies, in several placements | Calf and minipig studies |

**Error range found: correlation 0.90 for pressure events, in animals.** No drift rate and no volume error were found.
**Failure modes named:** offset drift; implant shift; tissue overgrowth; erosion; position-dependent readings.
**Important for this project:** these sensors measure **pressure**. In this model pressure is not a fullness indicator (handoff rule 16). An implanted *volume* signal is a different thing, and no figure for one was found.

## 3. Bioimpedance (electrodes on the skin)

| Point | Source (summary only) |
|---|---|
| Body posture and unknown urine conductivity limit continuous impedance monitoring of the bladder | *J Electr Bioimpedance* 2014 (simulation, bench and pig work) |
| Variation in urine conductivity caused a bladder-volume estimation error of up to 200% in earlier work | Reported in a later review of that work |
| A 2024 study with sixteen electrodes and a neural network reported about 1% average volume error, worse when the bladder is small and conductivity is low | 2024 neural-network study |
| Some impedance approaches are described as unsuitable for long-term monitoring because urine conductivity changes with health and diet | 2023 book chapter |

**Error range found: from about 1% (one study, conditions unclear from the summary) to 200% (conductivity not handled).** That spread is the finding: the error depends on whether urine conductivity and posture are controlled.
**Failure modes named:** urine conductivity; posture; movement; small bladder volumes.

## 4. What this means for reading Task 8

- **No source gave an error figure that could stand in for "sensor B".** Task 8's B error levels are therefore a grid, not an estimate of any technology.
- **Independence is the open question for every option.** Posture is named as a failure mode for impedance and for implanted pressure sensors, and posture is also what moves a patch. A skin-mounted second sensor could well share the fault. Task 8 reports that shared-fault case as the failure case.
- **Drift is named for implants.** Task 8 includes a drifting B as a side case.

## 5. Not done

- No full text was read. No primary source was checked for any figure.
- Posture error for impedance was not found as a number.
- Nothing on near-infrared accuracy in people with spinal cord injury was found.
