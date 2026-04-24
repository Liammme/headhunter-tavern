from app.crawlers.adapters.abetterweb3 import (
    _build_jobs_from_blocks,
    _extract_collection_and_view,
)


def test_extract_collection_and_view_supports_nested_notion_values():
    record_map = {
        "collection": {
            "nav-collection": {
                "value": {
                    "value": {
                        "id": "nav-collection",
                        "schema": {
                            "title": {
                                "name": "Name",
                            }
                        },
                    }
                }
            },
            "jobs-collection": {
                "value": {
                    "value": {
                        "id": "jobs-collection",
                        "schema": {
                            "company": {"name": "项目/公司"},
                            "role": {"name": "岗位需求"},
                            "apply": {"name": "投递"},
                        },
                    }
                }
            },
        },
        "collection_view": {
            "nav-view": {
                "value": {
                    "value": {
                        "id": "nav-view",
                        "type": "gallery",
                        "name": "导航",
                        "format": {
                            "collection_pointer": {
                                "id": "nav-collection",
                            }
                        },
                    }
                }
            },
            "jobs-view": {
                "value": {
                    "value": {
                        "id": "jobs-view",
                        "type": "table",
                        "name": "最近编辑",
                        "format": {
                            "collection_pointer": {
                                "id": "jobs-collection",
                            }
                        },
                    }
                }
            },
        },
    }

    collection_id, view_id, schema = _extract_collection_and_view(record_map)

    assert collection_id == "jobs-collection"
    assert view_id == "jobs-view"
    assert set(schema) == {"company", "role", "apply"}


def test_build_jobs_from_blocks_supports_nested_notion_values():
    schema = {
        "company": {"name": "项目/公司"},
        "role": {"name": "岗位需求"},
        "apply": {"name": "投递"},
        "source": {"name": "来源"},
        "remote": {"name": "远程"},
        "location": {"name": "办公区域"},
    }
    blocks = {
        "job-1": {
            "value": {
                "value": {
                    "id": "job-1",
                    "type": "page",
                    "parent_table": "collection",
                    "parent_id": "jobs-collection",
                    "created_time": 1_776_271_323_673,
                    "properties": {
                        "company": [["Acme"]],
                        "role": [["Growth Manager"]],
                        "apply": [["jobs@acme.com"]],
                        "source": [["https://example.com/post"]],
                        "remote": [["Yes"]],
                        "location": [["Remote"]],
                    },
                }
            }
        }
    }

    jobs = _build_jobs_from_blocks(blocks, "jobs-collection", schema)

    assert len(jobs) == 1
    assert jobs[0].company == "Acme"
    assert jobs[0].title == "Growth Manager"
    assert jobs[0].remote_type == "remote"
    assert jobs[0].canonical_url == "https://example.com/post"
