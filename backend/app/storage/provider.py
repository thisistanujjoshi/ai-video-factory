from abc import ABC, abstractmethod
from pathlib import Path

from app.config import get_settings

STORAGE_ROOT = Path(__file__).resolve().parents[3] / "storage"


class StorageProvider(ABC):
    """Metadata lives in Postgres; media bytes live here. Local filesystem
    is the dev implementation -- see spec section 43."""

    @abstractmethod
    async def upload(self, key: str, data: bytes) -> str:
        """Store `data` under `key`, return a path/URI usable to read it back."""

    @abstractmethod
    async def download(self, key: str) -> bytes: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...


class LocalStorageProvider(StorageProvider):
    def __init__(self, root: Path = STORAGE_ROOT):
        self.root = root

    async def upload(self, key: str, data: bytes) -> str:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return str(path)

    async def download(self, key: str) -> bytes:
        return (self.root / key).read_bytes()

    async def delete(self, key: str) -> None:
        (self.root / key).unlink(missing_ok=True)


def get_storage_provider() -> StorageProvider:
    provider = get_settings().storage_provider or "local"
    if provider == "local":
        return LocalStorageProvider()
    raise ValueError(f"storage provider {provider!r} is not implemented yet")
