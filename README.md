# Air Quality Monitoring Data Platform

A data platform for aggregating and visualizing air quality metrics from multiple sources.  
Built to explore patterns in air pollution data and make it accessible for analysis.

## Overview

This project was created to combine data engineering, API integration, and visualization while working with real-world environmental data. Air quality data is fragmented across different sources and formats, and this platform aims to centralize it and make it easier to work with.

There is also anecdotal evidence that professional CS2 player Zywoo (Team Vitality) performs worse in highly polluted cities, which motivated an exploratory analysis using air quality data.

## Why This Matters

Beyond technical demonstration, this project explores questions I've faced in production:

- **Cost vs. Performance**: When is Databricks worth the premium over Athena?
- **Vendor Lock-in**: How do we balance convenience with portability?
- **Data Quality at Scale**: What validation patterns work for streaming vs batch?
- **Platform Thinking**: How do we make data accessible without creating a bottleneck?

## Project Evolution

- This project started as a local proof-of-concept but quickly evolvido into a cloud-native platform. The initial approach used SQLite and Python scripts, but doesn't really reflect the kind of systems I've been working with.


## Architecture

- The platform follows a modern data stack approach, using. managed services where appropriate while maintaining control over infrastructure through code.

The data flows from the OpenAQ API through an AWS Lambda function into an S3 raw layer. From there, it is processed in two parallel paths:

1. **Databricks path**: Using Delta Live Tables for transformation and Unity Catalog for governance.
2. **AWS native path**: Using Athena with Iceberg tables and Glue Data Catalog.

The processed data is then served through a Data Products layer to downstream applications, including a FastAPI service, Metabase dashboards, and Databricks SQL.

![Diagram with the project's architecture](docs/diagrams/architecture.png)

## Why This Architecture?

I chose a dual-path approach (Databricks + AWS native) for a few reasons.

The split between Databricks and AWS services reflects a common pattern I've seen: companies standardizing on Databricks for core data engineering while maintaining some AWS-native pipelines for specific use cases.

## Tech Stack

### Infrastructure & Orchestration
- **Terraform**: For infrastructure as code to manage AWS and Databricks resources.
- **AWS**: S3 for storage, Lambda for serverless ingestion, Glue for catalog, Athena for querying.
- **Databricks**: For big data processing with Delta Lake and Unity Catalog.
- **Airflow**: For workflow orchestration (chosen for its modern API and ease of use).

### Data Processing & Storage
- **Apache Iceberg**: Used with Athena for open table format comparisons.
- **Delta Lake**: Used in Databricks for transactionaEl data storage.
- **dbt**: For SQL-based transformations (used with Athena and Databricks).
- **Great Expectations**: For data quality testing.

### Serving & Visualization
- **Metabase**: Open-source BI tool for dashboards.
- **FastAPI**: For building a REST API to serve data.
- **Databricks SQL**: For ad-hoc analysis and reporting.

## Getting Started
### 1. Create your local environment file
```bash
cp .env.example .env
```

Update `.env` with non-default passwords before running Airflow locally.

### 2. Initialize Airflow metadata DB and admin user
```bash
poetry run task init-airflow
```

### 3. Start local services
```bash
poetry run task airflow-local
```

## Documentation
I'll update architecture decision records (ADRs) in the docs/ directory to explain key choices. These are written as if for a team, explaining the context, decision, and consequences.

## Contributing
This is a personal project but feedback is welcome


## License
[MIT]
