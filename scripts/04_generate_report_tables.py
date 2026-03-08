from pathlib import Path
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_TABLES_DIR = PROJECT_ROOT / "outputs" / "tables"
OUTPUT_SUMMARIES_DIR = PROJECT_ROOT / "outputs" / "summaries"

OUTPUT_TABLES_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)


def load_cleaned_data() -> pd.DataFrame:
    file_path = PROCESSED_DIR / "mortality_cleaned.csv"
    if not file_path.exists():
        raise FileNotFoundError("Processed file mortality_cleaned.csv not found.")
    df = pd.read_csv(file_path, parse_dates=["report_month", "data_extract_date", "data_revision_date"])
    return df


def save_table(df: pd.DataFrame, file_name: str) -> None:
    df.to_csv(OUTPUT_TABLES_DIR / file_name, index=False)


def create_monthly_trend_tables(df: pd.DataFrame) -> None:
    analysis_df = df[(~df["is_suppressed"]) & (df["count_numeric"].notna())].copy()

    total_pop_all_cause = (
        analysis_df[
            (analysis_df["Strata"] == "Total Population") &
            (analysis_df["Cause"] == "ALL")
        ]
        .sort_values("report_month")
        [["report_month", "report_month_label", "count_numeric"]]
        .rename(columns={"count_numeric": "deaths"})
    )
    save_table(total_pop_all_cause, "monthly_total_population_all_cause.csv")

    gender_all_cause = (
        analysis_df[
            (analysis_df["Strata"] == "Gender") &
            (analysis_df["Cause"] == "ALL")
        ]
        .sort_values(["report_month", "Strata_Name"])
        [["report_month", "report_month_label", "Strata_Name", "count_numeric"]]
        .rename(columns={"Strata_Name": "gender", "count_numeric": "deaths"})
    )
    save_table(gender_all_cause, "monthly_gender_all_cause.csv")

    age_all_cause = (
        analysis_df[
            (analysis_df["Strata"] == "Age") &
            (analysis_df["Cause"] == "ALL")
        ]
        .sort_values(["report_month", "Strata_Name"])
        [["report_month", "report_month_label", "Strata_Name", "count_numeric"]]
        .rename(columns={"Strata_Name": "age_group", "count_numeric": "deaths"})
    )
    save_table(age_all_cause, "monthly_age_all_cause.csv")

    race_all_cause = (
        analysis_df[
            (analysis_df["Strata"] == "Race-Ethnicity") &
            (analysis_df["Cause"] == "ALL")
        ]
        .sort_values(["report_month", "Strata_Name"])
        [["report_month", "report_month_label", "Strata_Name", "count_numeric"]]
        .rename(columns={"Strata_Name": "race_ethnicity", "count_numeric": "deaths"})
    )
    save_table(race_all_cause, "monthly_race_ethnicity_all_cause.csv")

    place_type_all_cause = (
        analysis_df[
            (analysis_df["Strata"] == "Place Type") &
            (analysis_df["Cause"] == "ALL")
        ]
        .sort_values(["report_month", "Strata_Name"])
        [["report_month", "report_month_label", "Strata_Name", "count_numeric"]]
        .rename(columns={"Strata_Name": "place_type", "count_numeric": "deaths"})
    )
    save_table(place_type_all_cause, "monthly_place_type_all_cause.csv")


def create_latest_month_summary_tables(df: pd.DataFrame) -> None:
    analysis_df = df[(~df["is_suppressed"]) & (df["count_numeric"].notna())].copy()

    latest_month = analysis_df["report_month"].max()
    previous_month = latest_month - pd.offsets.MonthBegin(1)
    prior_year_same_month = latest_month - pd.DateOffset(years=1)

    # Latest month top causes for total population
    latest_all_cause_total = analysis_df[
        (analysis_df["report_month"] == latest_month) &
        (analysis_df["Strata"] == "Total Population") &
        (analysis_df["Cause"] == "ALL")
    ]["count_numeric"].iloc[0]

    latest_top_causes = (
        analysis_df[
            (analysis_df["report_month"] == latest_month) &
            (analysis_df["Strata"] == "Total Population") &
            (analysis_df["Cause"] != "ALL")
        ]
        .sort_values("count_numeric", ascending=False)
        [["report_month", "Cause", "Cause_Desc", "count_numeric"]]
        .rename(columns={"count_numeric": "deaths"})
        .reset_index(drop=True)
    )

    latest_top_causes["rank"] = latest_top_causes.index + 1
    latest_top_causes["share_of_total_pct"] = (
        latest_top_causes["deaths"] / latest_all_cause_total * 100
    ).round(2)

    latest_top_causes = latest_top_causes[
        ["rank", "report_month", "Cause", "Cause_Desc", "deaths", "share_of_total_pct"]
    ]

    save_table(latest_top_causes, "latest_month_top_causes_total_population.csv")

    # Latest month vs previous month for all-cause total population
    current_all_cause = analysis_df[
        (analysis_df["report_month"] == latest_month) &
        (analysis_df["Strata"] == "Total Population") &
        (analysis_df["Cause"] == "ALL")
    ][["report_month", "count_numeric"]].copy()
    current_all_cause = current_all_cause.rename(columns={"count_numeric": "latest_deaths"})

    previous_all_cause = analysis_df[
        (analysis_df["report_month"] == previous_month) &
        (analysis_df["Strata"] == "Total Population") &
        (analysis_df["Cause"] == "ALL")
    ][["report_month", "count_numeric"]].copy()
    previous_all_cause = previous_all_cause.rename(columns={"count_numeric": "previous_month_deaths"})

    latest_vs_previous = pd.DataFrame({
        "latest_month": [latest_month],
        "previous_month": [previous_month]
    })

    if not current_all_cause.empty:
        latest_vs_previous["latest_deaths"] = current_all_cause["latest_deaths"].iloc[0]
    else:
        latest_vs_previous["latest_deaths"] = np.nan

    if not previous_all_cause.empty:
        latest_vs_previous["previous_month_deaths"] = previous_all_cause["previous_month_deaths"].iloc[0]
    else:
        latest_vs_previous["previous_month_deaths"] = np.nan

    latest_vs_previous["absolute_change"] = (
        latest_vs_previous["latest_deaths"] - latest_vs_previous["previous_month_deaths"]
    )
    latest_vs_previous["percent_change"] = np.where(
        latest_vs_previous["previous_month_deaths"].notna() &
        (latest_vs_previous["previous_month_deaths"] != 0),
        (latest_vs_previous["absolute_change"] / latest_vs_previous["previous_month_deaths"]) * 100,
        np.nan
    )
    save_table(latest_vs_previous, "latest_vs_previous_month_total_population_all_cause.csv")

    # Latest month vs same month prior year for all-cause total population
    prior_year_all_cause = analysis_df[
        (analysis_df["report_month"] == prior_year_same_month) &
        (analysis_df["Strata"] == "Total Population") &
        (analysis_df["Cause"] == "ALL")
    ][["report_month", "count_numeric"]].copy()
    prior_year_all_cause = prior_year_all_cause.rename(columns={"count_numeric": "prior_year_same_month_deaths"})

    latest_vs_prior_year = pd.DataFrame({
        "latest_month": [latest_month],
        "prior_year_same_month": [prior_year_same_month]
    })

    if not current_all_cause.empty:
        latest_vs_prior_year["latest_deaths"] = current_all_cause["latest_deaths"].iloc[0]
    else:
        latest_vs_prior_year["latest_deaths"] = np.nan

    if not prior_year_all_cause.empty:
        latest_vs_prior_year["prior_year_same_month_deaths"] = prior_year_all_cause["prior_year_same_month_deaths"].iloc[0]
    else:
        latest_vs_prior_year["prior_year_same_month_deaths"] = np.nan

    latest_vs_prior_year["absolute_change"] = (
        latest_vs_prior_year["latest_deaths"] - latest_vs_prior_year["prior_year_same_month_deaths"]
    )
    latest_vs_prior_year["percent_change"] = np.where(
        latest_vs_prior_year["prior_year_same_month_deaths"].notna() &
        (latest_vs_prior_year["prior_year_same_month_deaths"] != 0),
        (latest_vs_prior_year["absolute_change"] / latest_vs_prior_year["prior_year_same_month_deaths"]) * 100,
        np.nan
    )
    save_table(latest_vs_prior_year, "latest_vs_prior_year_total_population_all_cause.csv")

    # Cause-specific latest month vs previous month
    current_causes = analysis_df[
        (analysis_df["report_month"] == latest_month) &
        (analysis_df["Strata"] == "Total Population") &
        (analysis_df["Cause"] != "ALL")
    ][["Cause", "Cause_Desc", "count_numeric"]].copy()
    current_causes = current_causes.rename(columns={"count_numeric": "latest_deaths"})

    previous_causes = analysis_df[
        (analysis_df["report_month"] == previous_month) &
        (analysis_df["Strata"] == "Total Population") &
        (analysis_df["Cause"] != "ALL")
    ][["Cause", "Cause_Desc", "count_numeric"]].copy()
    previous_causes = previous_causes.rename(columns={"count_numeric": "previous_month_deaths"})

    cause_vs_previous = current_causes.merge(
        previous_causes,
        on=["Cause", "Cause_Desc"],
        how="outer"
    )

    cause_vs_previous["latest_month"] = latest_month
    cause_vs_previous["previous_month"] = previous_month
    cause_vs_previous["absolute_change"] = (
        cause_vs_previous["latest_deaths"] - cause_vs_previous["previous_month_deaths"]
    )
    cause_vs_previous["percent_change"] = np.where(
        cause_vs_previous["previous_month_deaths"].notna() &
        (cause_vs_previous["previous_month_deaths"] != 0),
        (cause_vs_previous["absolute_change"] / cause_vs_previous["previous_month_deaths"]) * 100,
        np.nan
    )
    cause_vs_previous = cause_vs_previous.sort_values("latest_deaths", ascending=False)
    save_table(cause_vs_previous, "latest_vs_previous_month_cause_specific.csv")

    # Cause-specific latest month vs same month prior year
    prior_year_causes = analysis_df[
        (analysis_df["report_month"] == prior_year_same_month) &
        (analysis_df["Strata"] == "Total Population") &
        (analysis_df["Cause"] != "ALL")
    ][["Cause", "Cause_Desc", "count_numeric"]].copy()
    prior_year_causes = prior_year_causes.rename(columns={"count_numeric": "prior_year_same_month_deaths"})

    cause_vs_prior_year = current_causes.merge(
        prior_year_causes,
        on=["Cause", "Cause_Desc"],
        how="outer"
    )

    cause_vs_prior_year["latest_month"] = latest_month
    cause_vs_prior_year["prior_year_same_month"] = prior_year_same_month
    cause_vs_prior_year["absolute_change"] = (
        cause_vs_prior_year["latest_deaths"] - cause_vs_prior_year["prior_year_same_month_deaths"]
    )
    cause_vs_prior_year["percent_change"] = np.where(
        cause_vs_prior_year["prior_year_same_month_deaths"].notna() &
        (cause_vs_prior_year["prior_year_same_month_deaths"] != 0),
        (cause_vs_prior_year["absolute_change"] / cause_vs_prior_year["prior_year_same_month_deaths"]) * 100,
        np.nan
    )
    cause_vs_prior_year = cause_vs_prior_year.sort_values("latest_deaths", ascending=False)
    save_table(cause_vs_prior_year, "latest_vs_prior_year_cause_specific.csv")

    # Text summary for the report
    summary_file = OUTPUT_SUMMARIES_DIR / "latest_reporting_period_summary.txt"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(f"Latest reporting month: {latest_month.strftime('%Y-%m')}\n")
        f.write(f"Previous month used for comparison: {previous_month.strftime('%Y-%m')}\n")
        f.write(f"Prior-year comparison month: {prior_year_same_month.strftime('%Y-%m')}\n")

        if not latest_vs_previous["latest_deaths"].isna().all():
            f.write(
                f"Latest all-cause deaths: {latest_vs_previous['latest_deaths'].iloc[0]:,.0f}\n"
            )
        if not latest_vs_previous["previous_month_deaths"].isna().all():
            f.write(
                f"Previous month all-cause deaths: {latest_vs_previous['previous_month_deaths'].iloc[0]:,.0f}\n"
            )
        if not latest_vs_prior_year["prior_year_same_month_deaths"].isna().all():
            f.write(
                f"Same month prior year all-cause deaths: {latest_vs_prior_year['prior_year_same_month_deaths'].iloc[0]:,.0f}\n"
            )


def main():
    df = load_cleaned_data()

    print("Generating monthly reporting tables...", flush=True)

    create_monthly_trend_tables(df)
    create_latest_month_summary_tables(df)

    print("Step 4 complete.", flush=True)
    print(f"Tables saved to: {OUTPUT_TABLES_DIR}", flush=True)
    print(f"Summary files saved to: {OUTPUT_SUMMARIES_DIR}", flush=True)


if __name__ == "__main__":
    main()