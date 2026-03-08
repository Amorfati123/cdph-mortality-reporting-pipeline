from pathlib import Path
from datetime import datetime
import requests
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
REF_DIR = PROJECT_ROOT / "data" / "reference"
PROFILE_DIR = PROJECT_ROOT / "data" / "profiling"

RAW_DIR.mkdir(parents=True, exist_ok=True)
REF_DIR.mkdir(parents=True, exist_ok=True)
PROFILE_DIR.mkdir(parents=True, exist_ok=True)

RESOURCE_ID = "3192c0ff-e380-4314-8a88-16a3bdace8b7"
BASE_URL = "https://data.chhs.ca.gov/api/3/action/datastore_search"

def fetch_ckan_data(resource_id: str, chunk_size: int = 1000) -> pd.DataFrame:
    all_records = []
    offset = 0

    while True:
        response = requests.get(
            BASE_URL,
            params={
                "resource_id": resource_id,
                "limit": chunk_size,
                "offset": offset
            },
            timeout=30
        )
        response.raise_for_status()
        payload = response.json()

        if not payload.get("success", False):
            raise RuntimeError("CKAN API request failed.")

        records = payload["result"]["records"]
        if not records:
            break

        all_records.extend(records)
        offset += chunk_size

    return pd.DataFrame(all_records)

def profile_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for col in df.columns:
        sample_vals = df[col].dropna().astype(str).unique()[:5]
        rows.append({
            "column": col,
            "dtype": str(df[col].dtype),
            "missing_n": int(df[col].isna().sum()),
            "missing_pct": round(df[col].isna().mean() * 100, 2),
            "distinct_n": int(df[col].nunique(dropna=True)),
            "sample_values": " | ".join(sample_vals)
        })

    return pd.DataFrame(rows)

def main():
    print("Pulling mortality data...", flush=True)

    run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    df = fetch_ckan_data(RESOURCE_ID)

    print(f"Retrieved {df.shape[0]} rows and {df.shape[1]} columns.", flush=True)

    raw_file = RAW_DIR / f"statewide_death_profiles_raw_{run_ts}.csv"
    df.to_csv(raw_file, index=False)

    dict_file = REF_DIR / "statewide_death_profiles_data_dictionary.csv"
    if dict_file.exists():
        df_dict = pd.read_csv(dict_file)
        dict_copy_file = PROFILE_DIR / f"data_dictionary_copy_{run_ts}.csv"
        df_dict.to_csv(dict_copy_file, index=False)
    else:
        print("Warning: data dictionary file not found.", flush=True)

    profile_df = profile_dataframe(df)
    profile_file = PROFILE_DIR / f"dataset_profile_{run_ts}.csv"
    profile_df.to_csv(profile_file, index=False)

    summary_lines = []
    summary_lines.append(f"Run timestamp: {run_ts}")
    summary_lines.append(f"Row count: {df.shape[0]}")
    summary_lines.append(f"Column count: {df.shape[1]}")
    summary_lines.append(f"Columns: {list(df.columns)}")

    for col in ["Year", "Month", "Strata", "Geography_Type", "ICD_Revision"]:
        if col in df.columns:
            vals = sorted(df[col].dropna().astype(str).unique().tolist())
            summary_lines.append(f"{col} unique values: {vals}")

    if {"Annotation_Code", "Annotation_Desc"}.issubset(df.columns):
        ann = df[["Annotation_Code", "Annotation_Desc"]].drop_duplicates()
        summary_lines.append("Annotation codes:")
        for _, row in ann.iterrows():
            summary_lines.append(f"  {row['Annotation_Code']} -> {row['Annotation_Desc']}")

    key_cols = [
        "Year", "Month", "Geography_Type", "Strata", "Strata_Name",
        "Cause", "Cause_Desc", "ICD_Revision"
    ]
    key_cols_present = [c for c in key_cols if c in df.columns]
    dup_n = df.duplicated(subset=key_cols_present).sum()
    summary_lines.append(f"Duplicate rows on analytic key: {dup_n}")

    summary_file = PROFILE_DIR / f"profile_summary_{run_ts}.txt"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines))

    print(f"Raw snapshot saved to: {raw_file}", flush=True)
    print(f"Profile table saved to: {profile_file}", flush=True)
    print(f"Summary file saved to: {summary_file}", flush=True)
    print("Step 1 complete.", flush=True)

if __name__ == "__main__":
    main()