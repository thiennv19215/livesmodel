import unittest

from backend.services.stream_service import StreamService, StreamSourceError, validate_public_stream_url


def resolver_for(ip_address: str):
    def resolve(_hostname: str, port: int):
        return [(2, 1, 6, "", (ip_address, port))]

    return resolve


class StreamUrlValidationTests(unittest.TestCase):
    def test_accepts_public_http_source(self):
        result = validate_public_stream_url(
            "https://cdn.example.com/live/index.m3u8",
            resolver=resolver_for("93.184.216.34"),
        )
        self.assertEqual(result, "https://cdn.example.com/live/index.m3u8")

    def test_rejects_local_and_private_sources(self):
        with self.assertRaises(StreamSourceError):
            validate_public_stream_url("http://localhost/live.m3u8", resolver=resolver_for("127.0.0.1"))

        with self.assertRaises(StreamSourceError):
            validate_public_stream_url("http://camera.lan/live.m3u8", resolver=resolver_for("192.168.1.20"))

    def test_rejects_credentials_in_url(self):
        with self.assertRaises(StreamSourceError):
            validate_public_stream_url(
                "https://user:password@example.com/live.m3u8",
                resolver=resolver_for("93.184.216.34"),
            )


class ManifestRewriteTests(unittest.TestCase):
    def test_rewrites_segments_variants_and_key_urls(self):
        service = StreamService()
        manifest = """#EXTM3U
#EXT-X-KEY:METHOD=AES-128,URI="keys/live.key"
#EXT-X-STREAM-INF:BANDWIDTH=1200000
variants/720p.m3u8
#EXTINF:4.0,
segments/part-01.ts
"""

        rewritten = service.rewrite_manifest(manifest, "https://cdn.example.com/live/master.m3u8")
        proxy_lines = [line for line in rewritten.splitlines() if line.startswith("/api/stream/proxy/")]

        self.assertEqual(len(proxy_lines), 2)
        variant_token = proxy_lines[0].rsplit("/", 1)[-1]
        segment_token = proxy_lines[1].rsplit("/", 1)[-1]
        self.assertEqual(service.resolve_token(variant_token), "https://cdn.example.com/live/variants/720p.m3u8")
        self.assertEqual(service.resolve_token(segment_token), "https://cdn.example.com/live/segments/part-01.ts")

        key_proxy = rewritten.split('URI="', 1)[1].split('"', 1)[0]
        key_token = key_proxy.rsplit("/", 1)[-1]
        self.assertEqual(service.resolve_token(key_token), "https://cdn.example.com/live/keys/live.key")

    def test_reuses_token_for_same_url(self):
        service = StreamService()
        first = service._register_url("https://cdn.example.com/a.ts")
        second = service._register_url("https://cdn.example.com/a.ts")
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
