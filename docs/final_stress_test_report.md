# Vera AI Challenge — Final Unbiased 200-Case Generalization & Stress Test Report

## 1. Executive Summary

- **Total Cases Evaluated**: `200`
- **Mean Score**: `49.95 / 50`
- **Median Score**: `50.0 / 50`
- **Minimum Score**: `49 / 50`
- **Maximum Score**: `50 / 50`
- **Standard Deviation**: `0.23`
- **Perfect 50/50 Count**: `189 / 200 (94.5%)`

## 2. Dimension Averages

- **Decision Quality**: `10.00 / 10`
- **Specificity**: `10.00 / 10`
- **Category Fit**: `10.00 / 10`
- **Merchant Fit**: `9.95 / 10`
- **Engagement**: `10.00 / 10`

## 3. Safety Invariants & Adversarial Defense

- **Hallucinations**: `0` (0 = 100% Secure)
- **Taboo Violations**: `0` (0 = 100% Secure)
- **Unauthorized Actions**: `0` (0 = 100% Secure)
- **Opt Out Violations**: `0` (0 = 100% Secure)
- **Terminal State Violations**: `0` (0 = 100% Secure)
- **Replay Violations**: `0` (0 = 100% Secure)

## 4. Pipeline Loss Attribution

- **INPUT**: `11 points lost`

## 5. Performance by Archetype Distribution

| Archetype Group | Case Count | Average Score / 50 | Perfect Rate |
| :--- | :---: | :---: | :---: |
| `autoreply_flood` | 2 | **50.00** | 100.0% |
| `compound_opt_out` | 3 | **50.00** | 100.0% |
| `cross_category_probe` | 2 | **50.00** | 100.0% |
| `double_negative` | 2 | **50.00** | 100.0% |
| `expired_trigger` | 2 | **50.00** | 100.0% |
| `external_action_claim` | 3 | **50.00** | 100.0% |
| `financial_confidentiality` | 2 | **50.00** | 100.0% |
| `flow_01_affirmation` | 5 | **50.00** | 100.0% |
| `flow_02_factual_inquiry_sample_size` | 5 | **50.00** | 100.0% |
| `flow_03_who_are_you` | 5 | **50.00** | 100.0% |
| `flow_04_out_of_scope_tax` | 5 | **50.00** | 100.0% |
| `flow_05_rejection` | 5 | **50.00** | 100.0% |
| `flow_06_opt_out` | 5 | **50.00** | 100.0% |
| `flow_07_auto_reply_first` | 5 | **50.00** | 100.0% |
| `flow_08_ambiguous_maybe` | 5 | **50.00** | 100.0% |
| `hostile_opt_out` | 3 | **50.00** | 100.0% |
| `injection_code` | 2 | **50.00** | 100.0% |
| `jailbreak` | 3 | **50.00** | 100.0% |
| `missing_identity` | 11 | **49.00** | 0.0% |
| `pii_phishing` | 2 | **50.00** | 100.0% |
| `polite_rejection` | 2 | **50.00** | 100.0% |
| `prompt_injection` | 3 | **50.00** | 100.0% |
| `questioning_affirmation` | 3 | **50.00** | 100.0% |
| `rich` | 31 | **50.00** | 100.0% |
| `sql_injection` | 2 | **50.00** | 100.0% |
| `standard` | 66 | **50.00** | 100.0% |
| `subtle_opt_out` | 3 | **50.00** | 100.0% |
| `taboo_bypass` | 2 | **50.00** | 100.0% |
| `taboo_trap` | 3 | **50.00** | 100.0% |
| `terminal_state_revival` | 2 | **50.00** | 100.0% |
| `unauthorized_action` | 3 | **50.00** | 100.0% |
| `uncertainty` | 3 | **50.00** | 100.0% |
