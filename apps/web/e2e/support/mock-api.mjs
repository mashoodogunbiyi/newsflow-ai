import { createServer } from "node:http";

const PORT = 4100;
const ARTICLE_ID = "10000000-0000-4000-8000-000000000001";
const GENERATION_ID = "20000000-0000-4000-8000-000000000002";
const GENERATED_POST_ID = "30000000-0000-4000-8000-000000000003";
const IMAGE_ID = "40000000-0000-4000-8000-000000000004";
const REGENERATED_IMAGE_ID = "40000000-0000-4000-8000-000000000005";
const DRAFT_ID = "50000000-0000-4000-8000-000000000005";
const POST_VERSION_ID = "60000000-0000-4000-8000-000000000006";
const USER_IDS = {
  "owner@example.com": "70000000-0000-4000-8000-000000000007",
  "other@example.com": "80000000-0000-4000-8000-000000000008",
};
const SESSION_EMAILS = {
  "owner-session": "owner@example.com",
  "other-session": "other@example.com",
};
const png = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
  "base64",
);

const article = {
  id: ARTICLE_ID,
  title: "Synthetic technology update for responsible AI testing",
  description: "A permitted synthetic article used only for deterministic NewsFlow AI tests.",
  source_url: "https://example.invalid/newsflow/synthetic-clean-energy",
  provider: "NewsFlow AI synthetic fixture",
  published_at: "2026-11-03T09:00:00Z",
  category: "technology",
  attribution: {
    display_name: "NewsFlow AI synthetic fixture",
    text: "Source: NewsFlow AI synthetic fixture - not live news",
    byline: "Synthetic test desk",
    copyright_notice: "Synthetic fixture. No third-party news content.",
  },
};

let state;
function reset() {
  state = {
    drafts: new Map(),
    generationFailure: false,
    generationTimeout: false,
    metrics: createMetrics(),
  };
}
reset();

function createMetrics() {
  return {
    articleDetail: 0,
    articleList: 0,
    authenticationState: 0,
    draftDetail: 0,
    draftList: 0,
    generation: 0,
    imageContent: 0,
    imageDownload: 0,
  };
}

function recordMetric(name) {
  state.metrics[name] += 1;
}

function cookies(request) {
  return Object.fromEntries(
    String(request.headers.cookie ?? "")
      .split(";")
      .map((part) => part.trim())
      .filter(Boolean)
      .map((part) => {
        const index = part.indexOf("=");
        return index < 0
          ? [part, ""]
          : [part.slice(0, index), decodeURIComponent(part.slice(index + 1))];
      }),
  );
}

function authenticatedEmail(request) {
  return SESSION_EMAILS[cookies(request).newsflow_session] ?? null;
}

function json(response, status, payload, headers = {}) {
  response.writeHead(status, {
    "Cache-Control": "no-store",
    "Content-Type": "application/json",
    ...headers,
  });
  response.end(JSON.stringify(payload));
}

function readBody(request) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    request.on("data", (chunk) => chunks.push(chunk));
    request.on("end", () => {
      try {
        const text = Buffer.concat(chunks).toString("utf8");
        resolve(text ? JSON.parse(text) : {});
      } catch (error) {
        reject(error);
      }
    });
    request.on("error", reject);
  });
}

function requireAuthentication(request, response) {
  const email = authenticatedEmail(request);
  if (!email) {
    json(response, 401, {
      error: { code: "authentication_required", message: "Authentication is required." },
    });
    return null;
  }
  return email;
}

function savedDraft(body, ownerEmail) {
  const now = "2026-11-03T09:10:00Z";
  const selectedImageId = body.selected_image_id ?? null;
  return {
    id: DRAFT_ID,
    owner_email: ownerEmail,
    generated_post_id: GENERATED_POST_ID,
    current_post_version_id: POST_VERSION_ID,
    selected_image_id: selectedImageId,
    selected_image: selectedImageId
      ? {
          id: selectedImageId,
          alt_text: "AI-generated editorial illustration for the synthetic technology update",
          mime_type: "image/png",
          width_px: 1536,
          height_px: 1024,
          ai_generated: true,
          ai_disclosure_required: true,
        }
      : null,
    title: body.title ?? article.title,
    edited_text: body.edited_text,
    tone: "professional",
    length: "medium",
    status: "saved",
    version: 1,
    source: {
      article_id: ARTICLE_ID,
      title: article.title,
      url: article.source_url,
      attribution: article.attribution.text,
    },
    generation: {
      generation_id: GENERATION_ID,
      original_post_version_id: POST_VERSION_ID,
      model_identifier: "mock-openai-text-model",
      prompt_version: "linkedin_v1",
      created_at: "2026-11-03T09:05:00Z",
    },
    created_at: now,
    updated_at: now,
  };
}

function publicDraft(draft) {
  const payload = { ...draft };
  delete payload.owner_email;
  return payload;
}

const server = createServer(async (request, response) => {
  const url = new URL(request.url ?? "/", `http://127.0.0.1:${PORT}`);
  const method = request.method ?? "GET";

  if (method === "GET" && url.pathname === "/health") {
    return json(response, 200, { status: "ok" });
  }
  if (method === "POST" && url.pathname === "/__test/reset") {
    reset();
    return json(response, 200, { status: "reset" });
  }
  if (method === "POST" && url.pathname === "/__test/metrics/reset") {
    state.metrics = createMetrics();
    return json(response, 200, { status: "reset" });
  }
  if (method === "GET" && url.pathname === "/__test/metrics") {
    return json(response, 200, state.metrics);
  }
  if (method === "POST" && url.pathname === "/__test/generation-failure") {
    state.generationFailure = true;
    return json(response, 200, { status: "configured" });
  }
  if (method === "POST" && url.pathname === "/__test/generation-timeout") {
    state.generationTimeout = true;
    return json(response, 200, { status: "configured" });
  }
  if (method === "POST" && url.pathname === "/__test/seed-owner-draft") {
    const draft = savedDraft(
      {
        edited_text: "Owner-only synthetic draft.",
        selected_image_id: IMAGE_ID,
        title: article.title,
      },
      "owner@example.com",
    );
    state.drafts.set(draft.id, draft);
    return json(response, 201, publicDraft(draft));
  }

  if (method === "POST" && url.pathname === "/api/v1/auth/login") {
    const body = await readBody(request);
    const email = typeof body.email === "string" ? body.email.toLowerCase() : "";
    if (!(email in USER_IDS) || body.password !== "TestPassword123!") {
      return json(response, 401, {
        error: { code: "invalid_credentials", message: "Invalid email or password." },
      });
    }
    const session = email === "other@example.com" ? "other-session" : "owner-session";
    return json(
      response,
      200,
      { id: USER_IDS[email], email },
      {
        "Set-Cookie": [
          `newsflow_session=${session}; HttpOnly; Path=/; SameSite=Lax`,
          "newsflow_csrf=e2e-csrf; Path=/; SameSite=Lax",
        ],
      },
    );
  }
  if (method === "GET" && url.pathname === "/api/v1/auth/me") {
    recordMetric("authenticationState");
    const email = requireAuthentication(request, response);
    return email ? json(response, 200, { id: USER_IDS[email], email }) : undefined;
  }
  if (method === "POST" && url.pathname === "/api/v1/auth/logout") {
    return json(
      response,
      204,
      {},
      {
        "Set-Cookie": [
          "newsflow_session=; HttpOnly; Path=/; Max-Age=0; SameSite=Lax",
          "newsflow_csrf=; Path=/; Max-Age=0; SameSite=Lax",
        ],
      },
    );
  }

  if (method === "GET" && url.pathname === "/api/articles") {
    recordMetric("articleList");
    if (!requireAuthentication(request, response)) return;
    const items = url.searchParams.get("search") === "no-results" ? [] : [article];
    return json(response, 200, { items, next_cursor: null });
  }
  if (method === "GET" && url.pathname === `/api/articles/${ARTICLE_ID}`) {
    recordMetric("articleDetail");
    if (!requireAuthentication(request, response)) return;
    return json(response, 200, { ...article, generation: { allowed: true, status: "available" } });
  }
  if (method === "POST" && url.pathname === "/api/generations") {
    recordMetric("generation");
    if (!requireAuthentication(request, response)) return;
    if (state.generationTimeout) {
      return json(response, 504, {
        error: {
          code: "openai_timeout",
          message: "The AI provider took too long to respond. Please try again deliberately.",
        },
      });
    }
    if (state.generationFailure) {
      return json(response, 503, {
        error: {
          code: "generation_unavailable",
          message: "Mocked provider is temporarily unavailable.",
        },
      });
    }
    const body = await readBody(request);
    return json(response, 201, {
      generation_id: GENERATION_ID,
      article_id: ARTICLE_ID,
      draft: "A synthetic AI-assisted LinkedIn draft for careful human review.",
      tone: body.tone,
      length: body.length,
      source_title: article.title,
      source_name: article.provider,
      source_url: article.source_url,
      source_attribution: article.attribution.text,
      status: "draft",
      review_required: true,
      grounding_status: "passed_automated_checks",
      validation_warnings: [],
      grounding_policy_version: "grounding_v1",
      created_at: "2026-11-03T09:05:00Z",
    });
  }
  if (method === "POST" && url.pathname === "/api/images") {
    if (!requireAuthentication(request, response)) return;
    return json(response, 201, {
      image_id: IMAGE_ID,
      generation_id: GENERATION_ID,
      generated_post_id: GENERATED_POST_ID,
      parent_image_id: null,
      regeneration_sequence: 0,
      status: "completed",
      safety_status: "approved",
      is_ai_generated: true,
      review_required: true,
      created_at: "2026-11-03T09:07:00Z",
    });
  }
  if (method === "POST" && url.pathname === `/api/images/${IMAGE_ID}/regenerate`) {
    if (!requireAuthentication(request, response)) return;
    return json(response, 201, {
      image_id: REGENERATED_IMAGE_ID,
      generation_id: GENERATION_ID,
      generated_post_id: GENERATED_POST_ID,
      parent_image_id: IMAGE_ID,
      regeneration_sequence: 1,
      status: "completed",
      safety_status: "approved",
      is_ai_generated: true,
      review_required: true,
      created_at: "2026-11-03T09:08:00Z",
    });
  }
  const requestedImageId = [IMAGE_ID, REGENERATED_IMAGE_ID].find(
    (imageId) => url.pathname === `/api/images/${imageId}/content`,
  );
  if (method === "GET" && requestedImageId) {
    recordMetric("imageContent");
    if (!requireAuthentication(request, response)) return;
    response.writeHead(200, { "Cache-Control": "private, no-store", "Content-Type": "image/png" });
    return response.end(png);
  }
  const downloadedImageId = [IMAGE_ID, REGENERATED_IMAGE_ID].find(
    (imageId) => url.pathname === `/api/images/${imageId}/download`,
  );
  if (method === "GET" && downloadedImageId) {
    recordMetric("imageDownload");
    if (!requireAuthentication(request, response)) return;
    response.writeHead(200, {
      "Cache-Control": "private, no-store",
      "Content-Disposition": `attachment; filename="newsflow-ai-illustration-${downloadedImageId}.png"`,
      "Content-Type": "image/png",
    });
    return response.end(png);
  }

  if (method === "POST" && url.pathname === "/api/v1/drafts") {
    const email = requireAuthentication(request, response);
    if (!email) return;
    const body = await readBody(request);
    const draft = savedDraft(body, email);
    state.drafts.set(draft.id, draft);
    return json(response, 201, publicDraft(draft));
  }
  if (method === "GET" && url.pathname === "/api/v1/drafts") {
    recordMetric("draftList");
    const email = requireAuthentication(request, response);
    if (!email) return;
    const items = [...state.drafts.values()]
      .filter((draft) => draft.owner_email === email)
      .map(publicDraft);
    return json(response, 200, {
      items,
      page: 1,
      page_size: Number(url.searchParams.get("page_size") ?? 20),
      sort: "updated_at_desc",
      total_items: items.length,
      total_pages: items.length ? 1 : 0,
    });
  }
  if (method === "GET" && url.pathname === `/api/v1/drafts/${DRAFT_ID}/versions`) {
    const email = requireAuthentication(request, response);
    const draft = state.drafts.get(DRAFT_ID);
    if (!email) return;
    if (!draft || draft.owner_email !== email) {
      return json(response, 404, {
        error: {
          code: "private_resource_not_found",
          message: "The requested resource was not found.",
        },
      });
    }
    const version = {
      id: POST_VERSION_ID,
      draft_id: DRAFT_ID,
      post_version_id: POST_VERSION_ID,
      selected_image_id: draft.selected_image_id,
      selected_image: draft.selected_image,
      generation_id: GENERATION_ID,
      restored_from_version_id: null,
      version_number: 1,
      change_type: "initial_save",
      title: draft.title,
      edited_text: draft.edited_text,
      tone: draft.tone,
      length: draft.length,
      source: draft.source,
      created_at: draft.created_at,
    };
    return json(response, 200, {
      items: [version],
      page: 1,
      page_size: 20,
      sort: "version_desc",
      total_items: 1,
      total_pages: 1,
    });
  }
  if (url.pathname === `/api/v1/drafts/${DRAFT_ID}`) {
    if (method === "GET") recordMetric("draftDetail");
    const email = requireAuthentication(request, response);
    const draft = state.drafts.get(DRAFT_ID);
    if (!email) return;
    if (!draft || draft.owner_email !== email) {
      return json(response, 404, {
        error: {
          code: "private_resource_not_found",
          message: "The requested resource was not found.",
        },
      });
    }
    if (method === "GET") return json(response, 200, publicDraft(draft));
    if (method === "DELETE") {
      state.drafts.delete(DRAFT_ID);
      response.writeHead(204, { "Cache-Control": "no-store" });
      return response.end();
    }
  }

  return json(response, 404, { error: { code: "not_found", message: "Mock route not found." } });
});

server.listen(PORT, "127.0.0.1", () => {
  process.stdout.write(`NewsFlow AI deterministic mock API listening on ${PORT}\n`);
});
