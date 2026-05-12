from __future__ import annotations

from dataclasses import dataclass
import re

JOB_CATEGORIES = (
    "设计",
    "运营",
    "市场",
    "销售",
    "商务",
    "产品",
    "技术",
    "AI/算法",
    "数据",
    "安全",
    "DevRel/社区",
    "财务/法务/HR",
    "其他",
)

MIXED_CATEGORY = "其他"


@dataclass(frozen=True)
class JobCategoryResult:
    primary: str
    secondary: tuple[str, ...]
    confidence: str
    reason: str
    mixed_job_posting: bool = False


@dataclass(frozen=True)
class CategoryRule:
    category: str
    title_pattern: re.Pattern


def _compile(pattern: str) -> re.Pattern:
    return re.compile(pattern, re.IGNORECASE)


RULES = (
    CategoryRule(
        "安全",
        _compile(
            r"\b(security|cybersecurity|appsec|secops|devsecops|threat|vulnerabilit(?:y|ies)|"
            r"pentest|penetration|risk|compliance|kyc|aml|fraud|trust\s*&\s*safety)\b|"
            r"安全|风控|合规|反欺诈|漏洞|审计"
        ),
    ),
    CategoryRule(
        "AI/算法",
        _compile(
            r"\b(ai|artificial intelligence|ml|machine learning|deep learning|llm|large language model|"
            r"genai|generative ai|computer vision|nlp|algorithm|research scientist|applied scientist|"
            r"prompt|rag|model training|model serving|inference)\b|"
            r"算法|机器学习|大模型|人工智能|模型推理|ai工程师|ai架构"
        ),
    ),
    CategoryRule(
        "数据",
        _compile(
            r"\b(data scientist|data engineer|data analyst|analytics engineer|business analytics|"
            r"bi engineer|data platform|data warehouse|etl|elt|sql|database administrator|dba|"
            r"analytics|analyst|insights|reporting|quantitative researcher|quant researcher|data quality)\b|"
            r"数据|数仓|分析师|报表|量化研究"
        ),
    ),
    CategoryRule(
        "设计",
        _compile(
            r"\b(designer|design|product design|ux|ui|user experience|visual|brand designer|graphic|"
            r"motion designer|creative director|multimedia editor|video editor|copywriter)\b|"
            r"设计师|设计|视觉|品牌|用户体验|交互|动效|剪辑|内容编辑"
        ),
    ),
    CategoryRule(
        "产品",
        _compile(r"\b(product manager|product owner|product lead|head of product|principal product)\b|产品经理|产品负责人"),
    ),
    CategoryRule(
        "DevRel/社区",
        _compile(
            r"\b(devrel|developer relations|developer advocate|developer experience|community manager|"
            r"community lead|ambassador|evangelist)\b|开发者关系|社区|布道师"
        ),
    ),
    CategoryRule(
        "销售",
        _compile(
            r"\b(sales|account executive|account manager|sales development|sdr|bdr|customer success|"
            r"solutions consultant|pre-sales|presales|loan originator)\b|销售|客户成功|售前"
        ),
    ),
    CategoryRule(
        "商务",
        _compile(
            r"\b(business development|\bbd\b|partnership|partnerships|partner manager|alliances|"
            r"ecosystem manager|strategic partnerships|commercial)\b|商务|合作|渠道|伙伴|生态拓展"
        ),
    ),
    CategoryRule(
        "市场",
        _compile(
            r"\b(marketing|marketer|growth marketing|content marketing|brand marketing|performance marketing|"
            r"seo|social media|communications|public relations|\bpr\b|campaign|event manager)\b|"
            r"市场|营销|品牌传播|公关|内容|社交媒体"
        ),
    ),
    CategoryRule(
        "运营",
        _compile(
            r"\b(operations|operator|program manager|project manager|delivery manager|chief of staff|ops|"
            r"support specialist|support engineer|customer support|implementation|supply chain|middle office|"
            r"personal assistant|executive assistant)\b|"
            r"运营|项目经理|交付|支持|客服|供应链|助理"
        ),
    ),
    CategoryRule(
        "财务/法务/HR",
        _compile(
            r"\b(finance|financial|accounting|accountant|controller|legal|counsel|lawyer|people|"
            r"talent acquisition|recruiter|hr|human resources|payroll)\b|"
            r"财务|会计|法务|律师|人力|招聘|薪酬|核算"
        ),
    ),
    CategoryRule(
        "技术",
        _compile(
            r"\b(engineer|engineering|developer|software|frontend|front-end|backend|back-end|full stack|"
            r"full-stack|devops|sre|platform|infrastructure|architect|python|java|typescript|javascript|"
            r"react|node|cloud|kubernetes|qa|quality engineer|test engineer|robotics|automation engineer|"
            r"ios|android|golang|solidity|rust|sdet|protocol engineer)\b|"
            r"工程师|开发|前端|后端|全栈|架构|测试|运维|机器人|自动化|智能合约|服务端"
        ),
    ),
)


def classify_job_category_result(title: str, description: str = "") -> JobCategoryResult:
    normalized_title = _normalize(title)
    normalized_description = _normalize(description)
    if _looks_like_mixed_job_posting(title or ""):
        return JobCategoryResult(
            primary=MIXED_CATEGORY,
            secondary=(),
            confidence="low",
            reason="title appears to contain multiple roles",
            mixed_job_posting=True,
        )

    title_matches = _match_categories(normalized_title)
    if title_matches:
        return JobCategoryResult(
            primary=title_matches[0],
            secondary=tuple(title_matches[1:]),
            confidence="high" if len(title_matches) == 1 else "medium",
            reason="title keyword match",
            mixed_job_posting=False,
        )

    context_matches = _match_categories(normalized_description)
    if context_matches:
        return JobCategoryResult(
            primary=context_matches[0],
            secondary=tuple(context_matches[1:]),
            confidence="low",
            reason="description keyword fallback",
            mixed_job_posting=False,
        )

    return JobCategoryResult(
        primary="其他",
        secondary=(),
        confidence="low",
        reason="no category keyword matched",
        mixed_job_posting=False,
    )


def _match_categories(text: str) -> list[str]:
    if not text:
        return []
    return [rule.category for rule in RULES if rule.title_pattern.search(text)]


def _looks_like_mixed_job_posting(title: str) -> bool:
    if not title:
        return False
    if title.count("http://") + title.count("https://") >= 2:
        return True
    if any(marker in title for marker in ("以下岗位", "岗位投递", "本周急招岗位", "所有职位")):
        return True
    role_lines = [line for line in title.splitlines() if _match_categories(line)]
    if len(role_lines) >= 3:
        return True
    if len(set(_match_categories(title))) >= 4:
        return True
    numbered_items = re.findall(r"(?:^|\s)(?:\d+[\.\)、]|[一二三四五六七八九十]、)", title)
    return len(numbered_items) >= 3


def _normalize(value: str) -> str:
    return " ".join((value or "").replace("\r\n", "\n").replace("\r", "\n").split())
