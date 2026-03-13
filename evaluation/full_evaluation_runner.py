from config import MODEL_SMALL, MODEL_LARGE
from evaluation.full_evaluation import run_full_evaluation

if __name__ == "__main__":

    # ── Full evaluation — gpt-4o-mini ─────────────────────────────
    run_full_evaluation(output_xlsx="results_gpt4o_mini.xlsx", delay_sec=3.0, active_model=MODEL_SMALL)
    # ── Full evaluation — gpt-4o (required for reflection Q4) ─────
    run_full_evaluation(output_xlsx="results_gpt4o.xlsx", delay_sec=3.0, active_model=MODEL_LARGE)