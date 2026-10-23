"""Agent 4: Data Report Crew.

Preserved from Project_4_Data_Report_Crew.ipynb.
"""

from io import StringIO
from pathlib import Path
from typing import Dict, Any, Union

import pandas as pd
from pydantic import BaseModel, Field
from crewai import Agent, Task, Crew, Process
from crewai_tools import FileReadTool

from services.gemini import get_llm
from services.file_storage import FileStorageService


class SalesReport(BaseModel):
    total_records: int = Field(description="Number of sales records")
    total_units_sold: int = Field(description="Total units sold")
    total_revenue: float = Field(description="Total revenue across all records")
    best_selling_product: str = Field(description="Product with the highest total units sold")
    highest_revenue_region: str = Field(description="Region with the highest total revenue")
    average_revenue_per_record: float = Field(description="Average revenue per sales record")


def calculate_ground_truth_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """Computes exact metrics from the dataset to ground the LLM's narrative report."""
    # Normalize column names for flexible matching
    col_map = {col.lower().replace(" ", "_"): col for col in df.columns}

    units_col = col_map.get("units_sold") or col_map.get("units") or col_map.get("quantity")
    rev_col = col_map.get("revenue") or col_map.get("sales") or col_map.get("total_price")
    prod_col = col_map.get("product") or col_map.get("item")
    reg_col = col_map.get("region") or col_map.get("location") or col_map.get("territory")

    metrics = {
        "total_records": int(len(df)),
    }

    if units_col and pd.api.types.is_numeric_dtype(df[units_col]):
        metrics["total_units_sold"] = int(df[units_col].sum())
        if prod_col:
            units_by_prod = df.groupby(prod_col)[units_col].sum()
            metrics["best_selling_product"] = str(units_by_prod.idxmax())
            metrics["best_selling_product_units"] = int(units_by_prod.max())
    else:
        metrics["total_units_sold"] = 0
        metrics["best_selling_product"] = "N/A"
        metrics["best_selling_product_units"] = 0

    if rev_col and pd.api.types.is_numeric_dtype(df[rev_col]):
        metrics["total_revenue"] = float(df[rev_col].sum())
        metrics["average_revenue_per_record"] = float(df[rev_col].mean())
        if prod_col:
            rev_by_prod = df.groupby(prod_col)[rev_col].sum()
            metrics["highest_revenue_product"] = str(rev_by_prod.idxmax())
        if reg_col:
            rev_by_reg = df.groupby(reg_col)[rev_col].sum()
            metrics["highest_revenue_region"] = str(rev_by_reg.idxmax())
            metrics["highest_revenue_region_total"] = float(rev_by_reg.max())
    else:
        metrics["total_revenue"] = 0.0
        metrics["average_revenue_per_record"] = 0.0
        metrics["highest_revenue_product"] = "N/A"
        metrics["highest_revenue_region"] = "N/A"
        metrics["highest_revenue_region_total"] = 0.0

    return metrics


def create_data_report_crew(
    csv_file_path: Path, output_file_path: Path, verified_metrics: Dict[str, Any]
):
    """Instantiates the Data Report Crew with verified metrics and safe paths."""
    llm = get_llm(temperature=0.2)
    file_reader = FileReadTool(file_path=str(csv_file_path))

    data_analyst = Agent(
        role="Sales Data Analyst",
        goal="Analyze sales data accurately and produce structured sales statistics.",
        backstory=(
            "You are a careful data analyst who examines sales records, "
            "calculates business metrics, and identifies product and regional trends. "
            "Use the supplied CSV data and never invent figures."
        ),
        llm=llm,
        tools=[file_reader],
        verbose=False,
    )

    insight_writer = Agent(
        role="Business Insight Writer",
        goal="Convert sales statistics into clear, useful business insights and recommendations.",
        backstory=(
            "You are a business analyst who explains sales trends "
            "in simple language and provides practical recommendations "
            "based only on the available data."
        ),
        llm=llm,
        verbose=False,
    )

    reviewer = Agent(
        role="Sales Report Reviewer",
        goal=(
            "Review the sales report for numerical accuracy, "
            "clarity, consistency, and actionable recommendations."
        ),
        backstory=(
            "You are a meticulous report reviewer. You verify claims "
            "against the supplied analysis, flag unsupported conclusions, "
            "and improve the report's readability."
        ),
        llm=llm,
        verbose=False,
    )

    analysis_task = Task(
        description=f"""
Analyze the sales data stored in {csv_file_path.name}.

Verified ground-truth metrics calculated directly from the dataset:
{verified_metrics}

Instructions:
- Base every calculation and answer on this data.
- Return the structured metrics in the required Pydantic format.
        """,
        expected_output=(
            "A structured sales analysis containing all key metrics derived accurately."
        ),
        agent=data_analyst,
        output_pydantic=SalesReport,
    )

    insight_task = Task(
        description=f"""
Write a professional sales performance report using these
verified metrics calculated directly from {csv_file_path.name}:

{verified_metrics}

Include the following sections:

1. Overall Sales Performance
   - Total records, units sold, total revenue, and average revenue per record.

2. Product Performance
   - Identify the best-selling product by units sold.
   - Identify the product generating the highest revenue.
   - Clearly distinguish units sold from revenue generated.

3. Regional Performance
   - Identify the region with the highest revenue.
   - Include its verified revenue figure.

4. Business Recommendations
   - Provide three practical recommendations supported by the available data.

Rules:
- Use only the verified numerical values supplied above.
- Do not recalculate, modify, or invent statistics.
- Use ₹ or standard currency symbol consistent with records.
- Do not claim sales growth or trends over time unless longitudinal data is present.
- Format the report using clean Markdown headings and bullets.
        """,
        expected_output=(
            "A Markdown sales report containing a summary, key findings, "
            "and three data-supported business recommendations."
        ),
        agent=insight_writer,
        context=[analysis_task],
    )

    review_task = Task(
        description=f"""
Review the draft sales report against these verified metrics:

{verified_metrics}

Check that:
1. Total records, units sold, total revenue, and average revenue match the verified values.
2. The best-selling product by units is correctly identified.
3. The highest-revenue product is correctly identified.
4. The highest-revenue region and its revenue are correct.
5. Every numerical claim is supported by the verified metrics.
6. Recommendations are reasonable and do not claim unsupported sales growth.

Correct every discrepancy and save the complete final report in Markdown to {output_file_path.name}.
        """,
        expected_output="A reviewed, corrected, professional Markdown sales report.",
        agent=reviewer,
        context=[analysis_task, insight_task],
        output_file=str(output_file_path),
    )

    return Crew(
        agents=[data_analyst, insight_writer, reviewer],
        tasks=[analysis_task, insight_task, review_task],
        process=Process.sequential,
        verbose=False,
    )


async def run_data_report(csv_content: Union[str, bytes]) -> Dict[str, Any]:
    """Parses CSV, calculates metrics, runs the Data Report Crew, and returns results."""
    try:
        if isinstance(csv_content, bytes):
            text = csv_content.decode("utf-8")
        else:
            text = str(csv_content)
        df = pd.read_csv(StringIO(text.strip()))
    except Exception as e:
        raise ValueError(f"Failed to parse CSV dataset: {e}")

    if df.empty or len(df.columns) < 2:
        raise ValueError(
            "The uploaded CSV is empty or has fewer than 2 columns. Please provide valid sales data with headers."
        )

    run_id, run_dir = FileStorageService.create_run_dir("data_report")
    csv_file_path = run_dir / "sales.csv"
    output_path = run_dir / "report.md"

    # Save uploaded CSV safely
    csv_file_path.write_text(df.to_csv(index=False), encoding="utf-8")

    # Compute ground truth
    metrics = calculate_ground_truth_metrics(df)

    crew = create_data_report_crew(csv_file_path, output_path, metrics)
    crew_output = await crew.kickoff_async()

    report_content = str(crew_output).strip()
    if not output_path.exists() or output_path.stat().st_size == 0:
        output_path.write_text(report_content, encoding="utf-8")
    else:
        report_content = output_path.read_text(encoding="utf-8")

    # Preview dataframe as records for frontend table display
    sample_preview = df.head(10).to_dict(orient="records")

    return {
        "run_id": run_id,
        "metrics": metrics,
        "content": report_content,
        "preview_data": sample_preview,
        "total_records": len(df),
        "filename": "report.md",
        "download_url": f"/download/{run_id}/report.md",
        "csv_download_url": f"/download/{run_id}/sales.csv",
    }
