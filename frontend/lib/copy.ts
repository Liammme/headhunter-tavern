import type { DayBucketPayload, JobCategory } from "./types";

export type FeedCopy = {
  tabs: Record<DayBucketPayload["bucket"], string>;
  ariaLabel: string;
  logoAlt: string;
  categoryFilterAriaLabel: string;
  allCategoriesLabel: string;
  categoryLabels: Record<JobCategory, string>;
  emptyEyebrowFromTab?: boolean;
  emptyNoMatchTitle: string;
  emptyNoJobsTitle: string;
  emptyDescription: string;
  expandEarlierLabel: string;
  collapseEarlierLabel: string;
};

export type CompanyCardCopy = {
  clueLabel: string;
  collapseClueLabel: string;
  jobListAriaLabel: (company: string) => string;
  viewOriginalPostLabel: string;
  expandJobsLabel: string;
  collapseJobsLabel: string;
};

export type IntelligenceCopy = {
  openReportAriaLabel: string;
  backLabel: string;
  livingReport: LivingReportCopy;
};

export type LivingReportCopy = {
  metaAriaLabel: string;
  versionLabel: (version: number) => string;
  baselineLabel: (days: number) => string;
  updatedLabel: (generatedAt: string) => string;
  sectionsAriaLabel: string;
  emptySectionsLabel: string;
  claimsAriaLabel: string;
  claimsTitle: string;
  watchlistAriaLabel: string;
  watchlistTitle: string;
  sampleCountLabel: (count: number) => string;
  statusLabels: Record<string, string>;
};

export type ChartCopy = {
  tooltipTitle: string;
  tooltipDescription: string;
  chartAriaLabel: string;
  barAriaLabel: (label: string, value: number) => string;
  fallbackLabels: [string, string, string];
};

export type JapanPageCopy = {
  feed: FeedCopy;
  companyCard: CompanyCardCopy;
  intelligence: IntelligenceCopy;
  chart: ChartCopy;
};

export const DEFAULT_FEED_COPY: FeedCopy = {
  tabs: {
    within_3_days: "最新",
    within_7_days: "7天内",
    earlier: "更早",
  },
  ariaLabel: "岗位时间筛选",
  logoAlt: "赏金猎人",
  categoryFilterAriaLabel: "岗位类型筛选",
  allCategoriesLabel: "全部岗位",
  categoryLabels: {
    "设计": "设计",
    "运营": "运营",
    "市场": "市场",
    "销售": "销售",
    "商务": "商务",
    "产品": "产品",
    "技术": "技术",
    "AI/算法": "AI/算法",
    "数据": "数据",
    "安全": "安全",
    "DevRel/社区": "DevRel/社区",
    "财务/法务/HR": "财务/法务/HR",
    "其他": "其他",
  },
  emptyNoMatchTitle: "这一栏暂时没有匹配岗位",
  emptyNoJobsTitle: "这一栏暂时没有岗位",
  emptyDescription: "等下一次抓取写入后，这里会自动展示对应时间段的公司机会。",
  expandEarlierLabel: "展开全部更早岗位",
  collapseEarlierLabel: "收起更早岗位",
};

export const DEFAULT_COMPANY_CARD_COPY: CompanyCardCopy = {
  clueLabel: "线索",
  collapseClueLabel: "收起线索",
  jobListAriaLabel: (company) => `${company}在招岗位`,
  viewOriginalPostLabel: "查看原帖",
  expandJobsLabel: "展开更多岗位",
  collapseJobsLabel: "收起岗位",
};

export const DEFAULT_LIVING_REPORT_COPY: LivingReportCopy = {
  metaAriaLabel: "活报告元信息",
  versionLabel: (version) => `第 ${version} 版`,
  baselineLabel: (days) => `基于 ${days} 天基线`,
  updatedLabel: (generatedAt) => `最近更新 ${generatedAt}`,
  sectionsAriaLabel: "报告章节",
  emptySectionsLabel: "暂无可展示章节。",
  claimsAriaLabel: "报告判断",
  claimsTitle: "判断",
  watchlistAriaLabel: "观察清单",
  watchlistTitle: "观察清单",
  sampleCountLabel: (count) => `样本数 ${count}`,
  statusLabels: {
    new: "新增",
    reinforced: "强化",
    weakened: "削弱",
    retired: "退休",
  },
};

export const DEFAULT_INTELLIGENCE_COPY: IntelligenceCopy = {
  openReportAriaLabel: "打开猎场控制台",
  backLabel: "返回",
  livingReport: DEFAULT_LIVING_REPORT_COPY,
};

export const DEFAULT_CHART_COPY: ChartCopy = {
  tooltipTitle: "Daily Capture Signal",
  tooltipDescription: "Showing live collection movement.",
  chartAriaLabel: "每日岗位收集数量统计图",
  barAriaLabel: (label, value) => `${label}，${value} 个岗位`,
  fallbackLabels: ["3天内", "7天内", "更早"],
};

export const JAPAN_UI_COPY: JapanPageCopy = {
  feed: {
    tabs: {
      within_3_days: "最新",
      within_7_days: "7日以内",
      earlier: "それ以前",
    },
    ariaLabel: "求人期間フィルター",
    logoAlt: "Talent Signal",
    categoryFilterAriaLabel: "職種フィルター",
    allCategoriesLabel: "すべての職種",
    categoryLabels: {
      "设计": "デザイン",
      "运营": "オペレーション",
      "市场": "マーケティング",
      "销售": "セールス",
      "商务": "事業開発",
      "产品": "プロダクト",
      "技术": "エンジニアリング",
      "AI/算法": "AI/アルゴリズム",
      "数据": "データ",
      "安全": "セキュリティ",
      "DevRel/社区": "DevRel/コミュニティ",
      "财务/法务/HR": "財務/法務/HR",
      "其他": "その他",
    },
    emptyNoMatchTitle: "このセクションには一致する求人がまだありません",
    emptyNoJobsTitle: "このセクションには求人がまだありません",
    emptyDescription: "次回の取得後、この期間に該当する企業の求人が表示されます。",
    expandEarlierLabel: "それ以前の求人をすべて表示",
    collapseEarlierLabel: "それ以前の求人を閉じる",
  },
  companyCard: {
    clueLabel: "線索",
    collapseClueLabel: "線索を閉じる",
    jobListAriaLabel: (company) => `${company}の募集中ポジション`,
    viewOriginalPostLabel: "原文を見る",
    expandJobsLabel: "さらに求人を表示",
    collapseJobsLabel: "求人を閉じる",
  },
  intelligence: {
    openReportAriaLabel: "マーケットレポートを開く",
    backLabel: "戻る",
    livingReport: {
      metaAriaLabel: "レポートメタ情報",
      versionLabel: (version) => `第${version}版`,
      baselineLabel: (days) => `${days}日ベースライン`,
      updatedLabel: (generatedAt) => `最終更新 ${generatedAt}`,
      sectionsAriaLabel: "レポート章",
      emptySectionsLabel: "表示できる章はまだありません。",
      claimsAriaLabel: "レポート判断",
      claimsTitle: "判断",
      watchlistAriaLabel: "ウォッチリスト",
      watchlistTitle: "ウォッチリスト",
      sampleCountLabel: (count) => `サンプル数 ${count}`,
      statusLabels: {
        new: "新規",
        reinforced: "強化",
        weakened: "弱化",
        retired: "終了",
      },
    },
  },
  chart: {
    tooltipTitle: "Daily Capture Signal",
    tooltipDescription: "取得状況の変化を表示しています。",
    chartAriaLabel: "求人取得数チャート",
    barAriaLabel: (label, value) => `${label}、${value}件`,
    fallbackLabels: ["3日以内", "7日以内", "それ以前"],
  },
};
