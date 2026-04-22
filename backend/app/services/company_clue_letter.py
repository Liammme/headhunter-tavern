from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Job


def generate_company_clue_letter(db: Session, *, company: str) -> dict:
    jobs = (
        db.query(Job)
        .filter(Job.company == company)
        .order_by(Job.collected_at.desc(), Job.id.desc())
        .all()
    )
    generated_at = _resolve_generated_at(jobs)

    if not jobs:
        return {
            "status": "failure",
            "company": company,
            "generated_at": generated_at,
            "narrative": f"{company} 的线索来信契约已建立，但当前还没有可用公司资料，因此暂时无法生成单公司线索来信。",
            "sections": [],
            "error_message": "Company not found",
        }

    top_jobs = jobs[:3]
    job_titles = "、".join(job.title for job in top_jobs)
    high_bounty_count = sum(1 for job in jobs if job.bounty_grade == "high")

    return {
        "status": "success",
        "company": company,
        "generated_at": generated_at,
        "narrative": (
            f"{company} 的单公司线索来信契约已建立。当前返回的是服务边界占位稿，"
            f"基于系统内已有岗位信息先组织结构，真实生成将在下一阶段接入。"
        ),
        "sections": [
            {
                "key": "what_i_saw",
                "title": "我先看到的",
                "content": f"当前这家公司可直接使用的重点岗位包括：{job_titles}。",
            },
            {
                "key": "what_it_means",
                "title": "这说明什么",
                "content": f"现有岗位池里共有 {len(jobs)} 个岗位，其中 {high_bounty_count} 个被标记为高赏金，可作为后续线索来信的输入基线。",
            },
            {
                "key": "next_move",
                "title": "你下一步怎么动",
                "content": "下一阶段会在这套契约上接入真实生成链路；当前阶段先固定请求参数、响应结构和失败边界。",
            },
        ],
        "error_message": None,
    }


def _resolve_generated_at(jobs: list[Job]) -> str:
    if jobs:
        latest = jobs[0].collected_at.replace(microsecond=0)
        return latest.isoformat()

    return datetime.now().replace(microsecond=0).isoformat()
