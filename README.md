# MESCPscripts

A personal repository for **ManageEngine Support Center Plus (SCP) automation scripts**, primarily focused on **Deluge scripts** and related snippets. This repository exists to document, store, and share reusable automation logic that solves operational problems — either for my own future reference or for others who may find it useful.

## Purpose
This repository centralizes those scripts so they are:
- reusable
- reviewable
- shareable
- easier to improve over time

Think of this as a **field notebook for ManageEngine automation**.

## Repository Structure
The structure may evolve, but generally follows this idea:
```text
/
├── supportcenter/
│   ├── deluge/
│   ├── api/
├── examples/
└── README.md
```

## Sub-account sync helper

Located at `supportcenter/api/subaccount_sync.py`, this helper reads a CSV file and creates or updates sub-accounts (branches) via the SupportCenter Plus REST API.

Quick start:

```bash
python -m supportcenter.api.subaccount_sync \
  --base-url https://icare-mtsm.ddns.net \
  --api-key  YOUR_TECHNICIAN_KEY \
  --portal-id 3 \  # optional when multiple portals exist
  --csv examples/sample_subaccounts.csv
```

Useful flags:

- `--id-field`: CSV column name used as the existing sub-account identifier when performing updates (defaults to `subaccount_id`).
- `--api-key-header`: Header name for the API key if your instance uses a non-default header (defaults to `TECHNICIAN_KEY`).
- `--endpoint`: Override the sub-account endpoint path if your deployment uses a different REST path.

The bundled `examples/sample_subaccounts.csv` demonstrates the expected CSV shape. Provide any additional columns your portal requires; they are forwarded directly to the API payload.
