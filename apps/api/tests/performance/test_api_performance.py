"""NFA-80 synthetic API latency, payload, and concurrency budgets."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from math import ceil
from time import perf_counter
from uuid import uuid4

from fastapi.testclient import TestClient

from tests.test_article_catalogue import (
    InMemoryArticleCatalogueRepository,
    article_record,
)
from tests.test_article_catalogue import (
    make_client as make_article_client,
)
from tests.test_image_delivery import (
    IMAGE_ID,
    MemoryStorage,
    image_record,
    selected_service,
)
from tests.test_image_delivery import (
    api_client as make_image_client,
)
from tests.test_saved_drafts import (
    InMemorySavedDraftRepository,
)
from tests.test_saved_drafts import (
    _client as make_draft_client,
)
from tests.test_saved_drafts import (
    _create as create_draft,
)

ARTICLE_LIST_P95_TARGET_MS = 150.0
LIBRARY_LIST_P95_TARGET_MS = 200.0
IMAGE_DELIVERY_P95_TARGET_MS = 250.0
CONCURRENT_ARTICLE_P95_TARGET_MS = 750.0
MAX_ARTICLE_RESPONSE_BYTES = 150_000
MAX_LIBRARY_RESPONSE_BYTES = 250_000


@dataclass(frozen=True)
class TimingSummary:
    """Content-free timing evidence for one repeatable local workload."""

    samples: int
    minimum_ms: float
    median_ms: float
    p95_ms: float
    maximum_ms: float


def summarise(samples: list[float]) -> TimingSummary:
    """Return deterministic nearest-rank statistics for measured milliseconds."""

    ordered = sorted(samples)
    return TimingSummary(
        samples=len(ordered),
        minimum_ms=ordered[0],
        median_ms=ordered[(len(ordered) - 1) // 2],
        p95_ms=ordered[ceil(0.95 * len(ordered)) - 1],
        maximum_ms=ordered[-1],
    )


def measure_requests(
    client: TestClient,
    path: str,
    *,
    samples: int = 30,
    warmups: int = 5,
) -> tuple[TimingSummary, int]:
    """Measure an authenticated synthetic GET workload after explicit warmup."""

    for _ in range(warmups):
        response = client.get(path)
        assert response.status_code == 200

    timings: list[float] = []
    response_size = 0
    for _ in range(samples):
        started = perf_counter()
        response = client.get(path)
        elapsed_ms = (perf_counter() - started) * 1000
        assert response.status_code == 200
        timings.append(elapsed_ms)
        response_size = len(response.content)
    return summarise(timings), response_size


def article_client() -> TestClient:
    records = [
        article_record(
            article_id=uuid4(),
            title=f"Synthetic performance article {number:03d}",
        )
        for number in range(101)
    ]
    return make_article_client(InMemoryArticleCatalogueRepository(records))


def library_client() -> TestClient:
    repository = InMemorySavedDraftRepository()
    client = make_draft_client(repository)
    created = create_draft(client).json()
    template = repository.items[next(iter(repository.items))]
    for number in range(1, 100):
        item_id = uuid4()
        repository.items[item_id] = replace(
            template,
            id=item_id,
            generated_post_id=uuid4(),
            current_post_version_id=uuid4(),
            selected_image_id=None,
            selected_image=None,
            title=f"Synthetic saved draft {number:03d}",
        )
    assert created["status"] == "saved"
    return client


def test_article_catalogue_latency_and_payload_budget() -> None:
    client = article_client()
    try:
        timing, response_size = measure_requests(
            client,
            "/api/articles?limit=100&sort=newest",
        )
    finally:
        client.close()

    print(f"NFA80 article_list={timing} response_bytes={response_size}")
    assert timing.p95_ms <= ARTICLE_LIST_P95_TARGET_MS
    assert response_size <= MAX_ARTICLE_RESPONSE_BYTES


def test_content_library_latency_and_payload_budget() -> None:
    client = library_client()
    try:
        timing, response_size = measure_requests(
            client,
            "/api/v1/drafts?page=1&page_size=100",
        )
    finally:
        client.close()

    print(f"NFA80 library_list={timing} response_bytes={response_size}")
    assert timing.p95_ms <= LIBRARY_LIST_P95_TARGET_MS
    assert response_size <= MAX_LIBRARY_RESPONSE_BYTES


def test_one_megabyte_private_image_delivery_budget() -> None:
    image_bytes = b"N" * 1_048_576
    service = selected_service(
        record=image_record(content=image_bytes),
        storage=MemoryStorage(content=image_bytes),
    )
    client = make_image_client(service=service)
    try:
        timing, response_size = measure_requests(
            client,
            f"/api/images/{IMAGE_ID}/content",
            samples=12,
            warmups=2,
        )
    finally:
        client.close()

    print(f"NFA80 image_delivery={timing} response_bytes={response_size}")
    assert timing.p95_ms <= IMAGE_DELIVERY_P95_TARGET_MS
    assert response_size == len(image_bytes)


def test_representative_concurrent_article_requests_remain_controlled() -> None:
    client = article_client()

    def request_once() -> tuple[int, float]:
        started = perf_counter()
        response = client.get("/api/articles?limit=20&sort=newest")
        return response.status_code, (perf_counter() - started) * 1000

    try:
        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(lambda _number: request_once(), range(24)))
    finally:
        client.close()

    statuses = [status for status, _elapsed in results]
    timing = summarise([elapsed for _status, elapsed in results])
    print(f"NFA80 concurrent_article_list={timing}")
    assert statuses == [200] * 24
    assert timing.p95_ms <= CONCURRENT_ARTICLE_P95_TARGET_MS


def test_pagination_contracts_remain_bounded() -> None:
    article = article_client()
    library = library_client()
    try:
        article_response = article.get("/api/articles?limit=101")
        library_response = library.get("/api/v1/drafts?page=1&page_size=101")
    finally:
        article.close()
        library.close()

    assert article_response.status_code == 422
    assert library_response.status_code == 422
