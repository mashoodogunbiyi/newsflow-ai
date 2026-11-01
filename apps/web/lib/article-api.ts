import { cookies } from "next/headers";

import { isArticlePage, type ArticlePage } from "@/types/article";

const SESSION_COOKIE_NAME = "newsflow_session";
const ARTICLE_PAGE_SIZE = 9;

export type ArticleSort = "newest" | "oldest";

export type ArticlePageOptions = {
  cursor?: string;
  search?: string;
  sort?: ArticleSort;
};

export type ArticlePageResult =
  | { data: ArticlePage; status: "success" }
  | {
      reason: "authentication_required" | "invalid_request" | "unavailable";
      status: "error";
    };

function getBackendBaseUrl() {
  const configuredUrl =
    process.env.API_INTERNAL_BASE_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "http://localhost:8000";

  return configuredUrl.replace(/\/+$/, "");
}

function hasValidOptions(options: ArticlePageOptions) {
  return (
    (!options.cursor || options.cursor.length <= 512) &&
    (!options.search || options.search.length <= 200) &&
    (!options.sort || options.sort === "newest" || options.sort === "oldest")
  );
}

function buildArticleUrl(options: ArticlePageOptions) {
  const searchParameters = new URLSearchParams({
    limit: String(ARTICLE_PAGE_SIZE),
    sort: options.sort ?? "newest",
  });

  if (options.cursor) {
    searchParameters.set("cursor", options.cursor);
  }
  if (options.search) {
    searchParameters.set("search", options.search);
  }

  return `${getBackendBaseUrl()}/api/articles?${searchParameters.toString()}`;
}

export async function getArticlePage(options: ArticlePageOptions = {}): Promise<ArticlePageResult> {
  if (!hasValidOptions(options)) {
    return { status: "error", reason: "invalid_request" };
  }

  const sessionCookie = (await cookies()).get(SESSION_COOKIE_NAME)?.value;
  if (!sessionCookie) {
    return { status: "error", reason: "authentication_required" };
  }

  try {
    const response = await fetch(buildArticleUrl(options), {
      headers: {
        Accept: "application/json",
        Cookie: `${SESSION_COOKIE_NAME}=${encodeURIComponent(sessionCookie)}`,
      },
      cache: "no-store",
    });

    if (response.status === 401) {
      return { status: "error", reason: "authentication_required" };
    }
    if (response.status === 422) {
      return { status: "error", reason: "invalid_request" };
    }
    if (!response.ok) {
      return { status: "error", reason: "unavailable" };
    }

    const payload: unknown = await response.json();
    if (!isArticlePage(payload)) {
      return { status: "error", reason: "unavailable" };
    }

    return { status: "success", data: payload };
  } catch {
    return { status: "error", reason: "unavailable" };
  }
}
