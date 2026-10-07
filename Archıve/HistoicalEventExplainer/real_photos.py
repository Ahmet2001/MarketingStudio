import html
import json
import os
import re
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen

from pydantic import BaseModel, Field

from api_retry import RetryPolicy, call_with_retry


COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"
COMMONS_PROVIDER_URL = "https://commons.wikimedia.org"
OPENVERSE_API_URL = "https://api.openverse.org/v1/images/"
OPENVERSE_PROVIDER_URL = "https://openverse.org"
DEFAULT_REAL_PHOTO_RESULTS = 12
DEFAULT_REAL_PHOTO_CANDIDATES = 10
DEFAULT_USER_AGENT = (
    "TopicExplainer/1.0 (documentary media search; "
    "set WIKIMEDIA_USER_AGENT to add contact information)"
)

_ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/tiff",
}
_NON_PHOTO_TERMS = {
    "ai-generated",
    "ai generated",
    "artificial intelligence generated",
    "midjourney",
    "stable diffusion",
    "dall-e",
    "computer-generated",
    "computer generated",
    "digital illustration",
    "vector image",
    "illustration",
    "line drawing",
    "pencil drawing",
    "digital drawing",
    "painting",
    "oil painting",
    "watercolor painting",
    "engraving",
    "lithograph",
    "political cartoon",
    "poster",
    "screenshot",
    "3d render",
    "photomontage",
    "photo montage",
    "collage",
    "locator map",
    "location map",
    "diagram",
    "infographic",
    "coat of arms",
    "logo",
}
_QUERY_NOISE_TERMS = {
    "actual",
    "agreement",
    "archive",
    "archival",
    "branch",
    "building",
    "conference",
    "crash",
    "crisis",
    "document",
    "economy",
    "event",
    "exterior",
    "interior",
    "kriz",
    "meeting",
    "operations",
    "photo",
    "photograph",
    "press",
    "reform",
}


class RealPhotoSelection(BaseModel):
    scene_number: int
    provider: str
    provider_url: str
    asset_id: str
    page_id: int | None = None
    title: str
    search_query: str
    creator: str
    credit: str = ""
    license: str
    license_url: str = ""
    usage_terms: str = ""
    date_created: str = ""
    description: str = ""
    page_url: str
    image_url: str
    local_file: str
    semantic_match_score: int | None = None
    semantic_match_reason: str = ""
    depiction_type: str = "unknown"
    credit_line: str


class RealPhotoManifest(BaseModel):
    provider: str = "Openverse + Wikimedia Commons"
    provider_url: str = OPENVERSE_PROVIDER_URL
    attribution_notice: str = (
        "Verify every source page before publication and reproduce each credit line. "
        "Openverse and Commons files have individual licenses; attribution, "
        "share-alike, and other conditions may apply."
    )
    photos: list[RealPhotoSelection] = Field(default_factory=list)


class NoRelevantPhotoError(RuntimeError):
    """Raised when authentic candidates exist but none safely depicts the scene."""


@dataclass(frozen=True)
class RealPhotoCandidate:
    search_query: str
    page_id: int
    title: str
    page_url: str
    image_url: str
    preview_url: str
    mime_type: str
    width: int
    height: int
    creator: str
    credit: str
    license: str
    license_url: str
    usage_terms: str
    date_created: str
    description: str
    categories: str
    match_score: int | None = None
    match_reason: str = ""
    depiction_type: str = "unknown"
    provider: str = "Wikimedia Commons"
    provider_url: str = COMMONS_PROVIDER_URL
    asset_id: str = ""


def _network_call(operation, *, label: str, retry_policy: RetryPolicy):
    def wrapped():
        try:
            return operation()
        except HTTPError:
            raise
        except (URLError, TimeoutError, OSError) as exc:
            raise ConnectionError(str(exc)) from exc

    return call_with_retry(wrapped, label=label, policy=retry_policy)


def _plain_text(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", html.unescape(without_tags)).strip()


def _metadata_value(metadata: dict[str, Any], key: str) -> str:
    item = metadata.get(key)
    if not isinstance(item, dict):
        return ""
    return _plain_text(str(item.get("value") or ""))


def _commons_page_url(title: str) -> str:
    encoded_title = quote(title.replace(" ", "_"), safe=":(),-")
    return f"{COMMONS_PROVIDER_URL}/wiki/{encoded_title}"


def _safe_download_url(value: str) -> bool:
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and (
        host == "upload.wikimedia.org"
        or host.endswith(".upload.wikimedia.org")
    )


def _looks_like_authentic_photo(
    *,
    title: str,
    mime_type: str,
    media_type: str,
    description: str,
    categories: str,
) -> bool:
    if mime_type not in _ALLOWED_MIME_TYPES:
        return False
    if media_type.upper() not in {"BITMAP", "UNKNOWN"}:
        return False
    searchable = " ".join((title, description, categories)).lower()
    return not any(term in searchable for term in _NON_PHOTO_TERMS)


def _credit_line(candidate: RealPhotoCandidate) -> str:
    creator = candidate.creator or candidate.credit or "Creator not stated"
    license_name = candidate.license or "License not stated"
    parts = [candidate.title, creator, license_name]
    if candidate.license_url:
        parts.append(candidate.license_url)
    parts.append(candidate.page_url)
    return " — ".join(parts)


def _query_variants(query: str) -> list[str]:
    """Relax an over-specific Commons query without losing its named subject."""
    normalized = " ".join(query.split()).strip()
    without_year = re.sub(r"\b(?:18|19|20)\d{2}\b", " ", normalized)
    without_year = re.sub(r"\s+", " ", without_year).strip(" ,-")

    tokens = re.findall(r"[\wÀ-ÖØ-öø-ÿİıŞşĞğÇçÖöÜü'-]+", without_year)
    without_noise = " ".join(
        token
        for token in tokens
        if token.casefold() not in _QUERY_NOISE_TERMS
    ).strip()
    localized_alias = re.sub(
        r"\bbankas[ıi]\b",
        "Bank",
        without_noise,
        flags=re.IGNORECASE,
    )
    localized_alias = re.sub(
        r"^(?:T\.?C\.?|TC)\s+",
        "",
        localized_alias,
        flags=re.IGNORECASE,
    ).strip()

    variants: list[str] = []
    for candidate in (without_year, without_noise, localized_alias):
        if (
            len(candidate) >= 3
            and candidate.casefold() != normalized.casefold()
            and candidate.casefold()
            not in {variant.casefold() for variant in variants}
        ):
            variants.append(candidate)
    return variants


class WikimediaCommonsClient:
    def __init__(
        self,
        *,
        retry_policy: RetryPolicy,
        timeout: int = 25,
        opener: Callable[..., Any] | None = None,
        user_agent: str | None = None,
        minimum_search_interval: float = 0.5,
    ) -> None:
        if minimum_search_interval < 0:
            raise ValueError("Minimum Wikimedia search interval cannot be negative.")
        self.retry_policy = retry_policy
        self.timeout = timeout
        self.opener = opener or urlopen
        self.user_agent = (
            user_agent
            or os.getenv("WIKIMEDIA_USER_AGENT")
            or DEFAULT_USER_AGENT
        )
        self._search_cache: dict[
            tuple[str, int],
            list[RealPhotoCandidate],
        ] = {}
        self.minimum_search_interval = minimum_search_interval
        self._last_search_request_at = 0.0

    def _throttle_search(self) -> None:
        elapsed = time.monotonic() - self._last_search_request_at
        remaining = self.minimum_search_interval - elapsed
        if remaining > 0:
            time.sleep(remaining)
        self._last_search_request_at = time.monotonic()

    def search(
        self,
        query: str,
        *,
        per_page: int = DEFAULT_REAL_PHOTO_RESULTS,
    ) -> list[RealPhotoCandidate]:
        if not 1 <= per_page <= 50:
            raise ValueError("Wikimedia results per query must be between 1 and 50.")
        normalized_query = " ".join(query.split()).strip()
        if not normalized_query:
            return []
        cache_key = (normalized_query.casefold(), per_page)
        if cache_key in self._search_cache:
            return list(self._search_cache[cache_key])

        parameters = urlencode(
            {
                "action": "query",
                "format": "json",
                "formatversion": "2",
                "generator": "search",
                "gsrsearch": f"{normalized_query} filetype:bitmap",
                "gsrnamespace": "6",
                "gsrlimit": per_page,
                "prop": "imageinfo",
                "iiprop": "url|mime|thumbmime|size|mediatype|extmetadata",
                "iiurlwidth": "1600",
                "iiextmetadatalanguage": "en",
                "iiextmetadatafilter": (
                    "ImageDescription|ObjectName|DateTimeOriginal|Artist|Credit|"
                    "LicenseShortName|LicenseUrl|UsageTerms|Categories"
                ),
                "uselang": "en",
                "origin": "*",
            }
        )
        request = Request(
            f"{COMMONS_API_URL}?{parameters}",
            headers={
                "Accept": "application/json",
                "User-Agent": self.user_agent,
            },
        )

        def request_search() -> dict[str, Any]:
            self._throttle_search()
            with self.opener(request, timeout=self.timeout) as response:
                payload = response.read()
            if not payload:
                raise ConnectionError("Wikimedia Commons returned an empty response.")
            try:
                decoded = json.loads(payload.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ConnectionError(
                    "Wikimedia Commons returned invalid search JSON."
                ) from exc
            if not isinstance(decoded, dict):
                raise ConnectionError(
                    "Wikimedia Commons returned an unexpected response."
                )
            return decoded

        decoded = _network_call(
            request_search,
            label=f"Wikimedia Commons search '{normalized_query}'",
            retry_policy=self.retry_policy,
        )

        candidates: list[RealPhotoCandidate] = []
        pages = decoded.get("query", {}).get("pages", [])
        if not isinstance(pages, list):
            return candidates
        for page in pages:
            if not isinstance(page, dict):
                continue
            image_info_items = page.get("imageinfo")
            if not isinstance(image_info_items, list) or not image_info_items:
                continue
            info = image_info_items[0]
            if not isinstance(info, dict):
                continue
            metadata = info.get("extmetadata")
            if not isinstance(metadata, dict):
                metadata = {}

            title = str(page.get("title") or "")
            image_url = str(info.get("thumburl") or info.get("url") or "")
            preview_url = str(info.get("thumburl") or image_url)
            mime_type = str(info.get("thumbmime") or info.get("mime") or "")
            media_type = str(info.get("mediatype") or "UNKNOWN")
            description = _metadata_value(metadata, "ImageDescription")
            categories = _metadata_value(metadata, "Categories")
            if not _safe_download_url(image_url) or not _safe_download_url(preview_url):
                continue
            if not _looks_like_authentic_photo(
                title=title,
                mime_type=mime_type,
                media_type=media_type,
                description=description,
                categories=categories,
            ):
                continue

            try:
                page_id = int(page["pageid"])
                width = int(info.get("width") or 0)
                height = int(info.get("height") or 0)
            except (KeyError, TypeError, ValueError):
                continue
            if max(width, height) < 300:
                continue

            candidates.append(
                RealPhotoCandidate(
                    search_query=normalized_query,
                    page_id=page_id,
                    title=title,
                    page_url=_commons_page_url(title),
                    image_url=image_url,
                    preview_url=preview_url,
                    mime_type=mime_type,
                    width=width,
                    height=height,
                    creator=_metadata_value(metadata, "Artist")[:500],
                    credit=_metadata_value(metadata, "Credit")[:1000],
                    license=_metadata_value(metadata, "LicenseShortName")
                    or _metadata_value(metadata, "UsageTerms")
                    or "See file page",
                    license_url=_metadata_value(metadata, "LicenseUrl"),
                    usage_terms=_metadata_value(metadata, "UsageTerms"),
                    date_created=_metadata_value(
                        metadata, "DateTimeOriginal"
                    )[:300],
                    description=(
                        description
                        or _metadata_value(metadata, "ObjectName")
                    )[:3000],
                    categories=categories[:1500],
                    asset_id=str(page_id),
                )
            )
        self._search_cache[cache_key] = list(candidates)
        return candidates

    def download(self, image_url: str) -> bytes:
        if not _safe_download_url(image_url):
            raise RuntimeError(
                f"Refusing unexpected Wikimedia download URL: {image_url}"
            )
        request = Request(
            image_url,
            headers={"User-Agent": self.user_agent},
        )

        def request_image() -> bytes:
            with self.opener(request, timeout=self.timeout) as response:
                image_bytes = response.read()
                content_type = str(response.headers.get("Content-Type", ""))
            if not image_bytes:
                raise ConnectionError("Wikimedia Commons returned an empty image.")
            if content_type and not content_type.lower().startswith("image/"):
                raise ConnectionError(
                    "Wikimedia Commons returned unexpected content type: "
                    f"{content_type}"
                )
            return image_bytes

        return _network_call(
            request_image,
            label="Wikimedia Commons image download",
            retry_policy=self.retry_policy,
        )


def _safe_openverse_image_url(value: str) -> bool:
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    allowed_hosts = (
        "api.openverse.org",
        "live.staticflickr.com",
        "farm.staticflickr.com",
        "upload.wikimedia.org",
    )
    return parsed.scheme == "https" and any(
        host == allowed or host.endswith(f".{allowed}")
        for allowed in allowed_hosts
    )


def _mime_type_from_url(value: str) -> str:
    suffix = Path(urlparse(value).path).suffix.lower()
    if suffix == ".png":
        return "image/png"
    if suffix == ".webp":
        return "image/webp"
    return "image/jpeg"


class OpenverseClient:
    def __init__(
        self,
        *,
        retry_policy: RetryPolicy,
        timeout: int = 25,
        opener: Callable[..., Any] | None = None,
        user_agent: str | None = None,
        minimum_search_interval: float = 0.25,
    ) -> None:
        if minimum_search_interval < 0:
            raise ValueError("Minimum Openverse search interval cannot be negative.")
        self.retry_policy = retry_policy
        self.timeout = timeout
        self.opener = opener or urlopen
        self.user_agent = (
            user_agent
            or os.getenv("OPENVERSE_USER_AGENT")
            or DEFAULT_USER_AGENT
        )
        self.minimum_search_interval = minimum_search_interval
        self._last_search_request_at = 0.0
        self._search_cache: dict[
            tuple[str, int],
            list[RealPhotoCandidate],
        ] = {}

    def _throttle_search(self) -> None:
        elapsed = time.monotonic() - self._last_search_request_at
        remaining = self.minimum_search_interval - elapsed
        if remaining > 0:
            time.sleep(remaining)
        self._last_search_request_at = time.monotonic()

    def search(
        self,
        query: str,
        *,
        per_page: int = DEFAULT_REAL_PHOTO_RESULTS,
    ) -> list[RealPhotoCandidate]:
        if not 1 <= per_page <= 50:
            raise ValueError("Openverse results per query must be between 1 and 50.")
        normalized_query = " ".join(query.split()).strip()
        if not normalized_query:
            return []
        cache_key = (normalized_query.casefold(), per_page)
        if cache_key in self._search_cache:
            return list(self._search_cache[cache_key])

        parameters = urlencode(
            {
                "q": normalized_query,
                "page_size": per_page,
                "mature": "false",
                "categories": "photograph",
                # Exclude non-commercial and no-derivatives licenses because scene
                # images are cropped/animated and videos may be monetized.
                "license": "by,by-sa,cc0,pdm",
            }
        )
        request = Request(
            f"{OPENVERSE_API_URL}?{parameters}",
            headers={
                "Accept": "application/json",
                "User-Agent": self.user_agent,
            },
        )

        def request_search() -> dict[str, Any]:
            self._throttle_search()
            with self.opener(request, timeout=self.timeout) as response:
                payload = response.read()
            if not payload:
                raise ConnectionError("Openverse returned an empty response.")
            try:
                decoded = json.loads(payload.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ConnectionError("Openverse returned invalid search JSON.") from exc
            if not isinstance(decoded, dict):
                raise ConnectionError("Openverse returned an unexpected response.")
            return decoded

        decoded = _network_call(
            request_search,
            label=f"Openverse search '{normalized_query}'",
            retry_policy=self.retry_policy,
        )
        raw_results = decoded.get("results")
        if not isinstance(raw_results, list):
            raw_results = []

        candidates: list[RealPhotoCandidate] = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            asset_id = str(item.get("id") or "").strip()
            title = _plain_text(str(item.get("title") or ""))
            image_url = str(item.get("url") or "")
            preview_url = str(item.get("thumbnail") or "")
            page_url = str(item.get("foreign_landing_url") or "")
            if (
                not asset_id
                or not _safe_openverse_image_url(image_url)
                or not _safe_openverse_image_url(preview_url)
                or not page_url.startswith("https://")
            ):
                continue
            try:
                width = int(item.get("width") or 0)
                height = int(item.get("height") or 0)
                page_id = -((uuid.UUID(asset_id).int % 2_000_000_000) + 1)
            except (TypeError, ValueError, AttributeError):
                continue
            if max(width, height) < 300:
                continue

            source = _plain_text(str(item.get("source") or "source"))
            creator = _plain_text(str(item.get("creator") or ""))[:500]
            license_code = str(item.get("license") or "").upper()
            license_version = str(item.get("license_version") or "").strip()
            license_name = " ".join(
                part for part in (license_code, license_version) if part
            ) or "See source page"
            tags = item.get("tags")
            tag_names = []
            if isinstance(tags, list):
                for tag in tags[:30]:
                    if isinstance(tag, dict) and tag.get("name"):
                        tag_names.append(_plain_text(str(tag["name"])))
            description = " ".join(
                part for part in (title, " ".join(tag_names)) if part
            )[:3000]
            if not _looks_like_authentic_photo(
                title=title,
                mime_type=_mime_type_from_url(image_url),
                media_type="BITMAP",
                description=description,
                categories="photograph",
            ):
                continue

            candidates.append(
                RealPhotoCandidate(
                    search_query=normalized_query,
                    page_id=page_id,
                    title=title or f"Openverse image {asset_id}",
                    page_url=page_url,
                    image_url=image_url,
                    preview_url=preview_url,
                    mime_type=_mime_type_from_url(image_url),
                    width=width,
                    height=height,
                    creator=creator,
                    credit=_plain_text(str(item.get("creator_url") or ""))[:1000],
                    license=license_name,
                    license_url=str(item.get("license_url") or ""),
                    usage_terms=license_name,
                    date_created=_plain_text(
                        str(item.get("created_on") or "")
                    )[:300],
                    description=description,
                    categories="photograph",
                    provider=f"Openverse ({source})",
                    provider_url=OPENVERSE_PROVIDER_URL,
                    asset_id=asset_id,
                )
            )

        self._search_cache[cache_key] = list(candidates)
        return candidates

    def download(self, image_url: str) -> bytes:
        if not _safe_openverse_image_url(image_url):
            raise RuntimeError(f"Refusing unexpected Openverse image URL: {image_url}")
        request = Request(image_url, headers={"User-Agent": self.user_agent})

        def request_image() -> bytes:
            with self.opener(request, timeout=self.timeout) as response:
                image_bytes = response.read()
                content_type = str(response.headers.get("Content-Type", ""))
            if not image_bytes:
                raise ConnectionError("Openverse returned an empty image.")
            if content_type and not content_type.lower().startswith("image/"):
                raise ConnectionError(
                    f"Openverse returned unexpected content type: {content_type}"
                )
            return image_bytes

        return _network_call(
            request_image,
            label="Openverse image download",
            retry_policy=self.retry_policy,
        )


class MultiProviderPhotoClient:
    def __init__(
        self,
        *,
        retry_policy: RetryPolicy,
    ) -> None:
        self.openverse = OpenverseClient(retry_policy=retry_policy)
        self.commons = WikimediaCommonsClient(retry_policy=retry_policy)

    def search(
        self,
        query: str,
        *,
        per_page: int = DEFAULT_REAL_PHOTO_RESULTS,
    ) -> list[RealPhotoCandidate]:
        per_source = max(2, (per_page + 1) // 2)
        provider_results: list[list[RealPhotoCandidate]] = []
        for provider_name, provider in (
            ("Openverse", self.openverse),
            ("Wikimedia Commons", self.commons),
        ):
            try:
                provider_results.append(
                    provider.search(query, per_page=per_source)
                )
            except Exception as exc:
                print(
                    f"Warning: {provider_name} search failed for {query!r} "
                    f"({exc})."
                )
                provider_results.append([])

        combined: list[RealPhotoCandidate] = []
        seen: set[tuple[str, str]] = set()
        max_length = max((len(items) for items in provider_results), default=0)
        for index in range(max_length):
            for items in provider_results:
                if index >= len(items):
                    continue
                candidate = items[index]
                key = (
                    candidate.provider.casefold(),
                    candidate.asset_id or str(candidate.page_id),
                )
                if key in seen:
                    continue
                seen.add(key)
                combined.append(candidate)
                if len(combined) >= per_page:
                    return combined
        return combined

    def download(self, image_url: str) -> bytes:
        if _safe_download_url(image_url):
            return self.commons.download(image_url)
        return self.openverse.download(image_url)


def _image_suffix(candidate: RealPhotoCandidate) -> str:
    mime_suffixes = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/tiff": ".jpg",
    }
    return mime_suffixes.get(candidate.mime_type, ".jpg")


def download_scene_real_photos(
    *,
    client: WikimediaCommonsClient,
    scene_queries: list[list[str]],
    images_dir: Path,
    scene_narrations: list[str] | None = None,
    visual_anchors: list[str] | None = None,
    photo_requirements: list[str] | None = None,
    candidate_selector: (
        Callable[
            [int, str, str, str, list[RealPhotoCandidate]],
            RealPhotoCandidate,
        ]
        | None
    ) = None,
    per_query: int = DEFAULT_REAL_PHOTO_RESULTS,
    max_candidates: int = DEFAULT_REAL_PHOTO_CANDIDATES,
) -> tuple[list[Path], RealPhotoManifest]:
    if not scene_queries:
        raise ValueError("At least one scene real-photo query list is required.")
    if not 1 <= per_query <= 50:
        raise ValueError("Wikimedia results per query must be between 1 and 50.")
    if not 1 <= max_candidates <= 20:
        raise ValueError("Real-photo candidate count must be between 1 and 20.")

    scene_narrations = scene_narrations or [""] * len(scene_queries)
    visual_anchors = visual_anchors or [""] * len(scene_queries)
    photo_requirements = photo_requirements or [""] * len(scene_queries)
    for values, label in (
        (scene_narrations, "narration"),
        (visual_anchors, "visual-anchor"),
        (photo_requirements, "photo-requirement"),
    ):
        if len(values) != len(scene_queries):
            raise ValueError(
                f"Scene {label} count must match real-photo query count."
            )

    image_paths: list[Path] = []
    selections: list[RealPhotoSelection] = []
    used_page_ids: set[int] = set()

    for scene_number, queries in enumerate(scene_queries, start=1):
        normalized_queries = [
            " ".join(query.split()).strip()
            for query in queries
            if " ".join(query.split()).strip()
        ]
        candidates: list[RealPhotoCandidate] = []
        candidate_page_ids: set[int] = set()
        target_candidate_count = min(4, max_candidates)
        per_query_cap = min(2, target_candidate_count)
        scene_query_schedule: list[tuple[str, bool]] = []
        for original_query in normalized_queries:
            scene_query_schedule.append((original_query, False))
            variants = _query_variants(original_query)
            for variant in variants:
                if variant.casefold() not in {
                    query.casefold()
                    for query, _ in scene_query_schedule
                }:
                    scene_query_schedule.append((variant, True))

        for query, is_relaxed in scene_query_schedule:
            if is_relaxed:
                print(
                    f"Broadening authentic-photo search for scene {scene_number}: "
                    f"{query}"
                )
            query_candidates = client.search(query, per_page=per_query)
            added_for_query = 0
            for candidate in query_candidates:
                if candidate.page_id in used_page_ids | candidate_page_ids:
                    continue
                candidates.append(candidate)
                candidate_page_ids.add(candidate.page_id)
                added_for_query += 1
                if (
                    added_for_query >= per_query_cap
                    or len(candidates) >= target_candidate_count
                ):
                    break
            if not query_candidates:
                if not is_relaxed:
                    print(
                        f"No authentic provider photo found for scene "
                        f"{scene_number}: {query}"
                    )
            if len(candidates) >= target_candidate_count:
                break

        if not candidates:
            raise RuntimeError(
                f"Photo providers returned no usable authentic photo for scene "
                f"{scene_number} after {len(normalized_queries)} queries."
            )

        if candidate_selector is None:
            selected = candidates[0]
        else:
            try:
                selected = candidate_selector(
                    scene_number,
                    scene_narrations[scene_number - 1],
                    visual_anchors[scene_number - 1],
                    photo_requirements[scene_number - 1],
                    candidates,
                )
            except NoRelevantPhotoError as first_error:
                if len(candidates) >= max_candidates:
                    raise
                print(
                    f"Best scene {scene_number} photo was too weak; searching "
                    "additional scene-specific documentary evidence."
                )
                previous_candidate_count = len(candidates)
                retry_queries = [
                    query for query, _ in scene_query_schedule
                ]
                for query in retry_queries:
                    if len(candidates) >= max_candidates:
                        break
                    query_candidates = client.search(query, per_page=per_query)
                    for candidate in query_candidates:
                        if candidate.page_id in used_page_ids | candidate_page_ids:
                            continue
                        candidates.append(candidate)
                        candidate_page_ids.add(candidate.page_id)
                        if len(candidates) >= max_candidates:
                            break
                if len(candidates) == previous_candidate_count:
                    raise first_error
                selected = candidate_selector(
                    scene_number,
                    scene_narrations[scene_number - 1],
                    visual_anchors[scene_number - 1],
                    photo_requirements[scene_number - 1],
                    candidates,
                )
            if selected.page_id not in candidate_page_ids:
                raise RuntimeError(
                    "Real-photo candidate selector returned an unknown image."
                )

        output_path = images_dir / (
            f"scene_{scene_number:03d}{_image_suffix(selected)}"
        )
        output_path.write_bytes(client.download(selected.image_url))
        image_paths.append(output_path)
        used_page_ids.add(selected.page_id)

        selection = RealPhotoSelection(
            scene_number=scene_number,
            provider=selected.provider,
            provider_url=selected.provider_url,
            asset_id=selected.asset_id or str(selected.page_id),
            page_id=selected.page_id,
            title=selected.title,
            search_query=selected.search_query,
            creator=selected.creator,
            credit=selected.credit,
            license=selected.license,
            license_url=selected.license_url,
            usage_terms=selected.usage_terms,
            date_created=selected.date_created,
            description=selected.description,
            page_url=selected.page_url,
            image_url=selected.image_url,
            local_file=str(output_path),
            semantic_match_score=selected.match_score,
            semantic_match_reason=selected.match_reason,
            depiction_type=selected.depiction_type,
            credit_line=_credit_line(selected),
        )
        selections.append(selection)
        print(
            f"Authentic photo saved for scene {scene_number}: {selected.title}"
        )

    return image_paths, RealPhotoManifest(photos=selections)


def save_real_photo_manifest(
    manifest: RealPhotoManifest,
    path: Path,
) -> None:
    path.write_text(
        json.dumps(manifest.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def save_real_photo_credits(
    manifest: RealPhotoManifest,
    path: Path,
) -> None:
    lines = [
        "REAL PHOTO CREDITS",
        "",
        manifest.attribution_notice,
        "",
    ]
    for photo in manifest.photos:
        lines.append(f"Scene {photo.scene_number}: {photo.credit_line}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
