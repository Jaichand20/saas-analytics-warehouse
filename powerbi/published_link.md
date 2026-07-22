# Dashboard Delivery

This dashboard is delivered as a static PDF export (`powerbi/SaaS_Analytics_Dashboard.pdf`) rather than a live Power BI Service link. The `.pbip` project (`SaaS_Analytics_Dashboard.pbip` + `.Report`/`.SemanticModel` folders) is included in full, so the interactive report can be reopened and re-published to Power BI Service at any time by connecting to the `marts` BigQuery dataset via the `powerbi-reader` service account (see `data_model.md`).
