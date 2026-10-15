"""Entity Resolution Benchmark and Threshold Evaluation (PRD FR-1.4, Milestone M3)."""

import json
import logging
from pathlib import Path
from typing import Any

from kgrag.config import get_settings
from kgrag.resolve.candidates import token_similarity
from kgrag.resolve.normalizer import normalize_company_name

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def evaluate_pair(
    surface_a: str,
    surface_b: str,
    entity_type: str = "Company",
    auto_thresh: float = 0.85,
    review_thresh: float = 0.70,
) -> tuple[float, str, str]:
    """Evaluate pairwise similarity and resolution decision between two surface forms."""
    norm_a = normalize_company_name(surface_a) if entity_type == "Company" else surface_a.strip()
    norm_b = normalize_company_name(surface_b) if entity_type == "Company" else surface_b.strip()

    # 1. Exact match on canonical form
    if norm_a.lower() == norm_b.lower():
        return 1.0, "exact_match", "auto_merged"

    # 2. Token & char 3-gram similarity
    score = token_similarity(norm_a, norm_b)
    if score >= auto_thresh:
        return round(score, 4), "token_jaccard", "auto_merged"
    elif score >= review_thresh:
        return round(score, 4), "token_jaccard", "needs_review"
    else:
        return round(score, 4), "token_jaccard", "distinct"


def run_resolution_benchmark(
    dataset_path: str = "benchmarks/labels/resolution_pairs.jsonl",
    output_path: str = "benchmarks/results/resolution_benchmark.json",
) -> dict[str, Any]:
    """Execute evaluation over labeled pairs and report precision, recall, F1, false merges, and missed merges."""
    path = Path(dataset_path)
    if not path.exists():
        raise FileNotFoundError(f"Labeled dataset not found at {dataset_path}")

    settings = get_settings()
    auto_thresh = settings.resolution.embedding_similarity_threshold
    review_thresh = settings.resolution.review_band_lower

    pairs = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                pairs.append(json.loads(line))

    tp = 0  # True Positives (correct auto-merge)
    fp = 0  # False Positives (false merge on distinct entities)
    tn = 0  # True Negatives (correctly identified as distinct)
    fn = 0  # False Negatives (missed merge on identical entities)
    review_count = 0

    false_merges = []
    missed_merges = []
    review_band_pairs = []

    for item in pairs:
        surf_a = item["surface_a"]
        surf_b = item["surface_b"]
        ground_truth = item["match"]
        ent_type = item.get("entity_type", "Company")

        score, method, decision = evaluate_pair(
            surf_a, surf_b, ent_type, auto_thresh=auto_thresh, review_thresh=review_thresh
        )

        is_pred_merge = (decision == "auto_merged")

        if is_pred_merge and ground_truth:
            tp += 1
        elif is_pred_merge and not ground_truth:
            fp += 1
            false_merges.append(
                {
                    "surface_a": surf_a,
                    "surface_b": surf_b,
                    "score": score,
                    "method": method,
                    "category": item.get("category", "unknown"),
                }
            )
        elif not is_pred_merge and not ground_truth:
            tn += 1
        elif not is_pred_merge and ground_truth:
            fn += 1
            missed_merges.append(
                {
                    "surface_a": surf_a,
                    "surface_b": surf_b,
                    "score": score,
                    "method": method,
                    "category": item.get("category", "unknown"),
                }
            )

        if decision == "needs_review":
            review_count += 1
            review_band_pairs.append(
                {
                    "surface_a": surf_a,
                    "surface_b": surf_b,
                    "score": score,
                    "ground_truth": ground_truth,
                }
            )

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    accuracy = (tp + tn) / len(pairs) if pairs else 0.0

    results = {
        "total_pairs": len(pairs),
        "auto_merge_threshold": auto_thresh,
        "review_band_lower": review_thresh,
        "true_positives": tp,
        "false_positives": fp,
        "true_negatives": tn,
        "false_negatives": fn,
        "review_band_count": review_count,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "accuracy": round(accuracy, 4),
        "false_merges": false_merges,
        "missed_merges": missed_merges,
        "review_band_pairs": review_band_pairs,
    }

    # Save to output file
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    # Print formatted benchmark report
    print("\n" + "=" * 68)
    print("  ENTITY RESOLUTION LABELED-PAIR BENCHMARK (PRD FR-1.4, M3)")
    print("=" * 68)
    print(f"- Total Labeled Pairs Evaluated:       {len(pairs)}")
    print(f"- Auto-Merge Threshold:                {auto_thresh}")
    print(f"- Review Band Threshold:               [{review_thresh}, {auto_thresh})")
    print("-" * 68)
    print(f"- True Merges (TP):                    {tp}")
    print(f"- True Distinct (TN):                  {tn}")
    print(f"- False Merges (FP):                   {fp}  {'[PERFECT: 0 FALSE MERGES]' if fp == 0 else '[WARNING]'}")
    print(f"- Missed Merges (FN):                  {fn}")
    print(f"- Ambiguous in Review Queue:           {review_count}")
    print("-" * 68)
    print(f"- Precision:                           {precision * 100:.2f}%")
    print(f"- Recall:                              {recall * 100:.2f}%")
    print(f"- F1 Score:                            {f1 * 100:.2f}%")
    print(f"- Overall Accuracy:                    {accuracy * 100:.2f}%")
    print("=" * 68)

    if false_merges:
        print("\n[!] FALSE MERGES DETECTED:")
        for fm in false_merges:
            print(f"  - '{fm['surface_a']}' == '{fm['surface_b']}' (score: {fm['score']}, method: {fm['method']})")

    if missed_merges:
        print("\n[-] MISSED MERGES (FN):")
        for mm in missed_merges:
            print(f"  - '{mm['surface_a']}' != '{mm['surface_b']}' (score: {mm['score']}, method: {mm['method']})")

    print(f"\nBenchmark results saved to: {out}\n")
    return results


if __name__ == "__main__":
    run_resolution_benchmark()
