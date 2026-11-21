"""
Experiment 3b recount: how many settings work, counted three separate ways. Runs no simulation.

  1. the full_loop_works column of exp3b_settings_summary.csv
  2. P1, P2 and P3 worked out again from the run and session tables, ignoring that column
  3. the WORKS labels drawn on the heatmap, counted from the figure itself

Also redraws the figure in memory and compares it with the saved PNG, so count 3 is known to
describe the file on disk. Writes results/task2/exp3b_ceiling40_working.csv.
Usage: python experiments/task2_recount.py
"""
import io
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import task2_experiment3b as t2  # noqa: E402

KEYS = ["stim_name", "sphincter_scaling", "max_duration_s", "threshold_ml", "pressure_ceiling_cmH2O"]


def from_raw_tables():
    """P1, P2, P3 and the invariants, from the frozen criteria and the raw rows only."""
    runs = pd.read_csv(t2.RESULTS / "exp3b_runs.csv")
    sessions = pd.read_csv(t2.RESULTS / "exp3b_sessions.csv")
    inv = ["A2_start_only_after_press_and_alert", "A3_no_start_in_lockout", "A4_sessions_within_max_duration"]
    r = runs.groupby(KEYS).agg(P2=("overflow_despite_alert", lambda x: 1 - x.mean()),
                               invariants=(inv[0], "all"), i3=(inv[1], "all"), i4=(inv[2], "all"))
    s = sessions.groupby(KEYS).agg(P1=("voided_ge_50pct", "mean"), P3=("ceiling_exceeded_gt5", lambda x: 1 - x.mean()))
    t = r.join(s).reset_index()
    t["works"] = (t.P1 >= 0.80) & (t.P2 >= 0.95) & (t.P3 >= 0.95) & t.invariants & t.i3 & t.i4
    return t


def from_figure(summary):
    """Count WORKS labels on the drawn figure, and compare the drawing with the saved PNG."""
    keep_close, t2.plt.close = t2.plt.close, lambda *a: None
    buffer = io.BytesIO()
    t2.plot_map(summary, buffer)
    fig = t2.plt.gcf()
    labels = sum("WORKS" in x.get_text() for ax in fig.axes for x in ax.texts)
    per_panel = [(ax.get_title(), sum("WORKS" in x.get_text() for x in ax.texts)) for ax in fig.axes]
    keep_close(fig)
    t2.plt.close = keep_close
    return labels, per_panel, buffer.getvalue() == (t2.RESULTS / "exp3b_works_map.png").read_bytes()


def main():
    summary = pd.read_csv(t2.RESULTS / "exp3b_settings_summary.csv")
    raw = from_raw_tables()
    merged = summary.merge(raw[KEYS + ["works"]], on=KEYS)
    labels, per_panel, same_png = from_figure(summary)
    print("settings:", len(summary))
    print("1. full_loop_works column:", int(summary.full_loop_works.sum()))
    print("2. recomputed from raw tables:", int(raw.works.sum()),
          "; settings that disagree with the column:", int((merged.works != merged.full_loop_works).sum()))
    print("3. WORKS labels on the figure:", labels, "; redraw identical to saved PNG:", same_png)
    for title, n in per_panel:
        print(f"   {n}  {title}")
    c = ["stim_name", "sphincter_scaling", "max_duration_s", "threshold_ml", "pressure_ceiling_cmH2O",
         "P1_sessions_voided_ge_50pct", "P2_runs_without_overflow_after_alert", "P3_sessions_within_ceiling_plus5",
         "median_residual_ml", "n_sessions"]
    ceiling40 = summary[(summary.pressure_ceiling_cmH2O == 40) & summary.full_loop_works][c]
    ceiling40 = ceiling40.sort_values(["threshold_ml", "sphincter_scaling", "max_duration_s"])
    ceiling40.to_csv(t2.RESULTS / "exp3b_ceiling40_working.csv", index=False)
    print("working settings at ceiling 40:", len(ceiling40))
    print(ceiling40.round(3).to_string(index=False))
    gap = summary[(summary.stim_name == "e0.6_s0.0_5on5off") & (summary.pressure_ceiling_cmH2O == 40) & (summary.threshold_ml == 350)]
    print("drive 0.6, ceiling 40, threshold 350, all six settings:")
    print(gap[c[1:3] + c[5:8] + ["full_loop_works"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
