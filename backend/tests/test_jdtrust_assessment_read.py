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
        "domain_warnings": [],
        "verification_tags": [],
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


def test_load_jdtrust_assessments_extracts_only_abnormal_domain_facts(tmp_path):
    output_path = tmp_path / "assessments.jsonl"
    output_path.write_text(
        json.dumps(
            {
                "legacy_job_id": 11,
                "combined_assessment": {
                    "risk_level": "needs_review",
                    "trust_score": 64,
                    "reason_codes": [],
                    "recommended_checks": [],
                    "evidence_refs": [],
                },
                "link_facts": [
                    {
                        "kind": "company_url",
                        "domain": "opengradient.ai",
                        "url": "https://opengradient.ai",
                    }
                ],
                "reputation_facts": [
                    {
                        "fact_name": "email_domain_status",
                        "fact_value": "mx_missing",
                        "note": "email domain has no MX record",
                    },
                    {
                        "fact_name": "domain_age_status",
                        "fact_value": "established",
                        "note": "domain is older than 90 days",
                    },
                    {
                        "fact_name": "domain_age_status",
                        "fact_value": "new_domain_30d",
                        "domain": "opengradient.ai",
                        "note": "domain registered recently",
                    },
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    assessments = load_jdtrust_assessments(output_path)

    assert assessments[11]["domain_warnings"] == [
        {
            "fact_name": "email_domain_status",
            "fact_value": "mx_missing",
            "label": "邮箱域名缺少 MX 记录",
        },
        {
            "fact_name": "domain_age_status",
            "fact_value": "new_domain_30d",
            "label": "项目域名注册未满 30 天",
        },
    ]


def test_load_jdtrust_assessments_does_not_show_source_site_domain_age_as_project_domain(tmp_path):
    output_path = tmp_path / "assessments.jsonl"
    output_path.write_text(
        json.dumps(
            {
                "legacy_job_id": 13,
                "canonical_url": "https://cryptocurrencyjobs.co/engineering/risk-labs-analytics-engineer/",
                "combined_assessment": {
                    "risk_level": "needs_review",
                    "trust_score": 64,
                    "reason_codes": [],
                    "recommended_checks": [],
                    "evidence_refs": [],
                },
                "link_facts": [
                    {
                        "kind": "company_url",
                        "domain": "ethena.fi",
                        "url": "https://www.ethena.fi/",
                    },
                    {
                        "kind": "company_url",
                        "domain": "cryptocurrencyjobs.co",
                        "url": "https://cryptocurrencyjobs.co/startups/ethena-labs/",
                    },
                ],
                "reputation_facts": [
                    {
                        "fact_name": "domain_age_status",
                        "fact_value": "new_domain_30d",
                        "domain": "cryptocurrencyjobs.co",
                        "note": "source site domain should not be treated as project domain",
                    },
                    {
                        "fact_name": "domain_age_status",
                        "fact_value": "new_domain_90d",
                        "domain": "ethena.fi",
                        "note": "project website domain registered recently",
                    },
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    assessments = load_jdtrust_assessments(output_path)

    assert assessments[13]["domain_warnings"] == [
        {
            "fact_name": "domain_age_status",
            "fact_value": "new_domain_90d",
            "label": "项目域名注册未满 90 天",
        }
    ]
    assert assessments[13]["verification_tags"] == [
        {
            "label": "项目域名注册未满 90 天",
            "tone": "warning",
            "description": "项目相关域名注册时间较短，建议结合其他证据判断。",
        }
    ]


def test_load_jdtrust_assessments_shows_project_website_domain_age_only_when_official_site_is_found(tmp_path):
    output_path = tmp_path / "assessments.jsonl"
    output_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "legacy_job_id": 14,
                        "canonical_url": "https://cryptocurrencyjobs.co/engineering/ethena-labs/",
                        "combined_assessment": {
                            "risk_level": "low",
                            "trust_score": 90,
                            "reason_codes": [],
                            "recommended_checks": [],
                            "evidence_refs": [],
                        },
                        "link_facts": [
                            {
                                "kind": "company_url",
                                "domain": "ethena.fi",
                                "url": "https://www.ethena.fi/",
                            }
                        ],
                        "reputation_facts": [
                            {
                                "fact_name": "domain_age_status",
                                "fact_value": "established",
                                "domain": "ethena.fi",
                                "domain_age_days": 420,
                            }
                        ],
                    }
                ),
                json.dumps(
                    {
                        "legacy_job_id": 15,
                        "canonical_url": "https://cryptocurrencyjobs.co/engineering/risk-labs/",
                        "combined_assessment": {
                            "risk_level": "needs_review",
                            "trust_score": 70,
                            "reason_codes": [],
                            "recommended_checks": [],
                            "evidence_refs": [],
                        },
                        "link_facts": [
                            {
                                "kind": "company_url",
                                "domain": "cryptocurrencyjobs.co",
                                "url": "https://cryptocurrencyjobs.co/startups/risk-labs/",
                            }
                        ],
                        "reputation_facts": [
                            {
                                "fact_name": "domain_age_status",
                                "fact_value": "established",
                                "domain": "cryptocurrencyjobs.co",
                                "domain_age_days": 420,
                            }
                        ],
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    assessments = load_jdtrust_assessments(output_path)

    assert assessments[14]["verification_tags"] == [
        {
            "label": "官网域名注册超过 1 年",
            "tone": "positive",
            "description": "原帖抓到了项目官网，并确认该官网域名注册时间超过 1 年。",
        }
    ]
    assert assessments[15]["verification_tags"] == []


def test_load_jdtrust_assessments_combines_split_domain_age_facts(tmp_path):
    output_path = tmp_path / "assessments.jsonl"
    output_path.write_text(
        json.dumps(
            {
                "legacy_job_id": 16,
                "canonical_url": "https://dejob.ai/jobDetail?id=6882",
                "combined_assessment": {
                    "risk_level": "low",
                    "trust_score": 90,
                    "reason_codes": [],
                    "recommended_checks": [],
                    "evidence_refs": [],
                },
                "link_facts": [
                    {
                        "kind": "company_url",
                        "domain": "fermah.xyz",
                        "url": "https://fermah.xyz/",
                    }
                ],
                "reputation_facts": [
                    {
                        "fact_name": "domain_age_status",
                        "fact_value": "established",
                    },
                    {
                        "fact_name": "domain_age_domain",
                        "fact_value": "fermah.xyz",
                    },
                    {
                        "fact_name": "domain_age_days",
                        "fact_value": "664",
                    },
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    assessments = load_jdtrust_assessments(output_path)

    assert assessments[16]["verification_tags"] == [
        {
            "label": "官网域名注册超过 1 年",
            "tone": "positive",
            "description": "原帖抓到了项目官网，并确认该官网域名注册时间超过 1 年。",
        }
    ]


def test_load_jdtrust_assessments_builds_job_level_verification_tags_from_validation_results(tmp_path):
    output_path = tmp_path / "assessments.jsonl"
    output_path.write_text(
        json.dumps(
            {
                "legacy_job_id": 12,
                "evidence": {"is_accessible": True},
                "link_facts": [
                    {
                        "kind": "ats_ashby",
                        "is_same_domain": False,
                    }
                ],
                "combined_assessment": {
                    "risk_level": "needs_review",
                    "trust_score": 77,
                    "reason_codes": ["rootdata_status_not_found", "identity_evidence_thin"],
                    "recommended_checks": [],
                    "evidence_refs": [],
                },
                "reputation_facts": [
                    {"fact_name": "rootdata_status", "fact_value": "not_found"},
                    {"fact_name": "identity_evidence", "fact_value": "thin"},
                    {"fact_name": "domain_age_status", "fact_value": "established"},
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    assessments = load_jdtrust_assessments(output_path)

    assert assessments[12]["verification_tags"] == [
        {
            "label": "RootData未命中",
            "tone": "warning",
            "description": "RootData 未找到匹配记录，不代表一定有风险，但需要更多外部佐证。",
        },
        {
            "label": "身份链偏薄",
            "tone": "warning",
            "description": "当前岗位页缺少足够的公司/项目外部佐证，建议进一步核验。",
        },
    ]
