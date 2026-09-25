from __future__ import annotations

from app.crawlers.adapters.discourse_ai_jobs import OpenRoboticsJobsAdapter, PyTorchJobsAdapter


class FakeResponse:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self) -> None:
        return None


class FakeDiscourseClient:
    def __init__(self, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def get(self, url: str):
        if url == "https://discourse.openrobotics.org/c/jobs/15.rss":
            return FakeResponse(
                _rss(
                    [
                        {
                            "title": "About the Jobs category",
                            "link": "https://discourse.openrobotics.org/t/about-the-jobs-category/301",
                            "description": "Category rules.",
                        },
                        {
                            "title": "Signal Robotics | Robotics AI Engineer | Remote",
                            "link": "https://discourse.openrobotics.org/t/robotics-ai-engineer/101",
                            "description": (
                                "Build autonomy with ROS2 and computer vision. "
                                '<a href="https://vendor.example">Our technology provider</a> '
                                '<a href="https://signal-robotics.example/careers">Company website</a> '
                                "Email jobs@signal-robotics.example"
                            ),
                        },
                        {
                            "title": "Robot Cloud | ROS2 Engineer | Munich",
                            "link": "https://discourse.openrobotics.org/t/ros2-engineer/102",
                            "description": "Work on ROS2 navigation. Apply through our website.",
                        },
                    ]
                )
            )
        if url == "https://discuss.pytorch.org/c/jobs/24.rss":
            return FakeResponse(
                _rss(
                    [
                        {
                            "title": "ML Engineer looking for work",
                            "link": "https://discuss.pytorch.org/t/ml-engineer-looking-for-work/201",
                            "description": "I am a candidate looking for an ML engineer position.",
                        },
                        {
                            "title": "Model Lab | Deep Learning Engineer | Remote",
                            "link": "https://discuss.pytorch.org/t/deep-learning-engineer/202",
                            "description": "Train PyTorch models. Email hiring@modellab.example",
                        },
                    ]
                )
            )
        raise AssertionError(f"unexpected URL: {url}")


def _rss(items: list[dict[str, str]]) -> str:
    rendered = "".join(
        f"""
        <item>
          <title>{item['title']}</title>
          <link>{item['link']}</link>
          <pubDate>Wed, 23 Sep 2026 19:18:06 +0000</pubDate>
          <description><![CDATA[{item['description']}]]></description>
        </item>
        """
        for item in items
    )
    return f"<?xml version='1.0'?><rss><channel>{rendered}</channel></rss>"


def test_open_robotics_jobs_uses_single_rss_request_and_keeps_hiring_posts(monkeypatch):
    monkeypatch.setattr("app.crawlers.adapters.discourse_ai_jobs.httpx.Client", FakeDiscourseClient)

    jobs = OpenRoboticsJobsAdapter().fetch()

    assert len(jobs) == 2
    first = jobs[0]
    assert first.source_job_id == "101"
    assert first.canonical_url == "https://discourse.openrobotics.org/t/robotics-ai-engineer/101"
    assert first.title == "Signal Robotics | Robotics AI Engineer | Remote"
    assert first.company == "Signal Robotics"
    assert first.remote_type == "remote"
    assert "jobs@signal-robotics.example" in first.description
    assert first.raw_payload == {
        "site": "open_robotics_jobs",
        "topic_slug": "robotics-ai-engineer",
        "category_url": "https://discourse.openrobotics.org/c/jobs/15",
        "company_url": "https://signal-robotics.example/careers",
    }


def test_pytorch_jobs_skips_candidate_posts_and_keeps_hiring_posts(monkeypatch):
    monkeypatch.setattr("app.crawlers.adapters.discourse_ai_jobs.httpx.Client", FakeDiscourseClient)

    jobs = PyTorchJobsAdapter().fetch()

    assert len(jobs) == 1
    job = jobs[0]
    assert job.source_job_id == "202"
    assert job.canonical_url == "https://discuss.pytorch.org/t/deep-learning-engineer/202"
    assert job.company == "Model Lab"
    assert "hiring@modellab.example" in job.description


def test_discourse_ai_job_adapters_are_registered_as_global_adapters():
    from app.crawlers.registry import ADAPTERS

    assert ADAPTERS["open_robotics_jobs"] is OpenRoboticsJobsAdapter
    assert ADAPTERS["pytorch_jobs"] is PyTorchJobsAdapter
