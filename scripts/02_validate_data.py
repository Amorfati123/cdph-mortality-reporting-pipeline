from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
VALIDATION_DIR = PROJECT_ROOT / "data" / "validation"

VALIDATION_DIR.mkdir(parents=True, exist_ok=True)

REQUIRED_COLUMNS = [
    "_id",
    "Year",
    "Month",
    "Geography_Type",
    "Strata",
    "Strata_Name",
    "Cause",
    "Cause_Desc",
    "ICD_Revision",
    "Count",
    "Annotation_Code",
    "Annotation_Desc",
    "Data_Extract_Date",
    "Data_Revision_Date",
]

EXPECTED_STRATA = {
    "Age",
    "Gender",
    "Place Type",
    "Race-Ethnicity",
    "Total Population",
}

EXPECTED_GEOGRAPHY_TYPE = {"Occurrence"}
EXPECTED_ICD_REVISION = {"ICD-10"}


def get_latest_raw_file(raw_dir: Path) -> Path:
    files = sorted(raw_dir.glob("statewide_death_profiles_raw_*.csv"))
    if not files:
        raise FileNotFoundError("No raw mortality files found in data/raw.")
    return files[-1]


def run_validation_checks(df: pd.DataFrame) -> pd.DataFrame:
    results = []

    def add_result(check_name: str, status: str, details: str):
        results.append(
            {
                "check_name": check_name,
                "status": status,
                "details": details,
            }
        )

    # Required columns
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        add_result("required_columns_present", "FAIL", f"Missing columns: {missing_cols}")
    else:
        add_result("required_columns_present", "PASS", "All required columns are present.")

    # Row count
    if len(df) > 0:
        add_result("row_count_positive", "PASS", f"Row count = {len(df)}")
    else:
        add_result("row_count_positive", "FAIL", "Dataset has zero rows.")

    # Fully duplicated rows
    full_dups = int(df.duplicated().sum())
    if full_dups == 0:
        add_result("full_duplicate_rows", "PASS", "No fully duplicated rows found.")
    else:
        add_result("full_duplicate_rows", "FAIL", f"Found {full_dups} fully duplicated rows.")

    # Duplicate analytic keys
    key_cols = [
        "Year",
        "Month",
        "Geography_Type",
        "Strata",
        "Strata_Name",
        "Cause",
        "Cause_Desc",
        "ICD_Revision",
    ]
    dup_keys = int(df.duplicated(subset=key_cols).sum())
    if dup_keys == 0:
        add_result("duplicate_analytic_keys", "PASS", "No duplicate analytic keys found.")
    else:
        add_result("duplicate_analytic_keys", "FAIL", f"Found {dup_keys} duplicate analytic keys.")

    # Year should be numeric
    year_numeric = pd.to_numeric(df["Year"], errors="coerce")
    invalid_years = df.loc[year_numeric.isna(), "Year"].unique().tolist()
    if len(invalid_years) == 0:
        add_result("year_numeric", "PASS", "All Year values are numeric.")
    else:
        add_result("year_numeric", "FAIL", f"Invalid Year values: {invalid_years}")

    # Month should be 01 to 12
    valid_months = {f"{i:02d}" for i in range(1, 13)}
    invalid_months = sorted(set(df["Month"].astype(str)) - valid_months)
    if len(invalid_months) == 0:
        add_result("month_valid_range", "PASS", "All Month values are between 01 and 12.")
    else:
        add_result("month_valid_range", "FAIL", f"Invalid Month values: {invalid_months}")

    # Geography type
    geography_values = set(df["Geography_Type"].dropna().astype(str).unique())
    if geography_values == EXPECTED_GEOGRAPHY_TYPE:
        add_result("geography_type_expected", "PASS", f"Geography_Type = {sorted(geography_values)}")
    else:
        add_result(
            "geography_type_expected",
            "FAIL",
            f"Unexpected Geography_Type values: {sorted(geography_values)}",
        )

    # Strata values
    strata_values = set(df["Strata"].dropna().astype(str).unique())
    unexpected_strata = sorted(strata_values - EXPECTED_STRATA)
    if len(unexpected_strata) == 0:
        add_result("strata_expected", "PASS", f"Strata values are expected: {sorted(strata_values)}")
    else:
        add_result("strata_expected", "FAIL", f"Unexpected Strata values: {unexpected_strata}")

    # ICD revision
    icd_values = set(df["ICD_Revision"].dropna().astype(str).unique())
    if icd_values == EXPECTED_ICD_REVISION:
        add_result("icd_revision_expected", "PASS", f"ICD_Revision = {sorted(icd_values)}")
    else:
        add_result("icd_revision_expected", "FAIL", f"Unexpected ICD_Revision values: {sorted(icd_values)}")

    # Count validation with suppression awareness
    annotation_code_clean = df["Annotation_Code"].fillna("").astype(str).str.strip()
    count_numeric = pd.to_numeric(df["Count"], errors="coerce")

    suppressed_mask = annotation_code_clean.isin(["1", "2"])
    unsuppressed_mask = ~suppressed_mask

    invalid_unsuppressed_count_n = int((unsuppressed_mask & count_numeric.isna()).sum())
    negative_unsuppressed_count_n = int((unsuppressed_mask & (count_numeric < 0)).sum())
    suppressed_row_n = int(suppressed_mask.sum())
    suppressed_with_numeric_count_n = int((suppressed_mask & count_numeric.notna()).sum())

    if invalid_unsuppressed_count_n == 0:
        add_result(
            "count_numeric_unsuppressed",
            "PASS",
            "All unsuppressed Count values are numeric.",
        )
    else:
        add_result(
            "count_numeric_unsuppressed",
            "FAIL",
            f"Found {invalid_unsuppressed_count_n} unsuppressed rows with nonnumeric Count values.",
        )

    if negative_unsuppressed_count_n == 0:
        add_result(
            "count_nonnegative_unsuppressed",
            "PASS",
            "All unsuppressed Count values are nonnegative.",
        )
    else:
        add_result(
            "count_nonnegative_unsuppressed",
            "FAIL",
            f"Found {negative_unsuppressed_count_n} unsuppressed rows with negative Count values.",
        )

    add_result(
        "suppressed_rows_identified",
        "PASS",
        f"Found {suppressed_row_n} suppressed rows with Annotation_Code 1 or 2.",
    )

    if suppressed_with_numeric_count_n == 0:
        add_result(
            "suppressed_count_consistency",
            "PASS",
            "Suppressed rows have no numeric Count values, as expected.",
        )
    else:
        add_result(
            "suppressed_count_consistency",
            "FAIL",
            f"Found {suppressed_with_numeric_count_n} suppressed rows with numeric Count values.",
        )

    # Required descriptive fields
    for col in ["Strata_Name", "Cause", "Cause_Desc"]:
        missing_n = int(df[col].isna().sum())
        if missing_n == 0:
            add_result(f"{col.lower()}_present", "PASS", f"No missing values in {col}.")
        else:
            add_result(f"{col.lower()}_present", "FAIL", f"Found {missing_n} missing values in {col}.")

    # Annotation codes should only be blank, 1, or 2
    annotation_values = set(df["Annotation_Code"].fillna("").astype(str).str.strip().unique())
    unexpected_annotation_values = sorted(annotation_values - {"", "1", "2"})
    if len(unexpected_annotation_values) == 0:
        add_result(
            "annotation_codes_expected",
            "PASS",
            f"Annotation codes are valid: {sorted(annotation_values)}",
        )
    else:
        add_result(
            "annotation_codes_expected",
            "FAIL",
            f"Unexpected Annotation_Code values: {unexpected_annotation_values}",
        )

    # Date parsing
    for col in ["Data_Extract_Date", "Data_Revision_Date"]:
        parsed = pd.to_datetime(df[col], errors="coerce")
        invalid_dates = int(parsed.isna().sum())
        if invalid_dates == 0:
            add_result(f"{col.lower()}_parseable", "PASS", f"All {col} values parsed successfully.")
        else:
            add_result(
                f"{col.lower()}_parseable",
                "FAIL",
                f"Found {invalid_dates} unparseable values in {col}.",
            )

    return pd.DataFrame(results)


def main():
    latest_raw_file = get_latest_raw_file(RAW_DIR)
    print(f"Validating file: {latest_raw_file}", flush=True)

    df = pd.read_csv(latest_raw_file, dtype=str)
    validation_results = run_validation_checks(df)

    output_csv = VALIDATION_DIR / "validation_results_latest.csv"
    output_txt = VALIDATION_DIR / "validation_report_latest.txt"

    validation_results.to_csv(output_csv, index=False)

    with open(output_txt, "w", encoding="utf-8") as f:
        for _, row in validation_results.iterrows():
            f.write(f"[{row['status']}] {row['check_name']}: {row['details']}\n")

    fail_count = int((validation_results["status"] == "FAIL").sum())

    print(f"Validation complete. FAIL checks: {fail_count}", flush=True)
    print(f"Validation CSV saved to: {output_csv}", flush=True)
    print(f"Validation report saved to: {output_txt}", flush=True)


if __name__ == "__main__":
    main()