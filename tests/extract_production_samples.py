#!/usr/bin/env python3
"""Extract VAST samples from production logs.

This script extracts real VAST XML responses from production logs
and saves them as test samples, with anonymization.

Usage:
    python extract_production_samples.py

The script will:
1. Read production logs from ~/middleware/logs/
2. Extract VAST XML responses
3. Anonymize personal data
4. Save to tests/production_samples/provider/
"""

import hashlib
import json
import re
import sys
from pathlib import Path


def anonymize_xml(xml: str) -> str:
    """Anonymize personal data in VAST XML.

    Args:
        xml: Original VAST XML

    Returns:
        Anonymized XML
    """
    # Remove or mask device IDs, IPs, etc.
    xml = re.sub(r"device_id=[a-f0-9-]+", "device_id=ANONYMIZED", xml)
    xml = re.sub(r"ip=[\d.]+", "ip=ANONYMIZED", xml)
    xml = re.sub(r"serial=[a-f0-9-]+", "serial=ANONYMIZED", xml)

    # Mask tracking URLs with personal data
    # Keep structure but anonymize identifiers
    xml = re.sub(r"(https?://[^/]+/track/)([a-f0-9-]{32,})", r"\1ANONYMIZED_ID", xml)

    return xml


def extract_from_vast_client_log(
    log_file: Path, output_dir: Path, provider: str = "g.adstrm.ru"
) -> int:
    """Extract VAST XML from vast_client.jsonl log.

    Args:
        log_file: Path to vast_client.jsonl
        output_dir: Output directory
        provider: Provider name for subdirectory

    Returns:
        Number of samples extracted
    """
    provider_dir = output_dir / provider
    provider_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    seen_hashes = set()  # Deduplicate

    print(f"Reading {log_file}...")

    with open(log_file) as f:
        for line_num, line in enumerate(f, 1):
            try:
                data = json.loads(line)

                # Look for XML preview in various fields
                xml = None
                if "response_preview" in data:
                    xml = data["response_preview"]
                elif "vast_response" in data:
                    xml = data["vast_response"]

                if xml and xml.strip().startswith("<?xml"):
                    # Deduplicate based on content hash
                    content_hash = hashlib.md5(xml.encode()).hexdigest()[:8]
                    if content_hash in seen_hashes:
                        continue

                    seen_hashes.add(content_hash)
                    count += 1

                    # Anonymize
                    anonymized = anonymize_xml(xml)

                    # Save
                    output_file = provider_dir / f"vast_sample_{count:03d}_{content_hash}.xml"
                    output_file.write_text(anonymized, encoding="utf-8")

                    if count % 10 == 0:
                        print(f"  Extracted {count} samples...")

            except json.JSONDecodeError:
                continue
            except Exception as e:
                print(f"  Warning: Error on line {line_num}: {e}")
                continue

    return count


def main():
    """Main extraction function."""
    # Paths
    logs_dir = Path.home() / "middleware" / "logs"
    output_dir = Path(__file__).parent / "production_samples"

    if not logs_dir.exists():
        print(f"Error: Logs directory not found: {logs_dir}")
        print("Please ensure production logs are available.")
        sys.exit(1)

    # Extract from vast_client.jsonl
    vast_client_log = logs_dir / "vast_client.jsonl"

    if vast_client_log.exists():
        print(f"\n{'=' * 60}")
        print("Extracting VAST samples from production logs")
        print(f"{'=' * 60}\n")

        count = extract_from_vast_client_log(vast_client_log, output_dir, provider="g.adstrm.ru")

        print(f"\n{'=' * 60}")
        print("✅ Extraction complete!")
        print(f"{'=' * 60}")
        print(f"\nExtracted {count} unique VAST samples")
        print(f"Output directory: {output_dir / 'g.adstrm.ru'}")
        print("\nNext steps:")
        print(f"  1. Review samples in {output_dir / 'g.adstrm.ru'}")
        print("  2. Run tests: pytest tests/production_samples/")
        print("  3. Commit anonymized samples to git")
        print()

    else:
        print(f"Error: {vast_client_log} not found")
        print("\nAvailable log files:")
        for log_file in logs_dir.glob("*.jsonl"):
            print(f"  - {log_file.name}")
        sys.exit(1)


if __name__ == "__main__":
    main()
