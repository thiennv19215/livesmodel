import asyncio
import ipaddress
import re
import socket
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, Optional
from urllib.parse import urljoin, urlparse

import httpx


HLS_CONTENT_TYPES = {
    "application/vnd.apple.mpegurl",
    "application/x-mpegurl",
    "audio/mpegurl",
    "audio/x-mpegurl",
}
MAX_MANIFEST_BYTES = 2 * 1024 * 1024
MAX_REGISTERED_URLS = 5000
URI_ATTRIBUTE_PATTERN = re.compile(r'URI=(?P<quote>["\'])(?P<uri>.*?)(?P=quote)')


class StreamSourceError(ValueError):
    """Raised when a stream source cannot be used safely."""


def _default_resolver(hostname: str, port: int) -> Iterable[tuple]:
    return socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)


def validate_public_stream_url(
    raw_url: str,
    resolver: Callable[[str, int], Iterable[tuple]] = _default_resolver,
) -> str:
    url = raw_url.strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise StreamSourceError("Nguồn phát phải là URL HTTP hoặc HTTPS hợp lệ")
    if parsed.username or parsed.password:
        raise StreamSourceError("URL nguồn phát không được chứa thông tin đăng nhập")

    hostname = parsed.hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise StreamSourceError("Không cho phép nguồn phát trỏ vào máy cục bộ")

    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError as exc:
        raise StreamSourceError("Cổng trong URL nguồn phát không hợp lệ") from exc
    try:
        addresses = resolver(hostname, port)
    except OSError as exc:
        raise StreamSourceError("Không phân giải được tên miền nguồn phát") from exc

    found_address = False
    for address in addresses:
        found_address = True
        ip_text = address[4][0]
        try:
            ip = ipaddress.ip_address(ip_text.split("%", 1)[0])
        except ValueError as exc:
            raise StreamSourceError("Nguồn phát trả về địa chỉ IP không hợp lệ") from exc
        if not ip.is_global:
            raise StreamSourceError("Không cho phép nguồn phát trỏ vào mạng nội bộ hoặc địa chỉ đặc biệt")

    if not found_address:
        raise StreamSourceError("Tên miền nguồn phát không có địa chỉ khả dụng")
    return url


@dataclass
class StreamProxyResponse:
    response: httpx.Response
    client: httpx.AsyncClient

    async def close(self) -> None:
        await self.response.aclose()
        await self.client.aclose()


class StreamService:
    def __init__(self) -> None:
        self.source_url = ""
        self.source_label = ""
        self.source_type = ""
        self.root_token = ""
        self.updated_at: Optional[float] = None
        self.last_error = ""
        self._token_urls: "OrderedDict[str, str]" = OrderedDict()
        self._lock = asyncio.Lock()

    def status(self) -> Dict[str, object]:
        return {
            "is_configured": bool(self.root_token),
            "label": self.source_label,
            "source_type": self.source_type,
            "source_url": self.source_url,
            "playback_url": f"/api/stream/proxy/{self.root_token}" if self.root_token else "",
            "updated_at": self.updated_at,
            "last_error": self.last_error,
        }

    async def configure(self, raw_url: str, label: str = "") -> Dict[str, object]:
        url = await asyncio.to_thread(validate_public_stream_url, raw_url)
        source_type = self._detect_source_type(url)
        async with self._lock:
            self._token_urls.clear()
            self.source_url = url
            self.source_label = label.strip()[:120]
            self.source_type = source_type
            self.updated_at = time.time()
            self.last_error = ""
            self.root_token = self._register_url(url)
        return self.status()

    async def clear(self) -> Dict[str, object]:
        async with self._lock:
            self.source_url = ""
            self.source_label = ""
            self.source_type = ""
            self.root_token = ""
            self.updated_at = time.time()
            self.last_error = ""
            self._token_urls.clear()
        return self.status()

    def resolve_token(self, token: str) -> str:
        url = self._token_urls.get(token)
        if not url:
            raise StreamSourceError("Liên kết phát đã hết hạn hoặc không hợp lệ")
        self._token_urls.move_to_end(token)
        return url

    async def open_remote(self, token: str, range_header: str = "") -> StreamProxyResponse:
        url = self.resolve_token(token)
        await asyncio.to_thread(validate_public_stream_url, url)
        headers = {
            "Accept": "*/*",
            "User-Agent": "LivestreamAgent/1.0 stream-proxy",
        }
        if range_header:
            headers["Range"] = range_header

        client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0),
            follow_redirects=False,
        )
        current_url = url
        try:
            for _ in range(5):
                request = client.build_request("GET", current_url, headers=headers)
                response = await client.send(request, stream=True)
                if response.status_code not in {301, 302, 303, 307, 308}:
                    return StreamProxyResponse(response=response, client=client)

                location = response.headers.get("location")
                await response.aclose()
                if not location:
                    raise StreamSourceError("Nguồn phát chuyển hướng nhưng thiếu địa chỉ đích")
                current_url = urljoin(current_url, location)
                await asyncio.to_thread(validate_public_stream_url, current_url)
            raise StreamSourceError("Nguồn phát chuyển hướng quá nhiều lần")
        except Exception:
            await client.aclose()
            raise

    def is_hls_response(self, url: str, content_type: str, first_bytes: bytes = b"") -> bool:
        clean_type = content_type.split(";", 1)[0].strip().lower()
        return (
            clean_type in HLS_CONTENT_TYPES
            or urlparse(url).path.lower().endswith(".m3u8")
            or first_bytes.lstrip().startswith(b"#EXTM3U")
        )

    def rewrite_manifest(self, manifest: str, base_url: str) -> str:
        rewritten = []
        for line in manifest.splitlines():
            stripped = line.strip()
            if not stripped:
                rewritten.append(line)
                continue

            if stripped.startswith("#"):
                def replace_uri(match: re.Match) -> str:
                    absolute_url = urljoin(base_url, match.group("uri"))
                    token = self._register_url(absolute_url)
                    return f'URI={match.group("quote")}/api/stream/proxy/{token}{match.group("quote")}'

                rewritten.append(URI_ATTRIBUTE_PATTERN.sub(replace_uri, line))
                continue

            absolute_url = urljoin(base_url, stripped)
            token = self._register_url(absolute_url)
            leading = line[: len(line) - len(line.lstrip())]
            rewritten.append(f"{leading}/api/stream/proxy/{token}")
        return "\n".join(rewritten) + "\n"

    def _register_url(self, url: str) -> str:
        for token, registered_url in list(self._token_urls.items()):
            if registered_url == url:
                self._token_urls.move_to_end(token)
                return token

        token = uuid.uuid4().hex
        self._token_urls[token] = url
        while len(self._token_urls) > MAX_REGISTERED_URLS:
            oldest_token = next(iter(self._token_urls))
            if oldest_token == self.root_token and len(self._token_urls) > 1:
                self._token_urls.move_to_end(oldest_token)
                continue
            self._token_urls.popitem(last=False)
        return token

    @staticmethod
    def _detect_source_type(url: str) -> str:
        path = urlparse(url).path.lower()
        if path.endswith(".m3u8"):
            return "hls"
        if path.endswith((".mp4", ".webm", ".ogg")):
            return "video"
        return "auto"
