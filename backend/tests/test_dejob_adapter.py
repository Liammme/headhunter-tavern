from app.crawlers.adapters.dejob import _build_jobs


def test_dejob_build_jobs_includes_salary_range_from_structured_fields():
    jobs = _build_jobs(
        [
            {
                "topicId": 6839,
                "url": "https://dejob.ai/jobDetail?id=6839",
                "positionName": "Business Development",
                "company": "Viabtc",
                "content": "Build partner channels.",
                "content2": "Own affiliate growth.",
                "content3": "Festival reward, remote working environment.",
                "minSalary": 2500,
                "maxSalary": 5000,
                "officeModeName": "Remote",
                "workTypeName": "Full Time",
            }
        ]
    )

    assert len(jobs) == 1
    assert "Salary range: USD 2,500 - 5,000 / month." in jobs[0].description
    assert "Build partner channels." in jobs[0].description


def test_dejob_build_jobs_treats_one_dollar_floor_as_open_salary_range():
    jobs = _build_jobs(
        [
            {
                "topicId": 6838,
                "url": "https://dejob.ai/jobDetail?id=6838",
                "positionName": "Technical Researcher",
                "company": "Sec3",
                "content": "Research Solana security.",
                "minSalary": 1,
                "maxSalary": 2000,
                "officeModeName": "Remote",
                "workTypeName": "Part Time",
            }
        ]
    )

    assert len(jobs) == 1
    assert "Salary range: USD 0 - 2,000 / month." in jobs[0].description


def test_dejob_build_jobs_ignores_tiny_placeholder_salary_values():
    jobs = _build_jobs(
        [
            {
                "topicId": 6840,
                "url": "https://dejob.ai/jobDetail?id=6840",
                "positionName": "Community Intern",
                "company": "Placeholder Labs",
                "content": "Manage community posts.",
                "minSalary": 0.1,
                "maxSalary": 0.9,
                "officeModeName": "Remote",
                "workTypeName": "Part Time",
            }
        ]
    )

    assert len(jobs) == 1
    assert "Salary range:" not in jobs[0].description
    assert "Manage community posts." in jobs[0].description
