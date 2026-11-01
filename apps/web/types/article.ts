export type ArticleAttribution = {
  byline: string | null;
  copyright_notice: string | null;
  display_name: string;
  text: string;
};

export type Article = {
  attribution: ArticleAttribution;
  category: string | null;
  description: string | null;
  id: string;
  provider: string;
  published_at: string;
  source_url: string;
  title: string;
};

export type ArticlePage = {
  items: Article[];
  next_cursor: string | null;
};

export const ARTICLE_CATEGORIES = [
  { id: "technology", label: "Technology" },
  { id: "business", label: "Business" },
  { id: "world_news", label: "World News" },
  { id: "science", label: "Science" },
  { id: "other", label: "Other" },
] as const;

export type ArticleCategory = (typeof ARTICLE_CATEGORIES)[number]["id"];

export function isArticleCategory(value: string | undefined): value is ArticleCategory {
  return ARTICLE_CATEGORIES.some((category) => category.id === value);
}

export function getArticleCategoryLabel(categoryId: ArticleCategory) {
  return ARTICLE_CATEGORIES.find((category) => category.id === categoryId)?.label ?? "Other";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNullableString(value: unknown): value is string | null {
  return value === null || typeof value === "string";
}

function isHttpsUrl(value: unknown): value is string {
  if (typeof value !== "string") {
    return false;
  }

  try {
    return new URL(value).protocol === "https:";
  } catch {
    return false;
  }
}

function isArticleAttribution(value: unknown): value is ArticleAttribution {
  return (
    isRecord(value) &&
    typeof value.display_name === "string" &&
    typeof value.text === "string" &&
    isNullableString(value.byline) &&
    isNullableString(value.copyright_notice)
  );
}

function isArticle(value: unknown): value is Article {
  if (!isRecord(value)) {
    return false;
  }

  return (
    typeof value.id === "string" &&
    typeof value.title === "string" &&
    isNullableString(value.description) &&
    isHttpsUrl(value.source_url) &&
    typeof value.provider === "string" &&
    typeof value.published_at === "string" &&
    !Number.isNaN(Date.parse(value.published_at)) &&
    isNullableString(value.category) &&
    isArticleAttribution(value.attribution)
  );
}

export function isArticlePage(value: unknown): value is ArticlePage {
  return (
    isRecord(value) &&
    Array.isArray(value.items) &&
    value.items.every(isArticle) &&
    isNullableString(value.next_cursor)
  );
}
