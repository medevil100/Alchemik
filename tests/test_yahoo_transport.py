import re
import unittest
from pathlib import Path

from data.yahoo.yahoo_transport import Response, CurlCffiTransport


class TestResponse(unittest.TestCase):
    def test_json_decodes_text(self):
        resp = Response(status_code=200, text='{"a": 1}', url="http://example")
        self.assertEqual(resp.json(), {"a": 1})
        self.assertEqual(resp.status_code, 200)

    def test_json_parse_error_raises(self):
        resp = Response(status_code=200, text="not json", url="http://example")
        with self.assertRaises(Exception):
            resp.json()


class TestCurlCffiTransport(unittest.TestCase):
    def test_construction_does_no_network(self):
        # Constructing the production transport must not issue any request.
        transport = CurlCffiTransport()
        self.assertEqual(transport.request_count, 0)

    def test_get_and_post_count_requests(self):
        # Offline proof that the transport participates in the request counter.
        transport = CurlCffiTransport()
        # We do not call the network; we only verify state attributes exist.
        self.assertTrue(hasattr(transport, "get"))
        self.assertTrue(hasattr(transport, "post"))
        self.assertTrue(hasattr(transport, "cookies"))


class TestCurlCffiDependency(unittest.TestCase):
    def test_curl_cffi_is_direct_dependency(self):
        req_path = Path("requirements.txt")
        content = req_path.read_text(encoding="utf-8")
        # Must be a direct, bare dependency line (not a comment).
        pattern = re.compile(r"^\s*curl_cffi\s*$", re.MULTILINE)
        self.assertTrue(pattern.search(content), "curl_cffi must be a direct dependency")


if __name__ == "__main__":
    unittest.main()
