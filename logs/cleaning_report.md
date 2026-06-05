# Data Cleaning & Transformation Report

**Execution Date:** 2026-06-05 19:47:50
**Date Filter Threshold:** 2026-06-05

## 1. Transaction Table Anomalies

| Anomaly Type | Detected & Resolved Count |
|---|---|
| Duplicates | 231 |
| Negative spends | 208 |
| Future dates | 225 |
| Invalid categories | 10545 |
| Date formats corrected | 214 |

## 2. Offer Views Anomalies

| Anomaly Type | Detected & Resolved Count |
|---|---|
| Type mismatches resolved | 454 |
| Duplicates | 0 |

## 3. Dataset Row Summary

| Dataset | Raw Row Count | Clean Row Count | Rows Excluded | Error Rate |
|---|---|---|---|---|
| transactions | 73291 | 72627 | 664 | 0.91% |
| offer_views | 8483 | 8483 | 0 | 0.00% |
| customers | 1000 | 1000 | 0 | 0.00% |
| merchants | 200 | 200 | 0 | 0.00% |
| email_opens | 921 | 921 | 0 | 0.00% |
| reward_redemptions | 2965 | 2965 | 0 | 0.00% |
| campaign_clicks | 1803 | 1803 | 0 | 0.00% |
