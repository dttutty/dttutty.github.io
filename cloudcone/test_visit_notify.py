#!/usr/bin/env python3

import json
import os
import pathlib
import sys
import unittest
from unittest import mock


os.environ.setdefault("NTFY_TOPIC", "test-topic")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-key")
sys.path.insert(0, str(pathlib.Path(__file__).parent))

import visit_notify


class FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class NotificationTests(unittest.TestCase):
    @mock.patch("visit_notify.urllib.request.urlopen", return_value=FakeResponse())
    def test_notification_contains_full_ip_address(self, urlopen):
        for address in ("203.0.113.42", "2001:db8::42"):
            with self.subTest(address=address):
                visit_notify.publish_notification(
                    "这是一次来自移动设备的直接访问。",
                    "/research.html",
                    "direct",
                    address,
                    "Los Angeles, California, US",
                    "America/Los_Angeles",
                    "Mobile",
                    "iOS 18.5",
                    "Safari 18.5",
                    "zh-CN",
                    [
                        "  CF-IPCity: Los Angeles",
                        "  CF-Ray: 1234567890abcdef-LAX",
                    ],
                )
                request = urlopen.call_args.args[0]
                message = request.data.decode("utf-8")
                self.assertIn("AI Analysis:\n这是一次来自移动设备的直接访问。\n", message)
                self.assertIn(f"IP: {address}\n", message)
                self.assertIn("Device: Mobile\n", message)
                self.assertIn("OS: iOS 18.5\n", message)
                self.assertIn("Browser: Safari 18.5\n", message)
                self.assertIn("Language: zh-CN\n", message)
                self.assertIn("Cloudflare Details:\n", message)
                self.assertIn("  CF-IPCity: Los Angeles\n", message)
                self.assertIn("  CF-Ray: 1234567890abcdef-LAX", message)
                self.assertLess(len(message), 4096)

    def test_iphone_safari_client_details(self):
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 "
                "Mobile/15E148 Safari/604.1"
            ),
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        self.assertEqual(
            visit_notify.visitor_client(headers),
            ("Mobile", "iOS 18.5", "Safari 18.5", "zh-CN"),
        )

    def test_windows_edge_client_details(self):
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "CF-Device-Type": "desktop",
        }
        self.assertEqual(
            visit_notify.visitor_client(headers),
            ("Desktop", "Windows 10/11", "Edge 138.0.0.0", "en-US"),
        )

    def test_cloudflare_details_include_all_non_secret_headers(self):
        headers = {
            "CF-Connecting-IP": "203.0.113.42",
            "CF-IPCity": "Los Angeles",
            "CF-IPCountry": "US",
            "CF-Ray": "1234567890abcdef-LAX",
            "CF-Visitor": '{"scheme":"https"}',
            "CDN-Loop": "cloudflare; loops=1",
            "CF-Access-Jwt-Assertion": "must-not-leak",
            "User-Agent": "Mozilla/5.0",
        }
        details = visit_notify.cloudflare_details(headers)
        joined = "\n".join(details)
        self.assertIn("CF-Connecting-IP: 203.0.113.42", joined)
        self.assertIn("CF-IPCity: Los Angeles", joined)
        self.assertIn("CF-IPCountry: US", joined)
        self.assertIn("CF-Ray: 1234567890abcdef-LAX", joined)
        self.assertIn('CF-Visitor: {"scheme":"https"}', joined)
        self.assertIn("CDN-Loop: cloudflare; loops=1", joined)
        self.assertNotIn("must-not-leak", joined)
        self.assertNotIn("User-Agent", joined)

    @mock.patch("visit_notify.socket.getaddrinfo")
    @mock.patch("visit_notify.socket.gethostbyaddr")
    def test_verified_google_crawler_requires_matching_forward_dns(
        self, gethostbyaddr, getaddrinfo
    ):
        visit_notify.verified_google_address.cache_clear()
        gethostbyaddr.return_value = (
            "crawl-66-249-66-1.googlebot.com",
            [],
            ["66.249.66.1"],
        )
        getaddrinfo.return_value = [
            (2, 1, 6, "", ("66.249.66.1", 0)),
        ]
        headers = {"User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1)"}
        self.assertTrue(
            visit_notify.is_verified_google_crawler(headers, "66.249.66.1")
        )
        self.assertTrue(
            visit_notify.is_verified_google_crawler(
                {"User-Agent": "Storebot-Google/1.0"}, "66.249.66.1"
            )
        )
        self.assertFalse(
            visit_notify.is_verified_google_crawler(
                {"User-Agent": "Mozilla/5.0 Chrome/138.0"}, "66.249.66.1"
            )
        )

    @mock.patch("visit_notify.socket.getaddrinfo")
    @mock.patch("visit_notify.socket.gethostbyaddr")
    def test_spoofed_googlebot_fails_forward_dns(self, gethostbyaddr, getaddrinfo):
        visit_notify.verified_google_address.cache_clear()
        gethostbyaddr.return_value = (
            "crawl-203-0-113-42.googlebot.com",
            [],
            ["203.0.113.42"],
        )
        getaddrinfo.return_value = [(2, 1, 6, "", ("203.0.113.99", 0))]
        headers = {"User-Agent": "Googlebot/2.1"}
        self.assertFalse(
            visit_notify.is_verified_google_crawler(headers, "203.0.113.42")
        )

    @mock.patch("visit_notify.urllib.request.urlopen")
    def test_openai_responses_request_and_text_extraction(self, urlopen):
        response_body = {
            "output": [
                {"type": "reasoning"},
                {
                    "type": "message",
                    "content": [
                        {"type": "output_text", "text": "可能是真人直接访问。\n环境正常。"}
                    ],
                },
            ]
        }
        response = FakeResponse()
        response.read = mock.Mock(return_value=json.dumps(response_body).encode("utf-8"))
        urlopen.return_value = response

        analysis = visit_notify.analyze_visit(
            "/research.html",
            "direct",
            "203.0.113.42",
            "Los Angeles, California, US",
            "America/Los_Angeles",
            "Desktop",
            "Windows 10/11",
            "Edge 138",
            "zh-CN",
            ["  CF-Ray: 1234567890abcdef-LAX"],
        )

        self.assertEqual(analysis, "可能是真人直接访问。\n环境正常。")
        request = urlopen.call_args.args[0]
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(request.full_url, "https://api.openai.com/v1/responses")
        self.assertEqual(body["model"], "gpt-5.6-luna")
        self.assertEqual(body["reasoning"], {"effort": "none"})
        self.assertFalse(body["store"])
        self.assertIn("203.0.113.42", body["input"])


if __name__ == "__main__":
    unittest.main()
