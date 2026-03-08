from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def get_latest_raw_file(raw_dir: Path) -> Path:
    files = sorted(raw_dir.glob("statewide_death_profiles_raw_*.csv"))
    if not files:
        raise FileNotFoundError("No raw mortality files found in data/raw.")
    return files[-1]


def transform_mortality_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Clean text fields
    text_cols = [
        "Geography_Type",
        "Strata",
        "Strata_Name",
        "Cause",
        "Cause_Desc",
        "ICD_Revision",
        "Annotation_Code",
        "Annotation_Desc",
        "Data_Extract_Date",
        "Data_Revision_Date",
    ]

    for col in text_cols:
        df[col] = df[col].fillna("").astype(str).str.strip()

    # Standardize numeric fields
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype("Int64")
    df["Month"] = pd.to_numeric(df["Month"], errors="coerce").astype("Int64")

    # Create monthly reporting date
    df["report_month"] = pd.to_datetime(
        df["Year"].astype(str) + "-" + df["Month"].astype(str).str.zfill(2) + "-01",
        errors="coerce"
    )

    # Parse source dates
    df["data_extract_date"] = pd.to_datetime(df["Data_Extract_Date"], errors="coerce")
    df["data_revision_date"] = pd.to_datetime(df["Data_Revision_Date"], errors="coerce")

    # Suppression flags
    df["is_suppressed"] = df["Annotation_Code"].isin(["1", "2"])
    df["suppression_type"] = df["Annotation_Desc"].replace("", pd.NA)

    # Numeric count
    df["count_numeric"] = pd.to_numeric(df["Count"], errors="coerce")

    # For unsuppressed records, count should be numeric
    # For suppressed records, count_numeric should remain missing
    df["is_total_population"] = df["Strata"].eq("Total Population")
    df["is_all_cause"] = df["Cause"].eq("ALL")

    # Simple month label for charts/tables later
    df["report_month_label"] = df["report_month"].dt.strftime("%Y-%m")

    return df


def save_subset(df: pd.DataFrame, file_name: str) -> None:
    output_file = PROCESSED_DIR / file_name
    df.to_csv(output_file, index=False)


def main():
    latest_raw_file = get_latest_raw_file(RAW_DIR)
    print(f"Transforming file: {latest_raw_file}", flush=True)

    df = pd.read_csv(latest_raw_file, dtype=str)
    df_clean = transform_mortality_data(df)

    # Save full cleaned dataset
    save_subset(df_clean, "mortality_cleaned.csv")

    # Reporting subsets by strata
    save_subset(
        df_clean[df_clean["Strata"] == "Total Population"].copy(),
        "mortality_total_population.csv"
    )

    save_subset(
        df_clean[df_clean["Strata"] == "Age"].copy(),
        "mortality_age.csv"
    )

    save_subset(
        df_clean[df_clean["Strata"] == "Gender"].copy(),
        "mortality_gender.csv"
    )

    save_subset(
        df_clean[df_clean["Strata"] == "Race-Ethnicity"].copy(),
        "mortality_race_ethnicity.csv"
    )

    save_subset(
        df_clean[df_clean["Strata"] == "Place Type"].copy(),
        "mortality_place_type.csv"
    )

    # Total population, cause-specific subset
    save_subset(
        df_clean[
            (df_clean["Strata"] == "Total Population") &
            (df_clean["Cause"] != "ALL")
        ].copy(),
        "mortality_total_population_cause_specific.csv"
    )

    # Simple transformation summary
    summary_file = PROCESSED_DIR / "transformation_summary.txt"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(f"Input rows: {len(df)}\n")
        f.write(f"Output rows: {len(df_clean)}\n")
        f.write(f"Suppressed rows: {int(df_clean['is_suppressed'].sum())}\n")
        f.write(f"Date range: {df_clean['report_month'].min()} to {df_clean['report_month'].max()}\n")
        f.write(f"Total Population rows: {len(df_clean[df_clean['Strata'] == 'Total Population'])}\n")
        f.write(f"Age rows: {len(df_clean[df_clean['Strata'] == 'Age'])}\n")
        f.write(f"Gender rows: {len(df_clean[df_clean['Strata'] == 'Gender'])}\n")
        f.write(f"Race-Ethnicity rows: {len(df_clean[df_clean['Strata'] == 'Race-Ethnicity'])}\n")
        f.write(f"Place Type rows: {len(df_clean[df_clean['Strata'] == 'Place Type'])}\n")

    print("Transformation complete.", flush=True)
    print(f"Processed files saved to: {PROCESSED_DIR}", flush=True)


if __name__ == "__main__":
    main()