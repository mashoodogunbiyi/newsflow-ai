"""Isolated repositories and helpers for account-security regression tests."""

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import Settings
from app.main import create_app
from app.repositories import (
    AccountCredentials,
    AuthenticatedSession,
    DuplicateUserEmailError,
    RegisteredUser,
    SavedContent,
    SavedContentConflictError,
)
from app.security import Argon2PasswordHasher

TEST_PASSWORD = "Synthetic-Test-Password-42!"


@dataclass
class StoredSession:
    """Server-side session state retained only inside one test."""

    user_id: UUID
    csrf_token_hash: bytes
    expires_at: datetime
    revoked_at: datetime | None = None


@dataclass(frozen=True)
class BrowserSession:
    """Purpose-limited cookie values captured for one synthetic user."""

    session_token: str
    csrf_token: str


class StubDatabase:
    """Satisfy startup while repositories use isolated in-memory state."""

    async def check_connection(self) -> None:
        return None


class AccountSecurityRepository:
    """Implement account, session, and saved-content boundaries for one test."""

    def __init__(self) -> None:
        self.accounts_by_email: dict[str, AccountCredentials] = {}
        self.accounts_by_id: dict[UUID, AccountCredentials] = {}
        self.sessions: dict[bytes, StoredSession] = {}
        self.saved_items: dict[UUID, SavedContent] = {}
        self.owned_posts: dict[UUID, tuple[UUID, UUID]] = {}

    async def create_user(self, *, email: str, password_hash: str) -> RegisteredUser:
        if email in self.accounts_by_email:
            raise DuplicateUserEmailError("Synthetic duplicate email.")
        account = AccountCredentials(
            id=uuid4(),
            email=email,
            password_hash=password_hash,
            status="active",
        )
        self.accounts_by_email[email] = account
        self.accounts_by_id[account.id] = account
        return RegisteredUser(id=account.id, email=account.email)

    async def get_account_credentials(
        self,
        *,
        email: str,
    ) -> AccountCredentials | None:
        return self.accounts_by_email.get(email)

    async def create_session(
        self,
        *,
        user_id: UUID,
        token_hash: bytes,
        csrf_token_hash: bytes,
        expires_at: datetime,
    ) -> None:
        self.sessions[token_hash] = StoredSession(
            user_id=user_id,
            csrf_token_hash=csrf_token_hash,
            expires_at=expires_at,
        )

    async def get_active_session(
        self,
        *,
        token_hash: bytes,
        checked_at: datetime,
    ) -> AuthenticatedSession | None:
        stored = self.sessions.get(token_hash)
        if (
            stored is None
            or stored.revoked_at is not None
            or stored.expires_at <= checked_at
        ):
            return None
        account = self.accounts_by_id.get(stored.user_id)
        if account is None or account.status != "active":
            return None
        return AuthenticatedSession(
            user_id=account.id,
            email=account.email,
            csrf_token_hash=stored.csrf_token_hash,
            expires_at=stored.expires_at,
        )

    async def revoke_session(
        self,
        *,
        token_hash: bytes,
        revoked_at: datetime,
    ) -> bool:
        stored = self.sessions.get(token_hash)
        if stored is None or stored.revoked_at is not None:
            return False
        stored.revoked_at = revoked_at
        return True

    def add_owned_post(self, *, owner_id: UUID) -> tuple[UUID, UUID]:
        """Create synthetic post and version references for one owner."""

        post_id = uuid4()
        version_id = uuid4()
        self.owned_posts[post_id] = (owner_id, version_id)
        return post_id, version_id

    async def list_for_owner(self, *, owner_id: UUID) -> list[SavedContent]:
        return [item for item in self.saved_items.values() if item.owner_id == owner_id]

    async def get_for_owner(
        self,
        *,
        owner_id: UUID,
        item_id: UUID,
    ) -> SavedContent | None:
        item = self.saved_items.get(item_id)
        return item if item is not None and item.owner_id == owner_id else None

    async def create_for_owner(
        self,
        *,
        owner_id: UUID,
        generated_post_id: UUID,
        selected_post_version_id: UUID,
        selected_image_id: UUID | None,
        library_title: str | None,
    ) -> SavedContent | None:
        if selected_image_id is not None:
            return None
        if self.owned_posts.get(generated_post_id) != (
            owner_id,
            selected_post_version_id,
        ):
            return None
        if any(
            item.owner_id == owner_id and item.generated_post_id == generated_post_id
            for item in self.saved_items.values()
        ):
            raise SavedContentConflictError("Synthetic item already saved.")

        now = datetime.now(UTC)
        item = SavedContent(
            id=uuid4(),
            owner_id=owner_id,
            generated_post_id=generated_post_id,
            selected_post_version_id=selected_post_version_id,
            selected_image_id=None,
            library_title=library_title,
            rendered_text=f"Private synthetic draft for {owner_id}.",
            source_attribution="NewsFlow AI synthetic test fixture",
            saved_at=now,
            updated_at=now,
        )
        self.saved_items[item.id] = item
        return item

    async def update_title_for_owner(
        self,
        *,
        owner_id: UUID,
        item_id: UUID,
        library_title: str | None,
    ) -> SavedContent | None:
        item = await self.get_for_owner(owner_id=owner_id, item_id=item_id)
        if item is None:
            return None
        updated = replace(
            item,
            library_title=library_title,
            updated_at=datetime.now(UTC),
        )
        self.saved_items[item_id] = updated
        return updated

    async def delete_for_owner(self, *, owner_id: UUID, item_id: UUID) -> bool:
        item = await self.get_for_owner(owner_id=owner_id, item_id=item_id)
        if item is None:
            return False
        del self.saved_items[item_id]
        return True


@dataclass
class AccountSecurityContext:
    """Reusable client, storage, and browser-session operations for tests."""

    client: TestClient
    repository: AccountSecurityRepository
    password_hasher: Argon2PasswordHasher

    def register(
        self,
        *,
        email: str,
        password: str = TEST_PASSWORD,
    ):
        return self.client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password},
        )

    def login(
        self,
        *,
        email: str,
        password: str = TEST_PASSWORD,
    ):
        return self.client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )

    def capture_browser_session(self) -> BrowserSession:
        session_token = self.client.cookies.get("newsflow_session")
        csrf_token = self.client.cookies.get("newsflow_csrf")
        if session_token is None or csrf_token is None:
            raise AssertionError("A successful login must create both test cookies.")
        return BrowserSession(
            session_token=session_token,
            csrf_token=csrf_token,
        )

    def use_browser_session(self, session: BrowserSession) -> None:
        self.clear_browser_session()
        self.client.cookies.set("newsflow_session", session.session_token)
        self.client.cookies.set("newsflow_csrf", session.csrf_token)

    def clear_browser_session(self) -> None:
        self.client.cookies.clear()

    @staticmethod
    def csrf_headers(session: BrowserSession) -> dict[str, str]:
        return {"X-CSRF-Token": session.csrf_token}


def make_account_security_application(
    *,
    repository: AccountSecurityRepository,
    password_hasher: Argon2PasswordHasher,
):
    """Build an application whose mutable state exists for one test only."""

    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url=SecretStr(
            "postgresql://synthetic-user:synthetic-password@localhost/security-test"
        ),
        registration_rate_limit_attempts=100,
        login_rate_limit_attempts=100,
    )
    return create_app(
        settings=settings,
        database=StubDatabase(),
        user_repository=repository,
        authentication_repository=repository,
        saved_content_repository=repository,
        password_hasher=password_hasher,
    )
