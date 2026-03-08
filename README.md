# CDPH Mortality Reporting Pipeline

This project contains a complete Python workflow for monthly mortality reporting using the California Health and Human Services Open Data Portal Statewide Death Profiles dataset.

The pipeline was built to show how I would handle this process in practice from source ingestion through validation, transformation, reporting tables, figures, and a draft narrative summary.

## What this project does

- pulls mortality data from the CHHS CKAN API
- saves a raw snapshot for reproducibility
- validates schema, dates, domains, duplicates, and suppression logic
- creates a cleaned analytic dataset
- generates monthly reporting tables for total population, demographic subgroups, and cause of death
- produces figures, KPI summaries, and a short narrative summary
- includes a simple orchestration script for scheduled reruns when the source data changes

## Project structure

- `scripts/` contains the pipeline scripts
- `data/raw/` stores raw source snapshots
- `data/profiling/` stores dataset profiling outputs
- `data/validation/` stores validation results
- `data/processed/` stores cleaned analytic files
- `outputs/tables/` stores report-ready summary tables
- `outputs/figures/` stores figures for the report
- `outputs/summaries/` stores KPI and metadata summaries
- `outputs/narrative/` stores the text summary for the reporting period
- `logs/` stores pipeline run logs

## Main scripts

- `01_profile_data.py` profiles the source extract
- `02_validate_data.py` runs validation checks
- `03_transform_data.py` builds the clean analytic layer
- `04_generate_report_tables.py` creates report tables
- `05_create_figures_and_narrative.py` creates figures and narrative outputs
- `06_run_monthly_pipeline.py` checks for source updates and runs the full workflow when needed

## How to run

Create and activate a virtual environment, then install the requirements:

```bash
pip install -r requirements.txt
```

## Run the full workflow:
``` bash
python -u scripts/06_run_monthly_pipeline.py
```

You can also run each script individually in order if you want to inspect each stage.

## Notes

This project treats suppressed cells carefully. Rows with Annotation_Code values 1 and 2 are identified as suppressed and are not treated as zero counts in the reporting outputs.

The latest reporting period in this repository is based on the current source extract included in the run outputs.
