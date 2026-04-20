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
    - real_seeds.jsonl is updated incrementally; only new unique seeds are appended.

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
STATE_FILE = os.path.join(SCRIPT_DIR, "real_seeds_state.json")

# Minimum character length for model_output to be considered a valid generation
MIN_OUTPUT_LENGTH = 50
MAX_REQUIRED_SKILLS = 3
MAX_INTERESTS = 2


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


def _normalize_list(value, max_items: int | None = None) -> list[str]:
    """Normalize mixed list/string values into a de-duplicated list of strings."""
    items: list[str] = []

    if isinstance(value, list):
        for item in value:
            text = str(item).strip()
            if text:
                items.append(text)
    elif isinstance(value, str):
        for item in value.split(","):
            text = item.strip()
            if text:
                items.append(text)

    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
        if max_items is not None and len(result) >= max_items:
            break

    return result


def _parse_messages_payload(payload: dict) -> dict | None:
    """Parse {messages:[{role:user, content:'{...json...}'}]} into inner input dict."""
    messages = payload.get("messages", [])
    if not isinstance(messages, list) or len(messages) != 1:
        return None

    msg = messages[0] if isinstance(messages[0], dict) else {}
    content = msg.get("content", "")
    if not isinstance(content, str):
        return None

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return None

    if not isinstance(parsed, dict):
        return None
    if "student_data" not in parsed or "job_data" not in parsed:
        return None
    return parsed


def _canonicalize_seed_payload(raw_payload: dict) -> dict:
    """Coerce any legacy payload shape into the canonical finetuned schema."""
    student_raw = raw_payload.get("student_data", {}) if isinstance(raw_payload, dict) else {}
    job_raw = raw_payload.get("job_data", {}) if isinstance(raw_payload, dict) else {}

    target_role = str(job_raw.get("target_job_role", "")).strip()
    required_skills = _normalize_list(job_raw.get("required_skills", []), MAX_REQUIRED_SKILLS)
    interests = _normalize_list(student_raw.get("interests", []), MAX_INTERESTS)
    current_skills = _normalize_list(student_raw.get("current_skills", []))

    description = f"Targeting a role as {target_role}" if target_role else ""

    return {
        "student_data": {
            "demographics": str(student_raw.get("demographics", "")).strip(),
            "major": str(student_raw.get("major", "Undeclared")).strip() or "Undeclared",
            "interests": interests,
            "current_skills": current_skills,
            "personality": str(student_raw.get("personality", "")).strip(),
        },
        "job_data": {
            "target_job_role": target_role,
            "required_skills": required_skills,
            "description": description,
        },
    }


def _extract_canonical_payload(model_input: dict) -> dict | None:
    """
    Read canonical payload from logs.

    Priority:
      1) model_input.messages (new canonical logging shape)
      2) model_input.pre_generation_payload (legacy compatibility)
      3) model_input.student_data/job_data (legacy raw shape)
    """
    if not isinstance(model_input, dict):
        return None

    root_messages = model_input.get("messages")
    if isinstance(root_messages, list):
        parsed = _parse_messages_payload({"messages": root_messages})
        if parsed:
            return _canonicalize_seed_payload(parsed)

    pre_generation = model_input.get("pre_generation_payload")
    if isinstance(pre_generation, dict):
        parsed = _parse_messages_payload(pre_generation)
        if parsed:
            return _canonicalize_seed_payload(parsed)

    if isinstance(model_input.get("student_data"), dict) and isinstance(model_input.get("job_data"), dict):
        return _canonicalize_seed_payload({
            "student_data": model_input.get("student_data", {}),
            "job_data": model_input.get("job_data", {}),
        })

    return None


def _load_existing_seed_hashes(output_file: str) -> set[str]:
    """Load dedup hashes from existing seed file so we can append safely."""
    hashes: set[str] = set()

    if not os.path.exists(output_file):
        return hashes

    with open(output_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                seed_entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            seed_payload = _extract_canonical_payload(seed_entry)
            if not seed_payload:
                continue

            student_data = seed_payload.get("student_data", {})
            job_data = seed_payload.get("job_data", {})
            if not student_data.get("current_skills") or not job_data.get("target_job_role"):
                continue

            hashes.add(_dedup_key(student_data, job_data))

    return hashes


def _load_state(state_file: str) -> dict:
    """Load incremental extraction cursor state."""
    if not os.path.exists(state_file):
        return {}

    try:
        with open(state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_state(state_file: str, state: dict) -> None:
    """Persist incremental extraction cursor state."""
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f)


def _read_new_log_lines(log_file: str, state_file: str) -> tuple[list[str], int]:
    """
    Return only newly appended log lines since the previous extraction run.

    Uses a byte-offset cursor so repeated calls don't rescan the entire log.
    """
    state = _load_state(state_file)
    last_offset = int(state.get("log_offset", 0) or 0)

    current_size = os.path.getsize(log_file)
    if last_offset < 0 or last_offset > current_size:
        # Log was truncated/rotated; restart from beginning.
        last_offset = 0

    with open(log_file, "r", encoding="utf-8") as f:
        f.seek(last_offset)
        lines = f.readlines()
        new_offset = f.tell()

    return lines, new_offset


def extract_seeds(
    log_file: str = LOG_FILE,
    output_file: str = OUTPUT_FILE,
    state_file: str = STATE_FILE,
) -> int:
    """
    Read newly appended model-output log entries and append new unique seeds.

    Returns the number of seed entries appended in this run.
    """
    if not os.path.exists(log_file):
        print(f"[extract_real_seeds] Log file not found: {log_file}")
        return 0

    seen_hashes = _load_existing_seed_hashes(output_file)
    new_lines, new_offset = _read_new_log_lines(log_file, state_file)

    appended = 0

    # Ensure target file exists before appending.
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, "a", encoding="utf-8") as out:
        for idx, line in enumerate(new_lines, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                entry = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"[extract_real_seeds] Skipping malformed new line {idx}: {e}")
                continue

            model_output = entry.get("model_output", "")
            if not _is_valid_output(model_output):
                continue  # skip error / empty outputs

            model_input = entry.get("model_input", {})
            seed_payload = _extract_canonical_payload(model_input)
            if not seed_payload:
                continue

            student_data = seed_payload.get("student_data", {})
            job_data = seed_payload.get("job_data", {})

            # Require at minimum one skill and a target role
            if not student_data.get("current_skills") or not job_data.get("target_job_role"):
                continue

            key = _dedup_key(student_data, job_data)
            if key in seen_hashes:
                continue

            seen_hashes.add(key)

            seed_entry = {
                "messages": [
                    {
                        "role": "user",
                        "content": json.dumps(seed_payload, separators=(",", ":"), ensure_ascii=False),
                    }
                ]
            }

            out.write(json.dumps(seed_entry, ensure_ascii=False) + "\n")
            appended += 1

    _save_state(state_file, {"log_offset": new_offset})

    print(
        f"[extract_real_seeds] Appended {appended} new seed(s) to {output_file}. "
        f"Cursor offset: {new_offset}."
    )
    return appended


if __name__ == "__main__":
    count = extract_seeds()
    if count == 0:
        print("[extract_real_seeds] No new valid seeds to append.")
