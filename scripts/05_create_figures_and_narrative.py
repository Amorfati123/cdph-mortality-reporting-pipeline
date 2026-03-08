from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_TABLES_DIR = PROJECT_ROOT / "outputs" / "tables"
OUTPUT_SUMMARIES_DIR = PROJECT_ROOT / "outputs" / "summaries"
OUTPUT_FIGURES_DIR = PROJECT_ROOT / "outputs" / "figures"
OUTPUT_NARRATIVE_DIR = PROJECT_ROOT / "outputs" / "narrative"

OUTPUT_FIGURES_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_NARRATIVE_DIR.mkdir(parents=True, exist_ok=True)


def load_table(file_name: str, parse_dates=None) -> pd.DataFrame:
    file_path = OUTPUT_TABLES_DIR / file_name
    if not file_path.exists():
        raise FileNotFoundError(f"Expected file not found: {file_path}")
    return pd.read_csv(file_path, parse_dates=parse_dates)


def load_cleaned_data() -> pd.DataFrame:
    file_path = PROCESSED_DIR / "mortality_cleaned.csv"
    if not file_path.exists():
        raise FileNotFoundError(f"Expected file not found: {file_path}")
    return pd.read_csv(
        file_path,
        parse_dates=["report_month", "data_extract_date", "data_revision_date"]
    )


def save_figure(file_name: str) -> None:
    plt.tight_layout()
    plt.savefig(OUTPUT_FIGURES_DIR / file_name, dpi=300, bbox_inches="tight")
    plt.close()


def save_table_figure(df: pd.DataFrame, title: str, file_name: str) -> None:
    fig, ax = plt.subplots(figsize=(12, max(2.2, 0.7 * len(df) + 1.2)))
    ax.axis("off")
    ax.set_title(title, fontsize=12, pad=12)

    display_df = df.copy()
    for col in display_df.columns:
        if pd.api.types.is_datetime64_any_dtype(display_df[col]):
            display_df[col] = display_df[col].dt.strftime("%Y-%m-%d")

    table = ax.table(
        cellText=display_df.values,
        colLabels=display_df.columns,
        cellLoc="center",
        loc="center"
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.4)

    save_figure(file_name)


def create_all_cause_trend_chart() -> None:
    df = load_table("monthly_total_population_all_cause.csv", parse_dates=["report_month"])
    df = df.sort_values("report_month")

    plt.figure(figsize=(10, 5))
    plt.plot(df["report_month"], df["deaths"], marker="o")
    plt.title("California Monthly All-Cause Deaths, Total Population")
    plt.xlabel("Reporting Month")
    plt.ylabel("Deaths")
    plt.grid(True, alpha=0.3)
    save_figure("figure_1_total_population_all_cause_trend.png")


def create_top_causes_chart() -> None:
    df = load_table("latest_month_top_causes_total_population.csv", parse_dates=["report_month"])
    df = df.head(10).sort_values("deaths", ascending=True)

    plt.figure(figsize=(10, 6))
    plt.barh(df["Cause_Desc"], df["deaths"])
    plt.title("Top 10 Causes of Death in Latest Reporting Month")
    plt.xlabel("Deaths")
    plt.ylabel("Cause of Death")
    save_figure("figure_2_latest_month_top_10_causes.png")


def create_gender_trend_chart() -> None:
    df = load_table("monthly_gender_all_cause.csv", parse_dates=["report_month"])
    df = df.sort_values(["gender", "report_month"])

    plt.figure(figsize=(10, 5))
    for gender, group in df.groupby("gender"):
        plt.plot(group["report_month"], group["deaths"], marker="o", label=gender)

    plt.title("Monthly All-Cause Deaths by Gender")
    plt.xlabel("Reporting Month")
    plt.ylabel("Deaths")
    plt.legend(title="Gender")
    plt.grid(True, alpha=0.3)
    save_figure("figure_3_gender_all_cause_trend.png")


def create_latest_age_chart() -> None:
    df = load_table("monthly_age_all_cause.csv", parse_dates=["report_month"])
    latest_month = df["report_month"].max()
    latest_df = df[df["report_month"] == latest_month].copy()

    age_order = [
        "Under 1 year",
        "1-4 years",
        "5-14 years",
        "15-24 years",
        "25-34 years",
        "35-44 years",
        "45-54 years",
        "55-64 years",
        "65-74 years",
        "75-84 years",
        "85 years and over",
    ]

    latest_df["age_group"] = pd.Categorical(
        latest_df["age_group"],
        categories=age_order,
        ordered=True
    )
    latest_df = latest_df.sort_values("age_group")

    plt.figure(figsize=(11, 5))
    plt.bar(latest_df["age_group"].astype(str), latest_df["deaths"])
    plt.title(f"All-Cause Deaths by Age Group ({latest_month.strftime('%Y-%m')})")
    plt.xlabel("Age Group")
    plt.ylabel("Deaths")
    plt.xticks(rotation=45, ha="right")
    save_figure("figure_4_latest_month_age_distribution.png")


def create_latest_race_ethnicity_chart() -> None:
    df = load_table("monthly_race_ethnicity_all_cause.csv", parse_dates=["report_month"])
    latest_month = df["report_month"].max()
    latest_df = df[df["report_month"] == latest_month].copy()
    latest_df = latest_df.sort_values("deaths", ascending=True)

    plt.figure(figsize=(10, 6))
    plt.barh(latest_df["race_ethnicity"], latest_df["deaths"])
    plt.title(f"All-Cause Deaths by Race-Ethnicity ({latest_month.strftime('%Y-%m')})")
    plt.xlabel("Deaths")
    plt.ylabel("Race-Ethnicity")
    save_figure("figure_5_latest_month_race_ethnicity_distribution.png")


def create_kpi_summary_table() -> None:
    mom = pd.read_csv(OUTPUT_TABLES_DIR / "latest_vs_previous_month_total_population_all_cause.csv")
    yoy = pd.read_csv(OUTPUT_TABLES_DIR / "latest_vs_prior_year_total_population_all_cause.csv")

    kpi_df = pd.DataFrame(
        {
            "metric": [
                "Latest reporting month",
                "Latest all-cause deaths",
                "Previous month",
                "Previous month all-cause deaths",
                "Month-over-month absolute change",
                "Month-over-month percent change",
                "Same month prior year",
                "Same month prior-year deaths",
                "Year-over-year absolute change",
                "Year-over-year percent change",
            ],
            "value": [
                mom.loc[0, "latest_month"][:7],
                f"{mom.loc[0, 'latest_deaths']:,.0f}",
                mom.loc[0, "previous_month"][:7],
                f"{mom.loc[0, 'previous_month_deaths']:,.0f}",
                f"{mom.loc[0, 'absolute_change']:,.0f}",
                f"{mom.loc[0, 'percent_change']:.2f}%",
                yoy.loc[0, "prior_year_same_month"][:7],
                f"{yoy.loc[0, 'prior_year_same_month_deaths']:,.0f}",
                f"{yoy.loc[0, 'absolute_change']:,.0f}",
                f"{yoy.loc[0, 'percent_change']:.2f}%",
            ],
        }
    )

    kpi_df.to_csv(OUTPUT_SUMMARIES_DIR / "kpi_summary_table.csv", index=False)
    save_table_figure(
        kpi_df,
        "KPI Summary for Latest Reporting Month",
        "figure_6_kpi_summary_table.png"
    )


def create_data_quality_metadata_table() -> None:
    df = load_cleaned_data()

    extract_date = df["data_extract_date"].dropna().max()
    revision_date = df["data_revision_date"].dropna().max()
    latest_month = df["report_month"].dropna().max()
    earliest_month = df["report_month"].dropna().min()

    quality_df = pd.DataFrame(
        {
            "metric": [
                "Source dataset",
                "Raw extract row count",
                "Processed row count",
                "Suppressed rows",
                "Unsuppressed rows",
                "Suppressed row percent",
                "Earliest reporting month",
                "Latest reporting month",
                "Data extract date",
                "Data revision date",
                "Geography type values",
                "ICD revision values",
                "Strata values",
            ],
            "value": [
                "CHHS Statewide Death Profiles",
                f"{len(df):,}",
                f"{len(df):,}",
                f"{int(df['is_suppressed'].sum()):,}",
                f"{int((~df['is_suppressed']).sum()):,}",
                f"{(df['is_suppressed'].mean() * 100):.2f}%",
                earliest_month.strftime("%Y-%m"),
                latest_month.strftime("%Y-%m"),
                extract_date.strftime("%Y-%m-%d"),
                revision_date.strftime("%Y-%m-%d"),
                ", ".join(sorted(df["Geography_Type"].dropna().astype(str).unique())),
                ", ".join(sorted(df["ICD_Revision"].dropna().astype(str).unique())),
                ", ".join(sorted(df["Strata"].dropna().astype(str).unique())),
            ],
        }
    )

    quality_df.to_csv(OUTPUT_SUMMARIES_DIR / "data_quality_metadata_summary_table.csv", index=False)
    save_table_figure(
        quality_df,
        "Data Quality and Extract Metadata Summary",
        "figure_7_data_quality_metadata_table.png"
    )


def create_narrative_summary() -> None:
    latest_summary = pd.read_csv(OUTPUT_TABLES_DIR / "latest_vs_previous_month_total_population_all_cause.csv")
    yoy_summary = pd.read_csv(OUTPUT_TABLES_DIR / "latest_vs_prior_year_total_population_all_cause.csv")
    top_causes = pd.read_csv(OUTPUT_TABLES_DIR / "latest_month_top_causes_total_population.csv").head(5)
    df_clean = load_cleaned_data()

    latest_month = latest_summary.loc[0, "latest_month"][:7]
    latest_deaths = latest_summary.loc[0, "latest_deaths"]
    mom_abs = latest_summary.loc[0, "absolute_change"]
    mom_pct = latest_summary.loc[0, "percent_change"]
    yoy_abs = yoy_summary.loc[0, "absolute_change"]
    yoy_pct = yoy_summary.loc[0, "percent_change"]
    suppressed_n = int(df_clean["is_suppressed"].sum())
    extract_date = df_clean["data_extract_date"].dropna().max().strftime("%Y-%m-%d")
    revision_date = df_clean["data_revision_date"].dropna().max().strftime("%Y-%m-%d")

    lines = []
    lines.append(f"Latest reporting month: {latest_month}")
    lines.append(f"All-cause deaths in latest month: {latest_deaths:,.0f}")
    lines.append(f"Compared with the previous month, deaths changed by {mom_abs:,.0f} ({mom_pct:.2f}%).")
    lines.append(f"Compared with the same month in the prior year, deaths changed by {yoy_abs:,.0f} ({yoy_pct:.2f}%).")
    lines.append("")
    lines.append("Top 5 causes of death in the latest month:")
    for _, row in top_causes.iterrows():
        lines.append(
            f"{int(row['rank'])}. {row['Cause_Desc']} - {row['deaths']:,.0f} deaths "
            f"({row['share_of_total_pct']:.2f}% of all-cause deaths)"
        )
    lines.append("")
    lines.append(f"Suppressed rows excluded from direct numeric interpretation: {suppressed_n:,}")
    lines.append(f"Data extract date: {extract_date}")
    lines.append(f"Data revision date: {revision_date}")
    lines.append("The latest reporting month should be considered provisional because the source dataset is revised monthly.")

    narrative_file = OUTPUT_NARRATIVE_DIR / "monthly_narrative_summary.txt"
    with open(narrative_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    print("Creating figures and narrative summary...", flush=True)

    create_all_cause_trend_chart()
    create_top_causes_chart()
    create_gender_trend_chart()
    create_latest_age_chart()
    create_latest_race_ethnicity_chart()
    create_kpi_summary_table()
    create_data_quality_metadata_table()
    create_narrative_summary()

    print("Step 5 complete.", flush=True)
    print(f"Figures saved to: {OUTPUT_FIGURES_DIR}", flush=True)
    print(f"Narrative summary saved to: {OUTPUT_NARRATIVE_DIR}", flush=True)
    print(f"Summary tables saved to: {OUTPUT_SUMMARIES_DIR}", flush=True)


if __name__ == "__main__":
    main()