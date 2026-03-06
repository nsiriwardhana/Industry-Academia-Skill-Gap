"""
extract_real_seeds.py
─────────────────────
Converts real student usage data from `feedback/feedback_data/model_outputs_log.jsonl`
into a clean seed file (`datasets/real_seeds.jsonl`) that augment_dataset.py can consume.

Rules:
  - Only entries with a meaningful model output (not error, length >= 50) are included.
  - Deduplication is by SHA-256 hash of:
        sorted_skills + "|" + demographics.lower() + "|" + target_job_role.lower()
    so the same student submitting the same role twice yields ONE seed, but an
    updated skills list or a different target role produces a NEW seed.
  - real_seeds.jsonl is fully rewritten on every run (not appended to).

Usage:
  python datasets/extract_real_seeds.py           # manual run
  SEED_FILE=real_seeds.jsonl python run_server.py  # point augment_dataset at it
"""

import hashlib
import json
import os

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)

LOG_FILE = os.path.join(BACKEND_DIR, "feedback", "feedback_data", "model_outputs_log.jsonl")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "real_seeds.jsonl")

# Minimum character length for model_output to be considered a valid generation
MIN_OUTPUT_LENGTH = 50


def _is_valid_output(model_output: str) -> bool:
    """Return True if the model output looks like a real generation (not an error)."""
    if not model_output or len(model_output) < MIN_OUTPUT_LENGTH:
        return False
    lowered = model_output.strip().lower()
    # Filter out connection errors, API errors etc.
    if lowered.startswith("error:") or lowered.startswith("error "):
        return False
    return True


def _dedup_key(student_data: dict, job_data: dict) -> str:
    """Produce a deterministic hash that captures unique student × role pairs."""
    skills = sorted(s.strip().lower() for s in student_data.get("current_skills", []))
    demographics = student_data.get("demographics", "").lower().strip()
    target_role = job_data.get("target_job_role", "").lower().strip()

    raw = "|".join(skills) + "||" + demographics + "||" + target_role
    return hashlib.sha256(raw.encode()).hexdigest()


def extract_seeds(log_file: str = LOG_FILE, output_file: str = OUTPUT_FILE) -> int:
    """
    Read the model outputs log, deduplicate, and rewrite real_seeds.jsonl.

    Returns the number of unique seed entries written.
    """
    if not os.path.exists(log_file):
        print(f"[extract_real_seeds] Log file not found: {log_file}")
        return 0

    seen_hashes: set[str] = set()
    seeds: list[dict] = []

    with open(log_file, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                entry = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"[extract_real_seeds] Skipping malformed line {lineno}: {e}")
                continue

            model_output = entry.get("model_output", "")
            if not _is_valid_output(model_output):
                continue  # skip error / empty outputs

            model_input = entry.get("model_input", {})
            student_data = model_input.get("student_data", {})
            job_data = model_input.get("job_data", {})

            # Require at minimum one skill and a target role
            if not student_data.get("current_skills") or not job_data.get("target_job_role"):
                continue

            key = _dedup_key(student_data, job_data)
            if key in seen_hashes:
                continue  # duplicate — same student × role combination
            seen_hashes.add(key)

            # Build seed entry in the format expected by augment_dataset.py
            seed_payload = {
                "student_data": {
                    "demographics": student_data.get("demographics", ""),
                    "major": student_data.get("major", "Undeclared"),
                    "interests": student_data.get("interests", []),
                    "current_skills": student_data.get("current_skills", []),
                    "personality": student_data.get("personality", ""),
                },
                "job_data": {
                    "target_job_role": job_data.get("target_job_role", ""),
                    "required_skills": job_data.get("required_skills", []),
                    "description": job_data.get("description", ""),
                },
            }

            seed_entry = {
                "messages": [
                    {"role": "user", "content": json.dumps(seed_payload, ensure_ascii=False)}
                ]
            }
            seeds.append(seed_entry)

    # Rewrite output file from scratch
    with open(output_file, "w", encoding="utf-8") as out:
        for seed in seeds:
            out.write(json.dumps(seed, ensure_ascii=False) + "\n")

    print(f"[extract_real_seeds] {len(seeds)} unique seeds written to {output_file}")
    return len(seeds)


if __name__ == "__main__":
    count = extract_seeds()
    if count == 0:
        print("[extract_real_seeds] No valid seeds found — check the log file path or generate some plans first.")
