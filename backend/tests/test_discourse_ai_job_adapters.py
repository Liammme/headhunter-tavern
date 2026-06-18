from __future__ import annotations

from app.crawlers.adapters.discourse_ai_jobs import OpenRoboticsJobsAdapter, PyTorchJobsAdapter


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self._payload


class FakeDiscourseClient:
    def __init__(self, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def get(self, url: str):
        if url == "https://discourse.openrobotics.org/c/jobs/15.json":
            return FakeResponse(
                {
                    "topic_list": {
                        "topics": [
                            {
                                "id": 301,
                                "slug": "about-the-jobs-category",
                                "title": "About the Jobs category",
                            },
                            {
                                "id": 101,
                                "slug": "robotics-ai-engineer",
                                "title": "Signal Robotics | Robotics AI Engineer | Remote",
                                "created_at": "2026-06-17T12:00:00Z",
                            },
                            {
                                "id": 102,
                                "slug": "ros2-engineer",
                                "title": "Robot Cloud | ROS2 Engineer | Munich",
                            },
                        ]
                    }
                }
            )
        if url == "https://discourse.openrobotics.org/t/robotics-ai-engineer/101.json":
            return FakeResponse(
                {
                    "post_stream": {
                        "posts": [
                            {
                                "cooked": "<p>Build autonomy with ROS2 and computer vision. Email jobs@signal-robotics.example</p>",
                            }
                        ]
                    }
                }
            )
        if url == "https://discourse.openrobotics.org/t/ros2-engineer/102.json":
            return FakeResponse(
                {
                    "post_stream": {
                        "posts": [
                            {
                                "cooked": "<p>Work on ROS2 navigation. Apply through our website.</p>",
                            }
                        ]
                    }
                }
            )
        if url == "https://discuss.pytorch.org/c/jobs/24.json":
            return FakeResponse(
                {
                    "topic_list": {
                        "topics": [
                            {
                                "id": 201,
                                "slug": "ml-engineer-looking-for-work",
                                "title": "ML Engineer looking for work",
                            },
                            {
                                "id": 202,
                                "slug": "deep-learning-engineer",
                                "title": "Model Lab | Deep Learning Engineer | Remote",
                                "created_at": "2026-06-15T08:30:00Z",
                            },
                            {
                                "id": 203,
                                "slug": "ai-community-manager",
                                "title": "Community Lab | AI Community Manager | Remote",
                            },
                        ]
                    }
                }
            )
        if url == "https://discuss.pytorch.org/t/ml-engineer-looking-for-work/201.json":
            return FakeResponse(
                {
                    "post_stream": {
                        "posts": [
                            {
                                "cooked": "<p>I am a candidate looking for an ML engineer position. Email me@example.com</p>",
                            }
                        ]
                    }
                }
            )
        if url == "https://discuss.pytorch.org/t/deep-learning-engineer/202.json":
            return FakeResponse(
                {
                    "post_stream": {
                        "posts": [
                            {
                                "cooked": "<p>Train PyTorch models for production inference. Email hiring@modellab.example</p>",
                            }
                        ]
                    }
                }
            )
        if url == "https://discuss.pytorch.org/t/ai-community-manager/203.json":
            return FakeResponse(
                {
                    "post_stream": {
                        "posts": [
                            {
                                "cooked": "<p>Manage our AI Discord community. Apply through our website.</p>",
                            }
                        ]
                    }
                }
            )
        raise AssertionError(f"unexpected URL: {url}")


def test_open_robotics_jobs_fetches_robotics_posts_with_direct_contacts(monkeypatch):
    monkeypatch.setattr("app.crawlers.adapters.discourse_ai_jobs.httpx.Client", FakeDiscourseClient)

    jobs = OpenRoboticsJobsAdapter().fetch()

    assert len(jobs) == 1
    job = jobs[0]
    assert job.source_job_id == "101"
    assert job.canonical_url == "https://discourse.openrobotics.org/t/robotics-ai-engineer/101"
    assert job.title == "Signal Robotics | Robotics AI Engineer | Remote"
    assert job.company == "Signal Robotics"
    assert job.remote_type == "remote"
    assert "jobs@signal-robotics.example" in job.description
    assert job.raw_payload == {
        "site": "open_robotics_jobs",
        "topic_slug": "robotics-ai-engineer",
        "category_url": "https://discourse.openrobotics.org/c/jobs/15",
        "company_url": "",
    }


def test_pytorch_jobs_skips_candidate_posts_and_keeps_hiring_contacts(monkeypatch):
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
