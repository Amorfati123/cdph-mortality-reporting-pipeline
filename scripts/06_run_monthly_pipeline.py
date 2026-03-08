from pathlib import Path
from datetime import datetime
import subprocess
import sys
import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
VALIDATION_DIR = PROJECT_ROOT / "data" / "validation"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_SUMMARIES_DIR = PROJECT_ROOT / "outputs" / "summaries"
LOG_DIR = PROJECT_ROOT / "logs"

RAW_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

RESOURCE_ID = "3192c0ff-e380-4314-8a88-16a3bdace8b7"
BASE_URL = "https://data.chhs.ca.gov/api/3/action/datastore_search"

PROFILE_SCRIPT = PROJECT_ROOT / "scripts" / "01_profile_data.py"
VALIDATE_SCRIPT = PROJECT_ROOT / "scripts" / "02_validate_data.py"
TRANSFORM_SCRIPT = PROJECT_ROOT / "scripts" / "03_transform_data.py"
REPORT_TABLES_SCRIPT = PROJECT_ROOT / "scripts" / "04_generate_report_tables.py"
FIGURES_SCRIPT = PROJECT_ROOT / "scripts" / "05_create_figures_and_narrative.py"


def log_message(message: str, log_file: Path) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line, flush=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def fetch_latest_source_metadata() -> dict:
    response = requests.get(
        BASE_URL,
        params={"resource_id": RESOURCE_ID, "limit": 5},
        timeout=30
    )
    response.raise_for_status()
    payload = response.json()

    if not payload.get("success", False):
        raise RuntimeError("CKAN API request failed during metadata check.")

    records = payload["result"]["records"]
    if not records:
        raise RuntimeError("No records returned from source dataset.")

    sample_df = pd.DataFrame(records)

    metadata = {
        "data_extract_date": sample_df["Data_Extract_Date"].dropna().iloc[0] if "Data_Extract_Date" in sample_df.columns else None,
        "data_revision_date": sample_df["Data_Revision_Date"].dropna().iloc[0] if "Data_Revision_Date" in sample_df.columns else None,
        "source_total_rows": payload["result"].get("total")
    }
    return metadata


def get_latest_processed_metadata_file() -> Path:
    return OUTPUT_SUMMARIES_DIR / "pipeline_run_metadata.csv"


def previous_run_matches(current_metadata: dict) -> bool:
    metadata_file = get_latest_processed_metadata_file()
    if not metadata_file.exists():
        return False

    prev = pd.read_csv(metadata_file)
    if prev.empty:
        return False

    prev_row = prev.iloc[-1]

    return (
        str(prev_row.get("data_extract_date", "")) == str(current_metadata.get("data_extract_date", "")) and
        str(prev_row.get("data_revision_date", "")) == str(current_metadata.get("data_revision_date", "")) and
        str(prev_row.get("source_total_rows", "")) == str(current_metadata.get("source_total_rows", ""))
    )


def run_script(script_path: Path, log_file: Path) -> None:
    log_message(f"Running {script_path.name}", log_file)

    result = subprocess.run(
        [sys.executable, "-u", str(script_path)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True
    )

    if result.stdout:
        log_message(result.stdout.strip(), log_file)

    if result.returncode != 0:
        if result.stderr:
            log_message(result.stderr.strip(), log_file)
        raise RuntimeError(f"{script_path.name} failed with return code {result.returncode}")


def validation_passed() -> bool:
    report_file = VALIDATION_DIR / "validation_report_latest.txt"
    if not report_file.exists():
        return False

    with open(report_file, "r", encoding="utf-8") as f:
        report_text = f.read()

    return "[FAIL]" not in report_text


def write_run_metadata(current_metadata: dict, log_file: Path) -> None:
    metadata_file = get_latest_processed_metadata_file()

    run_record = pd.DataFrame(
        [
            {
                "run_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "data_extract_date": current_metadata.get("data_extract_date"),
                "data_revision_date": current_metadata.get("data_revision_date"),
                "source_total_rows": current_metadata.get("source_total_rows"),
            }
        ]
    )

    if metadata_file.exists():
        existing = pd.read_csv(metadata_file)
        updated = pd.concat([existing, run_record], ignore_index=True)
    else:
        updated = run_record

    updated.to_csv(metadata_file, index=False)
    log_message(f"Updated run metadata file: {metadata_file}", log_file)


def main():
    run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOG_DIR / f"monthly_pipeline_run_{run_ts}.log"

    log_message("Starting monthly mortality pipeline.", log_file)

    current_metadata = fetch_latest_source_metadata()
    log_message(
        f"Source metadata check: extract_date={current_metadata['data_extract_date']}, "
        f"revision_date={current_metadata['data_revision_date']}, "
        f"source_total_rows={current_metadata['source_total_rows']}",
        log_file
    )

    if previous_run_matches(current_metadata):
        log_message("No source update detected. Pipeline stopped without rerun.", log_file)
        return

    log_message("New or revised source data detected. Running pipeline.", log_file)

    run_script(PROFILE_SCRIPT, log_file)
    run_script(VALIDATE_SCRIPT, log_file)

    if not validation_passed():
        raise RuntimeError("Validation failed. Downstream processing stopped.")

    run_script(TRANSFORM_SCRIPT, log_file)
    run_script(REPORT_TABLES_SCRIPT, log_file)
    run_script(FIGURES_SCRIPT, log_file)

    write_run_metadata(current_metadata, log_file)
    log_message("Monthly mortality pipeline completed successfully.", log_file)


if __name__ == "__main__":
    main()