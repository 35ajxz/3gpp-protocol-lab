from __future__ import annotations

from logic_fuzz import run_campaign


def main() -> None:
    summary = run_campaign()
    print("---")
    print(f"logic_cases: {summary['case_count']}")
    print(f"logic_findings: {summary['finding_count']}")
    print(f"cases_with_findings: {summary['cases_with_findings']}")
    for key, value in sorted(summary["finding_types"].items()):
        print(f"finding_type[{key}]: {value}")


if __name__ == "__main__":
    main()
