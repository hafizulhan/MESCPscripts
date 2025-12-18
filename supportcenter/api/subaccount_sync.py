"""Synchronize sub-accounts (branches) in ManageEngine SupportCenter Plus via API.

This module reads sub-account data from a CSV file and issues POST/PUT requests
against the SupportCenter Plus REST API so you can automate creates and updates.

Key ideas
---------
- Each CSV row is converted into a JSON payload.
- If the CSV contains a ``subaccount_id`` column (or any field name you choose)
  with a value, the script performs an update (PUT). If not, it performs a create
  (POST).
- Additional columns are passed through directly to the API payload, so the CSV
  can describe any custom fields your portal expects.

Usage examples
--------------
Minimal example (create-only):
    python -m supportcenter.api.subaccount_sync \
        --base-url https://icare-mtsm.ddns.net \
        --api-key  YOUR_TECHNICIAN_KEY \
        --csv branches.csv

With portal selection and an alternate ID column:
    python -m supportcenter.api.subaccount_sync \
        --base-url https://icare-mtsm.ddns.net \
        --api-key  YOUR_TECHNICIAN_KEY \
        --portal-id 3 \
        --id-field branch_id \
        --csv branches.csv

Expected CSV headers
--------------------
- ``name`` (recommended): the sub-account/branch display name.
- ``subaccount_id`` (optional): identifier of an existing sub-account to update.
- Any other fields expected by your SupportCenter Plus instance, such as
  ``description``, ``address``, ``phone``.

Authentication
--------------
By default the script sends the API key in the ``TECHNICIAN_KEY`` header. Some
setups prefer ``AUTHTOKEN`` or a custom header; use ``--api-key-header`` to
match your environment.
"""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import requests


DEFAULT_ENDPOINT = "/api/v3/subaccounts"
DEFAULT_ID_FIELD = "subaccount_id"
DEFAULT_API_KEY_HEADER = "TECHNICIAN_KEY"


@dataclass
class SubAccountResult:
    """Represents the outcome of a single upsert operation."""

    payload: Dict[str, str]
    response_status: int
    response_body: Dict[str, object]


class ManageEngineSCPClient:
    """Thin API client for SupportCenter Plus.

    Only the pieces required for sub-account upserts are implemented. Adjust the
    endpoint or headers if your instance differs.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        portal_id: Optional[str] = None,
        api_key_header: str = DEFAULT_API_KEY_HEADER,
        verify_ssl: bool = True,
        endpoint: str = DEFAULT_ENDPOINT,
    ) -> None:
        if base_url.endswith("/"):
            base_url = base_url[:-1]
        self.base_url = base_url
        self.portal_id = portal_id
        self.endpoint = endpoint
        self.session = requests.Session()
        self.session.headers.update(
            {
                api_key_header: api_key,
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )
        self.verify_ssl = verify_ssl

    def upsert_subaccount(
        self, record: Dict[str, str], *, id_field: str = DEFAULT_ID_FIELD
    ) -> SubAccountResult:
        """Create or update a sub-account based on the presence of an ID field."""

        record_id = record.get(id_field) or None
        payload = {k: v for k, v in record.items() if k != id_field and v != ""}
        params = {"portalId": self.portal_id} if self.portal_id else {}

        if record_id:
            url = f"{self.base_url}{self.endpoint}/{record_id}"
            response = self.session.put(url, params=params, data=json.dumps(payload), verify=self.verify_ssl)
        else:
            url = f"{self.base_url}{self.endpoint}"
            response = self.session.post(url, params=params, data=json.dumps(payload), verify=self.verify_ssl)

        try:
            body = response.json()
        except ValueError:
            body = {"raw": response.text}

        return SubAccountResult(payload=payload, response_status=response.status_code, response_body=body)


def load_csv_records(csv_path: Path) -> List[Dict[str, str]]:
    """Load CSV rows into dictionaries.

    Empty cells are converted to empty strings for predictable filtering later.
    """

    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [{key: value or "" for key, value in row.items()} for row in reader]


def sync_subaccounts(
    *,
    csv_path: Path,
    base_url: str,
    api_key: str,
    portal_id: Optional[str] = None,
    id_field: str = DEFAULT_ID_FIELD,
    api_key_header: str = DEFAULT_API_KEY_HEADER,
    endpoint: str = DEFAULT_ENDPOINT,
    verify_ssl: bool = True,
) -> List[SubAccountResult]:
    """Synchronize sub-accounts from a CSV file.

    Returns a list of :class:`SubAccountResult` objects for reporting.
    """

    records = load_csv_records(csv_path)
    client = ManageEngineSCPClient(
        base_url,
        api_key,
        portal_id=portal_id,
        api_key_header=api_key_header,
        verify_ssl=verify_ssl,
        endpoint=endpoint,
    )

    results: List[SubAccountResult] = []
    for record in records:
        result = client.upsert_subaccount(record, id_field=id_field)
        results.append(result)
    return results


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upsert sub-accounts from CSV into ManageEngine SCP")
    parser.add_argument("--base-url", required=True, help="Base URL of the SupportCenter Plus portal, e.g. https://icare-mtsm.ddns.net")
    parser.add_argument("--api-key", required=True, help="Technician key or auth token")
    parser.add_argument("--csv", required=True, type=Path, help="Path to CSV file with sub-account data")
    parser.add_argument("--portal-id", help="Portal ID when multiple portals exist")
    parser.add_argument(
        "--id-field",
        default=DEFAULT_ID_FIELD,
        help=f"CSV column treated as the sub-account ID (default: {DEFAULT_ID_FIELD})",
    )
    parser.add_argument(
        "--endpoint",
        default=DEFAULT_ENDPOINT,
        help=f"API endpoint path for sub-accounts (default: {DEFAULT_ENDPOINT})",
    )
    parser.add_argument(
        "--api-key-header",
        default=DEFAULT_API_KEY_HEADER,
        help=f"Header name used for the API key (default: {DEFAULT_API_KEY_HEADER})",
    )
    parser.add_argument("--insecure", action="store_true", help="Disable TLS certificate verification")
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Optional[Iterable[str]] = None) -> None:
    args = parse_args(argv)
    results = sync_subaccounts(
        csv_path=args.csv,
        base_url=args.base_url,
        api_key=args.api_key,
        portal_id=args.portal_id,
        id_field=args.id_field,
        api_key_header=args.api_key_header,
        endpoint=args.endpoint,
        verify_ssl=not args.insecure,
    )

    created = sum(1 for result in results if result.response_status in {200, 201})
    statuses = [result.response_status for result in results]

    print("Processed rows:", len(results))
    print("HTTP statuses encountered:", {status: statuses.count(status) for status in sorted(set(statuses))})
    for idx, result in enumerate(results, start=1):
        print(f"Row {idx}: HTTP {result.response_status} -> {json.dumps(result.response_body)}")
    if created:
        print(f"Successfully created/updated {created} sub-accounts")


if __name__ == "__main__":
    main()
