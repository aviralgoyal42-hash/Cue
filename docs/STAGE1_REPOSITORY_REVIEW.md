# Project Cue: Stage 1 repository inspection and scientific review

Date: 2026-11-03. Status: inspection only. No framework code has been written.

Labels used in this document:
- **[CODE]** means I read it in the upstream source.
- **[PAPER]** means it comes from the peer-reviewed paper.
- **[LIT]** means it comes from other literature that I located and checked.
- **[CALC]** means I worked it out by hand from the code. It still has to be confirmed by running the model in Stage 2.
- **[OPEN]** marks a question that is unresolved and needs a decision or more information.

---

## 1. What was inspected

| Item | Detail |
|---|---|
| Repository | `MoveR-Digital-Health-and-Care-Hub/lower-urinary-tract-sim`, cloned unmodified to `project-cue/third_party/lut-sim` |
| Commit | `bd8f2a072ef017b99dc051b24972333141f7d257` (2025-08-27), tag **v1.3.0**. Earlier tags: v1.0.0 (2024-11-23), v1.1.0, v1.2.0. The repository has 6 commits in total. |
| Licence | MIT, © 2024 MoveR-Digital-Health-and-Care-Hub. Reuse and modification are allowed if the copyright and permission notice are kept. |
| Citation (CITATION.cff) | Cite the software (Lister and McConnell-Trevillion) and the paper. CITATION.cff still points to the **bioRxiv** preprint. Software archive: Zenodo 10.5281/zenodo.16961553 (v1.3.0). |
| Paper (peer reviewed) | Lister E, McConnell-Trevillion A, Jabbari M, Erfanian A, Nazarpour K. *An open-source neurodynamic model of the lower urinary tract.* **R Soc Open Sci** 2025;12(10):242062. doi:10.1098/rsos.242062. PMC12503948. CC BY. |
| Preprint | *An Open-Source Neurodynamic Model of the Bladder.* bioRxiv 2024, doi:10.1101/2024.11.21.624716. The published title is different. Cite the journal version. |
| Supplement (NOT YET READ) | figshare doi:10.6084/m9.figshare.c.8057289. It contains ESM Table S1 (full parameter list and sources) and Table S2 (OAB/BOO changes). **[OPEN]** This must be read before any parameter is labelled SOURCED. |

### Files in the repository

| File | Role |
|---|---|
| `model/LUT_Model.py` (v1.2.0 header, 405 lines) | **The model.** Single class `LUT`. |
| `paper_figures/LUT_Model_OAB.py`, `LUT_Model_BOO.py` | Pathology variants. These are frozen copies of the **v1.1.0** model, not subclasses (see §5). |
| `paper_figures/figures.ipynb` | Reproduces the paper figures. The saved outputs include printed numbers that we can use for Stage 2. |
| `paper_figures/hypotheses.ipynb` | Compares control, OAB and BOO over 3 simulated days. |
| `paper_figures/RealBladderData.mat` | The only experimental dataset: one **rat** cystometry recording (§6). |
| `requirements.txt` | Full pinned Jupyter environment of 120 packages, including macOS-only `appnope` and PyQt6. The model itself needs only numpy, scipy and pandas. |

The README import `from model import LUT_Model as model` is correct. `model/` has no `__init__.py`, so the import works as a namespace package when the repository root is on `sys.path`.

---

## 2. How the model works [CODE] (paper equations 2.1–2.15)

### 2.1 State, inputs and outputs

All internal values are in **SI units**: volume in m³, flow in m³/s, pressure in Pa, length in m and time in s.

| Symbol (code) | Meaning | Kind |
|---|---|---|
| `V_B` | Bladder volume | State |
| `f_aD_s` (f\*aD) | Normalised detrusor activation, 0–1 | State |
| `f_aS_s` (f\*aS) | Normalised sphincter activation, 0–1 | State |
| `r_U` | Urethral radius. Solved algebraically at each step by bisection. | Algebraic |
| `Q` | Outflow (voiding or leak) | Algebraic |
| `Q_in` | Urine inflow from the kidney model | Input |
| `p_D` | Detrusor pressure. No abdominal pressure term exists, so this is effectively p_det. | Output |
| `p_S` | Sphincter (urethral closure) pressure | Output |
| `w_e_s` ω\*e | Excitatory detrusor drive. "Pelvic nerve", i.e. parasympathetic. | Neural input, 0–1 |
| `w_i_s` ω\*i | Inhibitory detrusor drive. "Hypogastric nerve", i.e. sympathetic. | Neural input, 0–1 |
| `w_s_s` ω\*s | Excitatory sphincter drive. "Pudendal nerve", i.e. somatic. | Neural input, 0–1 |
| `voiding` | Boolean voiding state | Discrete state |

`process_neural_input(maxTime, dT, noise=1, V_unit='m^3', p_unit='Pa', verbose=False, seed=None, trigger_metric='pressure')` returns a pandas DataFrame. It has one row per step and these columns: `t, V_B, f_aD_s, f_aS_s, r_U, Q, p_D, p_S, Q_in, w_e_s, w_i_s, w_s_s, voiding`.

### 2.2 The simulation loop (one fixed step `dT`, forward Euler)

```
for each t in arange(0, maxTime, dT):
  1. voiding = is_voiding()               # discrete switch (see 2.4)
  2. ω*e, ω*i, ω*s = update_*_input()      # neural drive from current V_B, r_U, voiding
  3. f*aD += dT·(ω*e − f*aD − ω*i·f*aD)/τ_D    # τ_D = 1.0 s
     f*aS += dT·(ω*s − f*aS)/τ_S               # τ_S = 0.2 s
  4. Q_in  = get_Qin(t)                     # kidney
  5. V_B  += dT·(Q_in − Q);  V_B clipped to [0, max_V_B]      # p_D updated here
  6. r_U   = bisection root of (p_T − p_S) on [0, 5 mm]; if no root → r_U = 0 (closed)
  7. Q     = flow through the urethra given p_S and r_U
```

In plain language:
- Each neural input is a number between 0 and 1. Each one pulls its muscle's activation towards itself. The detrusor follows in about 1 s and the sphincter in about 0.2 s.
- Sympathetic drive (ω\*i) does not subtract from the detrusor. It **divides** it. The steady state is f\*aD = ω\*e / (1 + ω\*i).
- The volume changes by inflow minus outflow.
- At every step the code finds the urethral radius at which the pressure pushing urine out equals the sphincter's closing pressure. If no such radius exists, the urethra stays shut.

Mechanics (detrusor wall stress, sphincter tube, flow equation 2.9) follow **Bastiaanssen et al. 1996**, *J Theor Biol* 178:113–133 [PAPER]. The paper does not name a source for the activation equation or for τ_D and τ_S [PAPER].

### 2.3 Neural input model (the "brain" in this model)

The paper calls these Gaussian functions "neural inputs from the brain" [PAPER]. While the model is not voiding:
- ω\*e = 0.8·exp(−(F−1.0)²/(2·0.1²)) + 0.04 + 0.15·F, where F = V_B / max_V_B is the fullness.
- ω\*i = 0.6·exp(−(F−0.8)²/(2·0.08²)) + 0.1
- ω\*s = 0.5·(1 − exp(−(openness−1)²/(2·0.1²))), where openness = r_U / 5 mm.

During voiding the inputs are fixed constants: ω\*e = 0.6, ω\*i = 0, ω\*s = 0.1. All three are clipped to [0, 1].

The neural parameters (`neural_args`) and kidney parameters (`kidney_args`) are described as "novel". The paper says they "lack empirically defined physiological ranges" [PAPER]. It does not say whether they were fitted, tuned by hand, or taken from literature. They appear to be tuned by hand.

### 2.4 How voiding is decided (`is_voiding`)

- Voiding **starts** if `p_D ≥ 5366.9 Pa` (≈ 54.7 cmH₂O, the default `trigger_metric='pressure'`) **or** if `V_B ≥ max_V_B` (500 mL).
- Voiding **stops** only when `V_B < 1e-8 m³` (0.01 mL).
- The paper describes a volume threshold V_void. It gives no value or source for the 5366.9 Pa threshold or for the 500 mL limit [PAPER].

### 2.5 Kidney (urine production)

Q_in = max(0, [0.00625·sin(2π(t_h − 8)/24) + 0.017] mL/s × 10⁻⁶ + n·5×10⁻⁸ m³/s), where t_h is time in hours. A new value of n ~ U(−noise, +noise) is drawn whenever `t % 60 == 0`.

- The mean of 0.017 mL/s (about 1 mL/min) matches the paper's "healthy mean" [PAPER]. The paper cites references for 0.3 mL/min (lower bound) and 1 mL/min (mean).
- **Code and paper disagree [CODE vs PAPER].** The paper says the noise *multiplies* the sine output. The code *adds* n × 0.05 mL/s. With noise = 1, that added term can be up to three times the mean inflow.
- Because negative inflow is set to zero, the noise also raises the average. [CALC] With noise = 1 the expected inflow is about 0.022 mL/s, not 0.017 mL/s. This has to be checked in Stage 2.

### 2.6 Units and API pitfalls (relevant to the user's §9)

- Unit conversion happens only on output. It only recognises the exact strings `V_unit='ml'` and `p_unit='cmH2O'`. Any other spelling, such as `'mL'`, is **silently ignored** and the values stay in m³ or Pa. Our framework will always request SI and convert explicitly.
- Pressure conversion: 1 cmH₂O = 98.0665 Pa (the code uses 0.0101971621 cmH₂O per Pa).
- There is no initial-volume argument. Initial conditions are set by assigning attributes, e.g. `LUT.V_B = 1e-4` for 100 mL, before running.
- Calling `process_neural_input` a second time continues the old state but restarts `t` at 0, which resets the circadian phase. Figure 4 in the notebook relies on this behaviour.
- Randomness uses numpy's **global legacy RNG** (`np.random.seed`, `np.random.uniform`). If the sensor or user model used the same global RNG, it would change the physiology's random stream. Our modules must use separate `np.random.Generator` objects.
- The inflow noise is redrawn only when `t % 60 == 0` holds exactly in floating point. This works for dT = 0.1. For a dT that does not divide 60 exactly, the noise may be drawn only once.
- `p_theta` is defined but never used. `C_p` is used only if `tissue_pressed_in_BN` is True (default False).
- There is no per-step callback, and no argument for external neural input.

---

## 3. Can the library accept external neural input? (needed for the user's §F)

**Yes, but only by subclassing.** The paper says the model can "integrate external neural inputs" [PAPER]. In practice this means replacing the normalised ω values. There is no stimulus waveform, input interface, or stimulation model [PAPER].

The clean mechanism [CODE]: subclass `LUT` and override `update_parasympathetic_input`, `update_sympathetic_input`, `update_somatic_input` and `is_voiding`. All four are called once per step inside the **unmodified** `process_neural_input` loop. `is_voiding()` runs first in each step, so it can serve as the per-step hook. In that hook the rig would:
1. let the sensor take a reading,
2. let the device and safety controller update,
3. set the stimulation drive for the step.

The physics loop itself stays the original upstream code.

The alternative is to write our own step loop that calls the model's methods. That gives more control but duplicates upstream logic. Either way, Stage 2 needs a **regression test**: with all Cue hooks inactive, the subclass must reproduce the upstream output bit-for-bit with the same seed.

What stimulation could look like in this model: bursts of extra ω\*e (detrusor) and ω\*s (sphincter) drive. Sacral anterior roots carry both kinds of fibre, so both would be driven together. The model has a fast sphincter and a slow detrusor (τ_S = 0.2 s, τ_D = 1 s). The clinical idea of "post-stimulus voiding" relies on exactly that difference: the striated sphincter relaxes faster than the detrusor between bursts [LIT, reviews; primary source still to be obtained in Stage 5]. So the model *could* show sphincter–detrusor competition during bursts and flow in the gaps. **Whether it actually does is a Stage 5 result, not something to assume.**

Limits that must be stated:
- Nothing links electrical stimulation parameters (amplitude, frequency, pulse width) to ω. Any stimulus therefore stays in **dimensionless normalised drive** and is labelled hypothetical. We will not suggest clinical parameters.
- In the clinical device (Brindley-type sacral anterior root stimulation), stimulation is usually combined with dorsal rhizotomy to stop reflex overactivity, and the voiding it produces is high-pressure and intermittent [LIT, reviews]. Cue's concept does not include a rhizotomy. That is a scientific gap to state in the validation document.
- **Do not reuse the built-in voiding switch for Cue.** Once voiding starts, it holds the voiding drive until the bladder is under 0.01 mL. Complete emptying is therefore **built in by construction**, and the paper reports voided volume equal to capacity: baseline 489.56 mL voided out of 489.56 mL. The model does **not** represent post-void residual [PAPER: not stated]. Any residual volume Cue reports must come from the mechanics stopping flow (the sphincter closing or the cutoff firing). It must never come from this switch.

---

## 4. SCI condition: what the model can and cannot represent

### 4.1 What exists

- The paper says there are **no** afferent (sensory) pathways, **no** spinal reflexes and **no** PAG or PMC circuits. It calls the neural part "primarily a neural regulator system", not a simulation of central nervous system pathways [PAPER].
- The feedback that exists is algebraic. Fullness and urethral openness are fed straight into the drive functions.
- The model therefore cannot separate "sensation reaching the brain" from "the sacral reflex arc". Both are folded into the same Gaussian functions plus the `is_voiding` decision.

### 4.2 Proposed mapping for the simplified condition (to be decided before Stage 3) [OPEN]

| Pathway in the user's specification | Closest element in the model | Proposed SCI setting |
|---|---|---|
| Sensation to brain → deciding to void | `is_voiding()` pressure trigger | **Disabled.** No voluntary or supraspinal voiding. |
| Descending coordinated voiding program (PMC): detrusor on, sphincter relaxed | Voiding-phase constants (ω\*e 0.6, ω\*i 0, ω\*s 0.1) | **Disabled.** There is no coordinated sphincter relaxation. |
| Forced void at 500 mL | `is_voiding()` volume trigger | **Disabled.** It would silently empty the bladder to 0, which is not an SCI behaviour. |
| Storage-phase drives that depend on volume (ω\*e, ω\*i, ω\*s Gaussians) | `update_*_input` while not voiding | **Decision needed.** (a) Keep them as a stand-in for the intact sacral and thoracolumbar reflexes below the injury. (b) Replace them with configurable injury-level profiles. Either way this is an assumption. The paper calls them signals from the brain. |
| Bladder and sphincter mechanics, kidney, filling | Mechanics, `get_Qin` | Unchanged. |

### 4.3 Structural problems to solve in Stage 3

1. **The 500 mL hard clamp.** `V_B` is clipped at `max_V_B`. Without voiding, the volume would sit at exactly 500 mL and hide any over-distension. `max_V_B` has three separate jobs: the clamp, the forced-void threshold, and the fullness normalisation inside the neural Gaussians. Raising it changes the neural behaviour too. **[OPEN]** We need an override that separates these roles and is labelled ASSUMED.
2. **Leakage may emerge from the mechanics alone.** At the default storage drive (ω\*s ≈ 0.5), [CALC] the sphincter closure pressure is about 5.8 kPa (≈ 59 cmH₂O). This is just above the 54.7 cmH₂O void trigger. With voiding disabled, the detrusor pressure may exceed the closure pressure near full and open the urethra. That would be a model-predicted "reflex leak". Stage 3 must report this as a **model prediction**, not a confirmed SCI behaviour.
3. **Detrusor overactivity (DO).** The model has no involuntary phasic contractions. The OAB variant is a *tonic* increase in parasympathetic drive with less sympathetic inhibition. It produces earlier voiding, not phasic DO. **The library cannot show neurogenic DO as it stands.** We could add a labelled, hypothetical phasic-contraction term to ω\*e, but it would not be validated.
4. **Detrusor-sphincter dyssynergia (DSD).** This is **not modelled and not mentioned** in the paper [PAPER]. The mechanics *can* express a sphincter fighting the detrusor, because p_S competes with p_T when solving for r_U. DSD could therefore be approximated by keeping ω\*s high while ω\*e is high. That would be our assumption and not validated. SCI literature describes DSD as the bladder and sphincter contracting at the same time, which makes emptying inefficient [LIT: de Groat & Yoshimura 2012, *Exp Neurol* 235:123–132, PMC3580860].
5. **The time course after injury** (an initial areflexic phase, then emergence of a spinal micturition reflex) [LIT, same review] is not represented. We will label the condition as **one simplified, chronic, suprasacral-like scenario** with a configurable injury level. It is not a universal SCI model.

### 4.4 Alternatives that do represent SCI or spinal circuits (for reference only)

- **Fardadi M, Leiter JC, Lu DC, Iwasaki T.** 2024. *PLoS Comput Biol* 20(7):e1012237, doi:10.1371/journal.pcbi.1012237. A Hodgkin–Huxley micturition circuit that reproduces DSD after **human** SCI and models transcutaneous magnetic spinal stimulation. It is closer to the SCI question, but it is a heavier and different model. I have not checked its code or licence.
- **TibialModulationSim** (github.com/Aidan-MT/TibialModulationSim). A Brian2 spiking network with PAG, PMC and spinal afferent and efferent populations, coupled to an adapted version of this LUT model. It accompanies an eLife paper on tibial neuromodulation in humans. My clone of it failed because of Windows path length (§9), so I have read only its README.

My recommendation: stay with the user's chosen model, which is simple and can be defended. Cite these two models in the validation document as the routes to a mechanistic SCI reflex model in future work.

---

## 5. Existing pathology models [CODE + PAPER]

| Variant | How implemented | Reported result (paper and notebook) |
|---|---|---|
| OAB | Different Gaussian parameters: ω\*e peak 1.2 at F = 0.8; ω\*i peak 0.4 at F = 0.9; voiding ω\*e 0.8, ω\*s 0.05. Described as "detrusor hypersensitivity". | Intervoid interval −31.04% (≈5.9 h → 4.1 h). Capacity 489.58 → 334.89 mL. |
| BOO | Urethral resistances R₁ and R₂ multiplied by 5 | Maximum flow 21.11 → 12.31 mL/s (−41.71%) |

**Caveat:** both variant files are **v1.1.0 copies**. Their somatic input uses the raw `r_U` in metres instead of the normalised openness, so their sphincter feedback is effectively a constant. The current core model normalises it. The pathology results therefore come from a slightly different model than the current one. They also add unused keys (`neuron_threshold`, `filling_phase_*`).

---

## 6. Validation evidence in the original work

| Evidence | What it is | Strength |
|---|---|---|
| Rat cystometry | One recording in `RealBladderData.mat`, about 300 s long, with one void. Variables: pressure, infused, residual and voided volume, leakage, time vectors. The source animals are adult **male Wistar rats**, data from Jabbari & Erfanian 2019 (*Sci Rep* 9:18128), with ethics approval from Iran University of Science and Technology [PAPER]. **Units are not documented in the file.** The time vectors step every 0.05 s (20 Hz), but the stored "sampling rate" fields say 5 Hz and 50 Hz. | **Animal, qualitative.** Only the first filling phase is used. In Figure 2/3 both axes are min-max scaled to the model's range for display. The quantitative result is a Pearson r = 0.93 on the pressure/volume ratio. The paper is inconsistent about whether this used scaled data. Number of animals, anaesthesia and infusion rate are not stated. |
| Human literature comparisons | Cystometrogram *shape* (phases I–IV) compared with a textbook curve. Compliance above 40 mL/cmH₂O. Daytime intervoid interval of 5–7 h. Voiding duration 21 ± 13 s (model 27.3 s). Urine production 0.3–10 mL/min, mean 1 mL/min. | **Literature ranges and qualitative only.** The model has not been fitted to human patient data. The authors state that direct clinical validation is limited [PAPER]. |
| Sensitivity and noise analysis | ±5% and ±25% sweeps of the kidney and neural parameters, and noise levels 0–1 | Robustness, not validation. Reducing `somatic_a` by 15% or more stops voiding altogether [PAPER]. |

Summary for our validation document:
- The mechanics come from an established 1996 model.
- The neural and kidney layers are new and hand-set.
- The only experimental data are from rats, and the comparison is shape-level.
- **Nothing in the original work validates SCI behaviour, stimulation or residual volume.**
- [OPEN] The species basis of the mechanical parameters is not stated in the main text. Check ESM Table S1 and Bastiaanssen 1996.

---

## 7. Ultrasound sensing literature (for the user's §C)

| Source | What it gives us |
|---|---|
| **Toymus AT et al. 2024**, *Nat Commun* 15:7216, doi:10.1038/s41467-024-50397-8 (PMC11341558). This is the published form of arXiv 2310.09448. | Four flexible 2 MHz A-mode transducers record the times of the front and back bladder-wall echoes. Volume comes from a least-squares **sphere fit**, assuming 1480 m/s speed of sound. Tests: flasks (n = 10, mean relative error **14.85%**) and **5 healthy volunteers, supine only**, BMI 18–23.7, 84 (or 100)–800 mL. In vivo mean relative error **11.17%** (the error definition is not given) and R² 99.5%. The reference was B-mode ultrasound with the 0.52 ellipsoid formula, not catheterisation. A minimum number of echoes is needed. The paper states 4 in one place and 5 in another. Placement was guided manually. Data are in the Koç University repository (access not yet verified), source data come with the paper, and code is at Zenodo 10.5281/zenodo.11370303. |
| **Kim S, Kim A. 2026**, *Int Neurourol J* 30(2):95–104, doi:10.5213/inj.2652030.015 (review) | States that there are **no prospective validation studies of wearable bladder ultrasound in adults with SCI**. First-generation A-mode wearables mostly track fullness trends and give threshold alerts. DFree in 40 children with neurogenic bladder (Cai et al. 2025, *Neurourol Urodyn* 44:1188–92): accuracy 46%, sensitivity 70%, specificity 13%. SENS-U in children with functional voiding dysfunction: 90% sensitivity for "full bladder" (van Leuteren et al. 2018, *J Pediatr Urol*). These figures are as reported by the review. I have not yet checked them against the primary papers. |

**Conclusions for the sensor module:**
- No validated ultrasound model and no SCI dataset exist that we could use. The sensor must be labelled a **synthetic experimental proxy**.
- Its noise, bias, dropout, delay and posture or misalignment effects will be **scenario parameters marked ASSUMED**.
- We may show the published healthy-volunteer figure (about 11% mean relative error, supine, 5 people) as **one labelled reference scenario**. It must never be presented as SCI accuracy.
- The published failure modes give us realistic *kinds* of fault, without inventing magnitudes: too few echoes leading to no reading, operator-dependent placement, a fixed speed-of-sound assumption, a shape assumption (sphere versus real bladder), and only one posture tested.
- The 0.52 ellipsoid coefficient belongs to the B-mode reference method, not to the wearable device.

---

## 8. Reproduction targets for Stage 2 (from saved notebook outputs)

1. **Figure 2 run**: 1 day, dT = 0.1, seed = 42, output in mL and cmH₂O.
   - Row 0: f_aD 0.004000, f_aS 0.250000, p_D 0.178035, p_S 30.051363, Q_in 0.
   - Last row (t = 86399.9 s): V_B 484.591634 mL, f_aD 0.814422, p_D 53.065679, ω\*e 0.948264, ω\*i 0.164130.
   - This takes 864,000 steps. Runtime is unknown until we have Python.
2. **Sensitivity baseline**: 5 days, seed 42. Mean intervoid interval 6.04 h, mean peak capacity 489.56 mL, mean voided volume 489.56 mL.
3. **Hypotheses**: 3 days, seed 42. Control intervoid interval 21,360.90 s, capacity 489.58 mL, peak flow 21.11 mL/s. This is the slowest run, so it is optional.

An exact match is possible only if numpy's legacy Mersenne Twister stream is unchanged, which it normally is between versions.

---

## 9. Environment blockers found

1. **Python was not installed.** This is now resolved (2026-11-03). Python 3.12.10 was installed with winget for the current user. A virtual environment at `%USERPROFILE%\.venvs\project-cue` holds the upstream pins numpy 2.3.1, scipy 1.15.2, pandas 2.2.3 and matplotlib 3.10.0, plus pytest. It lives outside the project folder because of the path-length limit. `from model import LUT_Model` imports cleanly. A minimal `requirements.txt` will replace the upstream 120-package Jupyter environment.
2. **Windows path length.** Long paths are turned off in Windows (`LongPathsEnabled = 0`). The folder the app made for this session is already 181 characters deep, and the longest upstream file path is already 246 of the 260 allowed. Git needed `core.longpaths`, and the second repository clone failed. Moving the project to a short folder such as `C:\cue` avoids this. I did not change any Windows setting.
3. The partial second clone was removed. The upstream clone has no local changes (`git status` is clean).

---

## 10. Open decisions before Stage 3 and 5 (missing scientific information)

1. **SCI storage reflexes** (§4.2): keep the upstream Gaussian drives as the stand-in for intact reflexes, or use configurable injury-level profiles?
2. **Volume clamp** (§4.3.1): what SCI capacity limit to use? No sourced value has been found yet. It would be ASSUMED.
3. **Pressure-ceiling cutoff source.** Cue's only sensor is an ultrasound volume patch. A pressure ceiling needs a pressure signal. The options are:
   - (a) a hypothetical implanted pressure sensor, labelled synthetic;
   - (b) treating model pressure as an idealised "oracle" safety channel, clearly labelled as such;
   - (c) dropping the pressure ceiling in favour of the time and volume cutoffs.
   The time cutoff is the only one that does not depend on any sensor.
4. **ESM Table S1** must be read to label each mechanical parameter SOURCED, with the primary reference and species.
5. **Primary sources** still needed for the stimulation background (Brindley-type sacral anterior root stimulation) and for the DFree and SENS-U figures, before they go into the validation document.

## Sources consulted

- Upstream code: https://github.com/MoveR-Digital-Health-and-Care-Hub/lower-urinary-tract-sim (v1.3.0)
- Lister et al. 2025, R Soc Open Sci: https://pmc.ncbi.nlm.nih.gov/articles/PMC12503948/ and the preprint https://www.biorxiv.org/content/10.1101/2024.11.21.624716v1.full
- Toymus et al. 2024, Nat Commun: https://pmc.ncbi.nlm.nih.gov/articles/PMC11341558/ and arXiv https://arxiv.org/abs/2310.09448
- Kim & Kim 2026, Int Neurourol J: https://doi.org/10.5213/inj.2652030.015
- de Groat & Yoshimura 2012, Exp Neurol: https://pmc.ncbi.nlm.nih.gov/articles/PMC3580860
- Fardadi et al. 2024, PLoS Comput Biol: https://doi.org/10.1371/journal.pcbi.1012237
- TibialModulationSim README: https://github.com/Aidan-MT/TibialModulationSim
- Background on sacral anterior root stimulation (reviews only, primary source pending): https://en.wikipedia.org/wiki/Sacral_anterior_root_stimulator
