import json

from app.services.jdtrust_assessment_read import load_jdtrust_assessments


def test_load_jdtrust_assessments_indexes_combined_assessment_by_legacy_job_id(tmp_path):
    output_path = tmp_path / "assessments.jsonl"
    output_path.write_text(
        json.dumps(
            {
                "legacy_job_id": 42,
                "canonical_url": "https://jobs.example.com/42",
                "source_name": "web3jobs",
                "title": "Growth Lead",
                "company": "OpenGradient",
                "combined_assessment": {
                    "risk_level": "needs_review",
                    "trust_score": 61,
                    "reason_codes": ["missing_company_domain"],
                    "recommended_checks": ["核对官网招聘页"],
                    "evidence_refs": ["apply_link"],
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    assessments = load_jdtrust_assessments(output_path)

    assert assessments[42] == {
        "legacy_job_id": 42,
        "canonical_url": "https://jobs.example.com/42",
        "source_name": "web3jobs",
        "title": "Growth Lead",
        "company": "OpenGradient",
        "risk_level": "needs_review",
        "trust_score": 61,
        "reason_codes": ["missing_company_domain"],
        "recommended_checks": ["核对官网招聘页"],
        "evidence_refs": ["apply_link"],
    }


def test_load_jdtrust_assessments_ignores_malformed_rows(tmp_path):
    output_path = tmp_path / "assessments.jsonl"
    output_path.write_text(
        "\n".join(
            [
                "{bad json",
                json.dumps({"legacy_job_id": "missing assessment"}),
                json.dumps(
                    {
                        "legacy_job_id": 7,
                        "combined_assessment": {
                            "risk_level": "low",
                            "trust_score": 82,
                            "reason_codes": [],
                            "recommended_checks": [],
                            "evidence_refs": [],
                        },
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )

    assessments = load_jdtrust_assessments(output_path)

    assert list(assessments) == [7]


def test_load_jdtrust_assessments_returns_empty_when_path_missing(tmp_path):
    assert load_jdtrust_assessments(tmp_path / "missing.jsonl") == {}


def test_load_jdtrust_assessments_excludes_aijobs_source(tmp_path):
    output_path = tmp_path / "assessments.jsonl"
    output_path.write_text(
        json.dumps(
            {
                "legacy_job_id": 9,
                "source_name": "aijobsnet",
                "company": "Aijobs",
                "combined_assessment": {
                    "risk_level": "needs_review",
                    "trust_score": 61,
                    "reason_codes": ["job_board_identity"],
                    "recommended_checks": ["Verify the employer outside the job board."],
                    "evidence_refs": [],
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    assert load_jdtrust_assessments(output_path) == {}
