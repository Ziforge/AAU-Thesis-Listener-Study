#!/usr/bin/env python3
"""Analyse listener-study brand-identification responses.

Inputs (downloaded as CSV from the Google Sheet):
  analysis/responses.csv     — one row per (participant, trial) classification
  analysis/participants.csv  — one row per participant with metadata

Outputs:
  - summary.json              — numbers ready for the thesis
  - confusion_matrix.pdf      — true-system × listener-choice heatmap
  - per_system_accuracy.pdf   — bar chart of identification accuracy per system
  - results.txt               — per-system stats + Krippendorff alpha
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
RESP_CSV = HERE / "responses.csv"
PART_CSV = HERE / "participants.csv"

SYSTEM_ORDER = ["buchla_200", "serge", "ems_vcs3", "soundfreak"]
ALL_CHOICES = SYSTEM_ORDER + ["unknown", "modern"]
SYS_LABELS = {
    "buchla_200": "Buchla 200",
    "serge":      "Serge",
    "ems_vcs3":   "EMS / VCS3",
    "soundfreak": "Soundfreak",
    "unknown":    "Don't know",
    "modern":     "Modern/digital",
}


def krippendorff_alpha_nominal(rater_data):
    """Krippendorff's alpha for nominal data (categorical classification).
    rater_data: {rater_id: {item_id: category}}.
    Standard Krippendorff formula for nominal coincidences."""
    raters = sorted(rater_data.keys())
    items = sorted({i for r in raters for i in rater_data[r].keys()})
    if len(items) < 2 or len(raters) < 2: return float("nan")

    # Build coincidence matrix from per-item ratings
    categories = sorted({c for r in raters for c in rater_data[r].values()})
    cat_idx = {c: i for i, c in enumerate(categories)}
    K = len(categories)
    coinc = np.zeros((K, K))
    for it in items:
        ratings_for_item = [rater_data[r][it] for r in raters if it in rater_data[r]]
        n = len(ratings_for_item)
        if n < 2: continue
        for c1 in ratings_for_item:
            for c2 in ratings_for_item:
                if c1 == c2:  # diagonal: paired with itself
                    coinc[cat_idx[c1], cat_idx[c2]] += (1 / (n - 1))  # exclude self-pair
                    # Actually standard approach: count each ordered pair excluding self
                    # Here we'll use the simpler Krippendorff formula
        # Proper: increment coinc[c1, c2] by 1/(n-1) for each ordered pair where c1 != c2,
        # AND for c1 == c2 also (this is the "coincidence" definition)
    # Simpler implementation: per-item observed/expected disagreement
    # Observed disagreement
    Do = 0.0; total_pairs = 0
    for it in items:
        ratings = [rater_data[r][it] for r in raters if it in rater_data[r]]
        n = len(ratings)
        if n < 2: continue
        for i in range(n):
            for j in range(n):
                if i == j: continue
                Do += (1 if ratings[i] != ratings[j] else 0)
        total_pairs += n * (n - 1)
    if total_pairs == 0: return float("nan")
    Do /= total_pairs

    # Expected disagreement (random pairing of all values)
    all_vals = [v for r in raters for v in rater_data[r].values()]
    De = 0.0
    n_all_pairs = len(all_vals) * (len(all_vals) - 1)
    if n_all_pairs == 0: return float("nan")
    for i in range(len(all_vals)):
        for j in range(len(all_vals)):
            if i == j: continue
            De += (1 if all_vals[i] != all_vals[j] else 0)
    De /= n_all_pairs

    return 1.0 - (Do / De) if De > 0 else float("nan")


def main():
    if not RESP_CSV.exists() or not PART_CSV.exists():
        print(f"Missing CSV files. Expected:\n  {RESP_CSV}\n  {PART_CSV}")
        print("Download both tabs from the Google Sheet as CSV.")
        return 1

    parts = pd.read_csv(PART_CSV)
    resp = pd.read_csv(RESP_CSV)
    n_part = len(parts)
    n_resp = len(resp)
    print(f"Participants: {n_part}\nTotal responses: {n_resp}\n")

    # === PLACEBO / ATTENTION CHECKS ===
    print("=== Attention checks (placebo + repeat-consistency) ===")
    # Modern-digital placebo: ground truth is 'placebo_modern'; correct response = 'modern'
    placebo = resp[resp["true_system"] == "placebo_modern"]
    if len(placebo) > 0:
        placebo_correct = (placebo["listener_choice"] == "modern").sum()
        placebo_uncertain = (placebo["listener_choice"] == "unknown").sum()
        placebo_misclass_vintage = ((placebo["listener_choice"] != "modern") &
                                     (placebo["listener_choice"] != "unknown")).sum()
        n = len(placebo)
        print(f"  Modern-digital placebos: n={n}")
        print(f"    correctly identified as 'modern':     {placebo_correct} ({placebo_correct/n*100:.1f}%)")
        print(f"    marked 'unknown':                      {placebo_uncertain} ({placebo_uncertain/n*100:.1f}%)")
        print(f"    misclassified as vintage modular:      {placebo_misclass_vintage} ({placebo_misclass_vintage/n*100:.1f}%)")
        placebo_pass_rate = (placebo_correct + placebo_uncertain) / n
        if placebo_pass_rate < 0.7:
            print(f"    WARNING: only {placebo_pass_rate*100:.0f}% of placebos pass — listener pool may be inattentive")
        else:
            print(f"    pass rate: {placebo_pass_rate*100:.1f}% (good attention)")

    # Repeat-consistency: same stimulus_id appearing in 2 trials per participant — do they
    # answer the same?
    print("\n  Repeat-consistency (same stimulus presented twice):")
    consistent = 0; total_consist = 0
    for pid, g in resp.groupby("participant_id"):
        # Find stimulus_ids that appear ≥2 times in this participant's responses
        dup = g.groupby("stimulus_id").filter(lambda x: len(x) >= 2)
        for sid, sg in dup.groupby("stimulus_id"):
            if len(sg) < 2: continue
            choices = sg["listener_choice"].tolist()
            if len(set(choices)) == 1: consistent += 1
            total_consist += 1
    if total_consist > 0:
        consistency_rate = consistent / total_consist
        print(f"    consistent answers: {consistent}/{total_consist} = {consistency_rate*100:.1f}%")
        if consistency_rate < 0.5:
            print(f"    WARNING: only {consistency_rate*100:.0f}% consistency — random responses likely")

    peer_summary = None  # peer-distance removed by design — measured by metric chain (J=1.33)

    # Filter out placebo + repeat trials for main analysis (per-system accuracy)
    main_resp = resp[resp["true_system"] != "placebo_modern"]
    print("\n=== Per-system identification accuracy (main trials only) ===")
    by_sys = main_resp.groupby("true_system")
    sys_results = {}
    for sys, g in by_sys:
        total = len(g)
        correct = int((g["listener_choice"] == sys).sum())
        unknown = int((g["listener_choice"] == "unknown").sum())
        modern = int((g["listener_choice"] == "modern").sum())
        wrong_other_sys = total - correct - unknown - modern
        accuracy = correct / total if total > 0 else 0
        sys_results[sys] = {
            "n_trials": total, "correct": correct, "wrong_other_system": wrong_other_sys,
            "unknown": unknown, "modern": modern, "accuracy": float(accuracy)
        }
        print(f"  {SYS_LABELS.get(sys, sys):<14} n={total:>3}  "
              f"correct={correct:>3} ({accuracy*100:.1f}%)  "
              f"wrong-sys={wrong_other_sys:>3}  unknown={unknown:>3}  modern={modern:>3}")

    # Per-confidence-bin accuracy
    print("\n=== Accuracy stratified by confidence ===")
    for conf in [1, 2, 3, 4, 5]:
        g = resp[resp["confidence"] == conf]
        if len(g) == 0: continue
        acc = float((g["listener_choice"] == g["true_system"]).mean())
        print(f"  conf {conf}: n={len(g):>3}  accuracy={acc*100:.1f}%")

    # Per-experience-stratum accuracy
    print("\n=== Accuracy stratified by experience ===")
    merged = resp.merge(parts[["participant_id", "experience", "familiarity"]],
                         on="participant_id", how="left")
    for exp, g in merged.groupby("experience"):
        if len(g) == 0: continue
        acc = float((g["listener_choice"] == g["true_system"]).mean())
        print(f"  {exp:<14} n={len(g):>3}  accuracy={acc*100:.1f}%")

    # Confusion matrix
    print("\n=== Building confusion matrix ===")
    cm = np.zeros((len(SYSTEM_ORDER), len(ALL_CHOICES)), dtype=int)
    for _, row in resp.iterrows():
        if row["true_system"] not in SYSTEM_ORDER: continue
        if row["listener_choice"] not in ALL_CHOICES: continue
        i = SYSTEM_ORDER.index(row["true_system"])
        j = ALL_CHOICES.index(row["listener_choice"])
        cm[i, j] += 1
    cm_norm = cm / cm.sum(axis=1, keepdims=True).clip(min=1)

    fig, ax = plt.subplots(figsize=(9, 5))
    im = ax.imshow(cm_norm, cmap="YlOrBr", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(ALL_CHOICES)))
    ax.set_xticklabels([SYS_LABELS[c] for c in ALL_CHOICES], rotation=20, ha="right")
    ax.set_yticks(range(len(SYSTEM_ORDER)))
    ax.set_yticklabels([SYS_LABELS[s] for s in SYSTEM_ORDER])
    ax.set_xlabel("Listener choice")
    ax.set_ylabel("True system")
    ax.set_title("Brand-identification confusion matrix (rows normalised)")
    for i in range(len(SYSTEM_ORDER)):
        for j in range(len(ALL_CHOICES)):
            txt = f"{cm[i,j]}\n({cm_norm[i,j]*100:.0f}%)"
            ax.text(j, i, txt, ha="center", va="center",
                    fontsize=9, color="black" if cm_norm[i,j] < 0.5 else "white")
    fig.colorbar(im, ax=ax, label="Proportion")
    plt.tight_layout()
    plt.savefig(HERE / "confusion_matrix.pdf", format="pdf", bbox_inches="tight")
    print(f"wrote {HERE/'confusion_matrix.pdf'}")

    # Per-system accuracy bar chart
    fig, ax = plt.subplots(figsize=(7, 4))
    systems = list(sys_results.keys())
    accuracies = [sys_results[s]["accuracy"] for s in systems]
    ns = [sys_results[s]["n_trials"] for s in systems]
    chance = 1.0 / 4  # 4 system options (excluding unknown/modern)
    bars = ax.bar(range(len(systems)),
                  [a*100 for a in accuracies],
                  color=["#1f77b4", "#ff7f0e", "#2ca02c", "#9467bd"][:len(systems)])
    for bar, n, a in zip(bars, ns, accuracies):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height()+1,
                f"n={n}\n{a*100:.1f}%", ha="center", va="bottom", fontsize=9)
    ax.axhline(chance*100, color="grey", linestyle="--", alpha=0.6,
               label=f"Chance (1/4 systems = {chance*100:.0f}%)")
    ax.set_xticks(range(len(systems)))
    ax.set_xticklabels([SYS_LABELS[s] for s in systems], rotation=10, ha="right")
    ax.set_ylabel("Identification accuracy (%)")
    ax.set_title("Per-system brand-identification accuracy")
    ax.set_ylim(0, 100)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(HERE / "per_system_accuracy.pdf", format="pdf", bbox_inches="tight")
    print(f"wrote {HERE/'per_system_accuracy.pdf'}")

    # Inter-rater agreement (Krippendorff alpha for nominal data)
    rater_data = {}
    for pid, g in resp.groupby("participant_id"):
        rater_data[pid] = {row["stimulus_id"]: row["listener_choice"] for _, row in g.iterrows()}
    if len(rater_data) >= 3:
        alpha = krippendorff_alpha_nominal(rater_data)
        print(f"\n=== Inter-rater agreement (Krippendorff alpha, nominal) ===")
        print(f"α = {alpha:.3f}  ({'>0.667 acceptable, >0.8 strong' if alpha == alpha else 'computation failed'})")
    else:
        alpha = float("nan")

    # Save summary
    # Compute placebo + consistency for summary
    placebo_pass = float((placebo_correct + placebo_uncertain) / len(placebo)) if len(placebo) > 0 else None
    consistency_rate_val = float(consistent / total_consist) if total_consist > 0 else None
    summary = {
        "n_participants": int(n_part),
        "n_total_responses": int(n_resp),
        "experience_distribution": parts["experience"].value_counts().to_dict() if "experience" in parts.columns else {},
        "familiarity_distribution": parts["familiarity"].value_counts().to_dict() if "familiarity" in parts.columns else {},
        "device_distribution": parts["listening_device"].value_counts().to_dict() if "listening_device" in parts.columns else {},
        "attention_checks": {
            "placebo_modern_pass_rate": placebo_pass,
            "repeat_consistency_rate": consistency_rate_val,
        },
        "peer_distance": peer_summary,
        "per_system_accuracy": sys_results,
        "overall_accuracy_main_trials": float((main_resp["listener_choice"] == main_resp["true_system"]).mean()) if len(main_resp) > 0 else None,
        "krippendorff_alpha_nominal": float(alpha) if alpha == alpha else None,
        "chance_baseline": chance,
    }
    (HERE / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\nwrote {HERE/'summary.json'}")
    print(f"\nOverall identification accuracy: {summary['overall_accuracy']*100:.1f}%")
    print(f"Chance baseline (random over 4 systems): {chance*100:.0f}%")


if __name__ == "__main__":
    raise SystemExit(main())
