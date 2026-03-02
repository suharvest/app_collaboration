"""
Resource resolver for cloud materials support.

Downloads remote assets (URLs) to a local cache directory and returns the
cached path.  Local paths are resolved against a base directory as before.
All ``path`` / ``file`` fields in device YAML configs can therefore hold
either a relative local path **or** an ``https://`` URL – the resolver
handles both transparently.
"""

import hashlib
import logging
import os
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from urllib.parse import unquote, urlparse

logger = logging.getLogger(__name__)


class ResourceResolver:
    """Download and cache remote resources."""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir / "downloads"

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    @staticmethod
    def is_url(reference: str) -> bool:
        """Return *True* if *reference* looks like an HTTP(S) URL."""
        return isinstance(reference, str) and reference.startswith(
            ("http://", "https://")
        )

    # ------------------------------------------------------------------
    # Core resolve
    # ------------------------------------------------------------------

    async def resolve(
        self,
        reference: str,
        base_path: Optional[str] = None,
        checksum: Optional[Dict[str, str]] = None,
        progress_callback: Optional[Callable] = None,
    ) -> str:
        """Resolve a resource reference to a local file path.

        * If *reference* is a URL it is downloaded (with caching) and the
          local cache path is returned.
        * If *reference* is a relative path it is joined with *base_path*.
        * Absolute paths are returned as-is.
        """
        if self.is_url(reference):
            return await self._download_and_cache(
                reference, checksum, progress_callback
            )
        if base_path and not os.path.isabs(reference):
            return str(Path(base_path) / reference)
        return reference

    # ------------------------------------------------------------------
    # Download & cache
    # ------------------------------------------------------------------

    async def _download_and_cache(
        self,
        url: str,
        checksum: Optional[Dict[str, str]] = None,
        progress_callback: Optional[Callable] = None,
    ) -> str:
        """Download *url* into the cache directory (if not already cached)."""
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
        filename = self._filename_from_url(url)
        cache_dir = self.cache_dir / url_hash
        cache_path = cache_dir / filename

        # Check cache – if file exists and checksum matches, skip download
        if cache_path.exists():
            if checksum and not self._verify_checksum(cache_path, checksum):
                logger.info("Cached file checksum mismatch, re-downloading: %s", url)
            else:
                logger.info("Using cached file: %s", cache_path)
                return str(cache_path)

        # Download
        cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Downloading %s → %s", url, cache_path)

        if progress_callback:
            await self._report(progress_callback, f"Downloading {filename}...")

        try:
            await self._stream_download(url, cache_path, progress_callback)
        except Exception as exc:
            # Clean up partial download
            if cache_path.exists():
                cache_path.unlink()
            raise RuntimeError(f"Download failed for {url}: {exc}") from exc

        # Verify checksum after download
        if checksum and not self._verify_checksum(cache_path, checksum):
            cache_path.unlink()
            raise RuntimeError(f"Checksum verification failed after downloading {url}")

        if progress_callback:
            await self._report(progress_callback, f"Downloaded {filename}")

        return str(cache_path)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    MAX_RETRIES = 3

    async def _stream_download(
        self,
        url: str,
        dest: Path,
        progress_callback: Optional[Callable] = None,
    ) -> None:
        """Stream-download *url* to *dest* with retry on failure."""
        last_error: Optional[Exception] = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                await self._stream_download_once(url, dest, progress_callback)
                return  # success
            except Exception as exc:
                last_error = exc
                if attempt < self.MAX_RETRIES:
                    wait = attempt * 2  # 2s, 4s
                    logger.warning(
                        "Download attempt %d/%d failed for %s: %s  (retry in %ds)",
                        attempt,
                        self.MAX_RETRIES,
                        Path(url).name,
                        exc,
                        wait,
                    )
                    if progress_callback:
                        await self._report(
                            progress_callback,
                            f"Download interrupted, retrying ({attempt}/{self.MAX_RETRIES})...",
                        )
                    import asyncio

                    await asyncio.sleep(wait)
                    # Clean up partial file
                    if dest.exists():
                        dest.unlink()

        raise last_error  # type: ignore[misc]

    async def _stream_download_once(
        self,
        url: str,
        dest: Path,
        progress_callback: Optional[Callable] = None,
    ) -> None:
        """Single attempt to stream-download *url* to *dest*."""
        import httpx

        timeout = httpx.Timeout(30.0, read=120.0)
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()

                total = int(response.headers.get("content-length", 0))
                downloaded = 0

                with open(dest, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=65536):
                        f.write(chunk)
                        downloaded += len(chunk)

                        if progress_callback and total > 0:
                            pct = min(99, downloaded * 100 // total)
                            await self._report(
                                progress_callback,
                                f"Downloading {dest.name} ({downloaded // 1024}KB / {total // 1024}KB)",
                                pct,
                            )

    @staticmethod
    def _filename_from_url(url: str) -> str:
        """Extract a sensible filename from a URL."""
        parsed = urlparse(url)
        path = unquote(parsed.path)
        name = Path(path).name
        return name if name else "download"

    @staticmethod
    def _verify_checksum(path: Path, checksums: Dict[str, str]) -> bool:
        """Verify file against checksums (supports sha256, md5)."""
        for algo, expected in checksums.items():
            algo_lower = algo.lower()
            if algo_lower not in ("sha256", "md5"):
                logger.warning("Unsupported checksum algorithm: %s", algo)
                continue
            h = hashlib.new(algo_lower)
            with open(path, "rb") as f:
                for block in iter(lambda: f.read(65536), b""):
                    h.update(block)
            actual = h.hexdigest()
            if actual != expected:
                logger.error(
                    "Checksum mismatch for %s: expected %s, got %s",
                    path,
                    expected,
                    actual,
                )
                return False
        return True

    @staticmethod
    async def _report(
        callback: Callable,
        message: str,
        progress: Optional[int] = None,
    ) -> None:
        """Fire a progress callback (best-effort)."""
        try:
            if progress is not None:
                await callback("resolve_assets", progress, message)
            else:
                await callback("resolve_assets", 0, message)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------


def _create_resolver() -> ResourceResolver:
    from ..config import settings

    return ResourceResolver(settings.cache_dir)


# Lazy singleton – import ``resource_resolver`` from this module.
class _LazyResolver:
    """Delay construction until first attribute access so that importing
    this module does not trigger ``settings`` evaluation at import time."""

    _instance: Optional[ResourceResolver] = None

    def __getattr__(self, name: str) -> Any:
        if self._instance is None:
            self._instance = _create_resolver()
        return getattr(self._instance, name)


resource_resolver: ResourceResolver = _LazyResolver()  # type: ignore[assignment]
