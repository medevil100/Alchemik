import json
import unittest
from http.cookiejar import Cookie, CookieJar

from data.yahoo.yahoo_session import (
    YahooSession,
    YahooSessionError,
    FetchResult,
    OutcomeKind,
    ScreenerPage,
    ScreenerPagination,
)


class FakeResponse:
    def __init__(self, status_code, text, url=""):
        self.status_code = status_code
        self.text = text
        self.url = url

    def json(self):
        return json.loads(self.text)


class FakeCookies:
    def __init__(self, jar):
        self.jar = jar


def make_jar(domain=".yahoo.com", path="/", expires=9999999999, value=None):
    jar = CookieJar()
    cookie = Cookie(
        version=0,
        name="A3",
        value="SECRET_A3_VALUE",
        port=None,
        port_specified=False,
        domain=domain,
        domain_specified=True,
        domain_initial_dot=domain.startswith("."),
        path=path,
        path_specified=True,
        secure=False,
        expires=expires,
        discard=False,
        comment=None,
        comment_url=None,
        rest={"HttpOnly": None},
        rfc2109=False,
    )
    jar.set_cookie(cookie)
    return jar


class FakeTransport:
    def __init__(self):
        self.request_count = 0
        self.calls = []
        self._jar = None
        # map: (method, url) -> list of FakeResponse OR Exception OR callable
        self.responses = {}
        self.get_response = None
        self.post_response = None

    def _next(self, method, url):
        key = (method, url)
        if key in self.responses:
            pool = self.responses[key]
            item = pool.pop(0)
            return item
        # fallback generic
        if method == "GET":
            return self.get_response
        return self.post_response

    @property
    def cookies(self):
        return FakeCookies(self._jar)

    def get(self, url, params=None, timeout=30):
        self.request_count += 1
        self.calls.append(("GET", url, params))
        item = self._next("GET", url)
        if isinstance(item, Exception):
            raise item
        if callable(item):
            return item("GET", url, params)
        return item

    def post(self, url, data=None, headers=None, params=None, timeout=30):
        self.request_count += 1
        self.calls.append(("POST", url, params, data, headers))
        item = self._next("POST", url)
        if isinstance(item, Exception):
            raise item
        if callable(item):
            return item("POST", url, params, data, headers)
        return item


FC_URL = "https://fc.yahoo.com/"
CRUMB_URL = "https://query1.finance.yahoo.com/v1/test/getcrumb"
SCREENER_URL = "https://query1.finance.yahoo.com/v1/finance/screener"


def make_quote(symbol, price, quote_type="EQUITY", exchange="WSE",
               market="pl_market", currency="PLN"):
    return {
        "symbol": symbol,
        "quoteType": quote_type,
        "exchange": exchange,
        "market": market,
        "currency": currency,
        "regularMarketPrice": price,
    }


class TestYahooSessionBootstrap(unittest.TestCase):
    def setUp(self):
        self.transport = FakeTransport()

    def _session(self):
        return YahooSession(self.transport)

    def test_bootstrap_success_404_with_valid_a3_and_crumb_metadata(self):
        jar = make_jar(domain=".yahoo.com", path="/", expires=9999999999)
        self.transport._jar = jar
        self.transport.responses = {
            ("GET", FC_URL): [FakeResponse(404, "", FC_URL)],
            ("GET", CRUMB_URL): [FakeResponse(200, "abc123", CRUMB_URL)],
        }
        meta = self._session().bootstrap()

        self.assertTrue(meta["a3_present"])
        self.assertEqual(meta["a3_domain"], ".yahoo.com")
        self.assertEqual(meta["a3_path"], "/")
        self.assertTrue(meta["a3_expiry_present"])
        self.assertTrue(meta["crumb_present"])
        self.assertTrue(meta["crumb_non_html"])
        self.assertEqual(meta["crumb_length"], 6)

        # Secret values must not leak through metadata.
        dumped = json.dumps(meta)
        self.assertNotIn("SECRET_A3_VALUE", dumped)
        self.assertNotIn("abc123", dumped)

    def test_bootstrap_rejects_missing_a3(self):
        self.transport._jar = CookieJar()  # empty jar
        self.transport.responses = {
            ("GET", FC_URL): [FakeResponse(404, "", FC_URL)],
        }
        with self.assertRaises(YahooSessionError):
            self._session().bootstrap()

    def test_bootstrap_rejects_wrong_a3_domain(self):
        self.transport._jar = make_jar(domain="evil.com", path="/")
        self.transport.responses = {
            ("GET", FC_URL): [FakeResponse(404, "", FC_URL)],
        }
        with self.assertRaises(YahooSessionError):
            self._session().bootstrap()

    def test_bootstrap_rejects_wrong_a3_path(self):
        self.transport._jar = make_jar(domain=".yahoo.com", path="/other")
        self.transport.responses = {
            ("GET", FC_URL): [FakeResponse(404, "", FC_URL)],
        }
        with self.assertRaises(YahooSessionError):
            self._session().bootstrap()

    def test_bootstrap_rejects_missing_a3_expiry(self):
        self.transport._jar = make_jar(domain=".yahoo.com", path="/", expires=None)
        self.transport.responses = {
            ("GET", FC_URL): [FakeResponse(404, "", FC_URL)],
        }
        with self.assertRaises(YahooSessionError):
            self._session().bootstrap()

    def test_crumb_rejects_html(self):
        self.transport._jar = make_jar()
        self.transport.responses = {
            ("GET", FC_URL): [FakeResponse(404, "", FC_URL)],
            ("GET", CRUMB_URL): [FakeResponse(200, "<html><body>x</body></html>", CRUMB_URL)],
        }
        with self.assertRaises(YahooSessionError):
            self._session().bootstrap()

    def test_crumb_rejects_empty(self):
        self.transport._jar = make_jar()
        self.transport.responses = {
            ("GET", FC_URL): [FakeResponse(404, "", FC_URL)],
            ("GET", CRUMB_URL): [FakeResponse(200, "", CRUMB_URL)],
        }
        with self.assertRaises(YahooSessionError):
            self._session().bootstrap()

    def test_crumb_rejects_non_200(self):
        self.transport._jar = make_jar()
        self.transport.responses = {
            ("GET", FC_URL): [FakeResponse(404, "", FC_URL)],
            ("GET", CRUMB_URL): [FakeResponse(500, "err", CRUMB_URL)],
        }
        with self.assertRaises(YahooSessionError):
            self._session().bootstrap()

    def test_bootstrap_rejects_http_status_other_than_200_or_404(self):
        # Even with a valid A3 already present, any cookie-bootstrap status
        # other than 200/404 must abort before the crumb request.
        self.transport._jar = make_jar(domain=".yahoo.com", path="/", expires=9999999999)
        self.transport.responses = {
            ("GET", FC_URL): [FakeResponse(500, "", FC_URL)],
            ("GET", CRUMB_URL): [FakeResponse(200, "abc123", CRUMB_URL)],
        }
        with self.assertRaises(YahooSessionError):
            self._session().bootstrap()
        # Crumb request must NOT have been sent.
        self.assertFalse(any("getcrumb" in c[1] for c in self.transport.calls))


class TestYahooSessionScreener(unittest.TestCase):
    def setUp(self):
        self.transport = FakeTransport()
        self.transport._jar = make_jar()
        self.transport.responses = {
            ("GET", FC_URL): [FakeResponse(404, "", FC_URL)],
            ("GET", CRUMB_URL): [FakeResponse(200, "abc123", CRUMB_URL)],
        }
        self.session = YahooSession(self.transport)
        self.session.bootstrap()  # 2 requests (cookie + crumb)

    def test_screener_page_body_and_params(self):
        result = {
            "total": 1,
            "start": 0,
            "count": 1,
            "quotes": [make_quote("AAA.WA", 1.0)],
        }
        self.transport.responses[( "POST", SCREENER_URL)] = [
            FakeResponse(200, json.dumps({"finance": {"result": [result]}}), SCREENER_URL)
        ]
        res = self.session.fetch_screener_page(offset=0, size=250)
        self.assertEqual(res.kind, OutcomeKind.SUCCESS_WITH_DATA)

        # Inspect POST body
        post_call = [c for c in self.transport.calls if c[0] == "POST"][0]
        params = post_call[2]
        data = post_call[3]
        headers = post_call[4]
        self.assertEqual(params["crumb"], "abc123")
        self.assertEqual(params["corsDomain"], "finance.yahoo.com")
        self.assertEqual(params["formatted"], "false")
        self.assertEqual(params["lang"], "en-US")
        self.assertEqual(params["region"], "US")
        self.assertEqual(headers["Content-Type"], "application/json")

        body = json.loads(data)
        self.assertEqual(body["quoteType"], "EQUITY")
        self.assertEqual(body["size"], 250)
        self.assertEqual(body["offset"], 0)
        self.assertEqual(body["sortField"], "intradayprice")
        self.assertEqual(body["sortType"], "ASC")
        self.assertEqual(body["userId"], "")
        self.assertEqual(body["userIdType"], "guid")

        query = body["query"]
        self.assertEqual(query["operator"], "AND")
        operands = {op["operator"]: op["operands"] for op in query["operands"]}
        self.assertEqual(operands["EQ"], ["region", "pl"])
        self.assertEqual(operands["GTE"], ["intradayprice", 0.10])
        self.assertEqual(operands["LTE"], ["intradayprice", 10.00])

    def test_pagination_full_two_pages_consistent(self):
        quotes0 = [make_quote(f"S{i:03d}.WA", 0.5 + i * 0.001) for i in range(250)]
        quotes1 = [make_quote(f"S{i:03d}.WA", 0.5 + i * 0.001) for i in range(250, 429)]
        page0 = {"total": 429, "start": 0, "count": 250, "quotes": quotes0}
        page1 = {"total": 429, "start": 250, "count": 179, "quotes": quotes1}
        self.transport.responses[("POST", SCREENER_URL)] = [
            FakeResponse(200, json.dumps({"finance": {"result": [page0]}}), SCREENER_URL),
            FakeResponse(200, json.dumps({"finance": {"result": [page1]}}), SCREENER_URL),
        ]

        res = self.session.paginate_screener(size=250)
        self.assertEqual(res.kind, OutcomeKind.SUCCESS_WITH_DATA)
        pagination = res.data
        self.assertIsInstance(pagination, ScreenerPagination)
        self.assertEqual(pagination.total, 429)
        self.assertEqual(len(pagination.pages), 2)

        p0, p1 = pagination.pages
        self.assertEqual(p0.start, 0)
        self.assertEqual(p0.count, 250)
        self.assertEqual(len(p0.quotes), 250)
        self.assertEqual(p1.start, 250)
        self.assertEqual(p1.count, 179)
        self.assertEqual(len(p1.quotes), 179)

        all_symbols = [q["symbol"] for p in pagination.pages for q in p.quotes]
        self.assertEqual(len(all_symbols), len(set(all_symbols)), "duplicate symbols across pages")
        self.assertEqual(len(all_symbols), 429, "sum of records must equal total")

    def test_pagination_detects_duplicate_symbols(self):
        q = make_quote("AAA.WA", 1.0)
        page0 = {"total": 2, "start": 0, "count": 1, "quotes": [q]}
        page1 = {"total": 2, "start": 1, "count": 1, "quotes": [q]}
        self.transport.responses[("POST", SCREENER_URL)] = [
            FakeResponse(200, json.dumps({"finance": {"result": [page0]}}), SCREENER_URL),
            FakeResponse(200, json.dumps({"finance": {"result": [page1]}}), SCREENER_URL),
        ]
        with self.assertRaises(YahooSessionError):
            self.session.paginate_screener(size=250)

    def test_pagination_detects_empty_page_before_total(self):
        page0 = {"total": 5, "start": 0, "count": 0, "quotes": []}
        self.transport.responses[("POST", SCREENER_URL)] = [
            FakeResponse(200, json.dumps({"finance": {"result": [page0]}}), SCREENER_URL),
        ]
        with self.assertRaises(YahooSessionError):
            self.session.paginate_screener(size=250)

    def test_pagination_detects_start_mismatch(self):
        page0 = {"total": 2, "start": 7, "count": 1, "quotes": [make_quote("A.WA", 1.0)]}
        self.transport.responses[("POST", SCREENER_URL)] = [
            FakeResponse(200, json.dumps({"finance": {"result": [page0]}}), SCREENER_URL),
        ]
        with self.assertRaises(YahooSessionError):
            self.session.paginate_screener(size=250)

    def test_pagination_detects_count_mismatch(self):
        page0 = {"total": 2, "start": 0, "count": 5, "quotes": [make_quote("A.WA", 1.0)]}
        self.transport.responses[("POST", SCREENER_URL)] = [
            FakeResponse(200, json.dumps({"finance": {"result": [page0]}}), SCREENER_URL),
        ]
        with self.assertRaises(YahooSessionError):
            self.session.paginate_screener(size=250)

    def test_pagination_detects_total_change(self):
        page0 = {"total": 2, "start": 0, "count": 1, "quotes": [make_quote("A.WA", 1.0)]}
        page1 = {"total": 3, "start": 1, "count": 1, "quotes": [make_quote("B.WA", 1.0)]}
        self.transport.responses[("POST", SCREENER_URL)] = [
            FakeResponse(200, json.dumps({"finance": {"result": [page0]}}), SCREENER_URL),
            FakeResponse(200, json.dumps({"finance": {"result": [page1]}}), SCREENER_URL),
        ]
        with self.assertRaises(YahooSessionError):
            self.session.paginate_screener(size=250)


class TestYahooSessionChart(unittest.TestCase):
    def setUp(self):
        self.transport = FakeTransport()
        self.transport._jar = make_jar()
        self.transport.responses = {
            ("GET", FC_URL): [FakeResponse(404, "", FC_URL)],
            ("GET", CRUMB_URL): [FakeResponse(200, "abc123", CRUMB_URL)],
        }
        self.session = YahooSession(self.transport)
        self.session.bootstrap()

    def _chart_json(self):
        return json.dumps({
            "chart": {
                "result": [{
                    "meta": {"symbol": "AAA.WA", "currency": "PLN",
                             "exchangeName": "WSE", "instrumentType": "EQUITY"},
                    "timestamp": [1, 2, 3],
                    "indicators": {"quote": [{
                        "open": [1.0, 2.0, 3.0],
                        "high": [1.5, 2.5, 3.5],
                        "low": [0.5, 1.5, 2.5],
                        "close": [1.1, 2.1, 3.1],
                        "volume": [0, 100, 200],
                    }]},
                }],
                "error": None,
            }
        })

    def test_chart_daily_params(self):
        url = "https://query2.finance.yahoo.com/v8/finance/chart/AAA.WA"
        self.transport.responses[("GET", url)] = [
            FakeResponse(200, self._chart_json(), url)
        ]
        res = self.session.fetch_chart("AAA.WA", variant="daily")
        self.assertEqual(res.kind, OutcomeKind.SUCCESS_WITH_DATA)

        get_call = [c for c in self.transport.calls if c[0] == "GET" and "chart" in c[1]][0]
        self.assertEqual(get_call[1], url)
        params = get_call[2]
        self.assertEqual(params["range"], "1y")
        self.assertEqual(params["interval"], "1d")
        self.assertEqual(params["includePrePost"], "false")
        self.assertEqual(params["events"], "div,splits")
        self.assertEqual(params["crumb"], "abc123")

    def test_chart_intraday_params(self):
        url = "https://query2.finance.yahoo.com/v8/finance/chart/AAA.WA"
        self.transport.responses[("GET", url)] = [
            FakeResponse(200, self._chart_json(), url)
        ]
        self.session.fetch_chart("AAA.WA", variant="intraday")
        get_call = [c for c in self.transport.calls if c[0] == "GET" and "chart" in c[1]][0]
        params = get_call[2]
        self.assertEqual(params["range"], "5d")
        self.assertEqual(params["interval"], "5m")

    def test_chart_symbol_value_unchanged(self):
        symbol = "AAA.WA"
        url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}"
        self.transport.responses[("GET", url)] = [
            FakeResponse(200, self._chart_json(), url)
        ]
        self.session.fetch_chart(symbol, variant="daily")
        get_call = [c for c in self.transport.calls if c[0] == "GET" and "chart" in c[1]][0]
        # Symbol must appear verbatim in the URL path (dot preserved).
        self.assertEqual(get_call[1], url)

    def test_chart_neutral_http_error(self):
        url = "https://query2.finance.yahoo.com/v8/finance/chart/AAA.WA"
        self.transport.responses[("GET", url)] = [
            FakeResponse(404, '{"chart":{"result":null,"error":{}}}', url)
        ]
        res = self.session.fetch_chart("AAA.WA", variant="daily")
        self.assertEqual(res.kind, OutcomeKind.HTTP_ERROR)

    def test_chart_neutral_parse_error(self):
        url = "https://query2.finance.yahoo.com/v8/finance/chart/AAA.WA"
        self.transport.responses[("GET", url)] = [
            FakeResponse(200, "not json", url)
        ]
        res = self.session.fetch_chart("AAA.WA", variant="daily")
        self.assertEqual(res.kind, OutcomeKind.PARSE_ERROR)

    def test_chart_neutral_missing_fields(self):
        url = "https://query2.finance.yahoo.com/v8/finance/chart/AAA.WA"
        self.transport.responses[("GET", url)] = [
            FakeResponse(200, json.dumps({"unexpected": True}), url)
        ]
        res = self.session.fetch_chart("AAA.WA", variant="daily")
        self.assertEqual(res.kind, OutcomeKind.MISSING_FIELDS)

    def test_chart_neutral_no_data(self):
        url = "https://query2.finance.yahoo.com/v8/finance/chart/AAA.WA"
        self.transport.responses[("GET", url)] = [
            FakeResponse(200, json.dumps({"chart": {"result": None, "error": {"code": "Not Found"}}}), url)
        ]
        res = self.session.fetch_chart("AAA.WA", variant="daily")
        self.assertEqual(res.kind, OutcomeKind.SUCCESS_NO_DATA)

    def test_chart_neutral_transport_exception(self):
        url = "https://query2.finance.yahoo.com/v8/finance/chart/AAA.WA"
        self.transport.responses[("GET", url)] = [
            RuntimeError("network down")
        ]
        res = self.session.fetch_chart("AAA.WA", variant="daily")
        self.assertEqual(res.kind, OutcomeKind.TRANSPORT_EXCEPTION)

    def test_request_count_reflects_actual_requests(self):
        before = self.transport.request_count
        self.assertEqual(before, 2)  # bootstrap cookie + crumb

        url = "https://query2.finance.yahoo.com/v8/finance/chart/AAA.WA"
        self.transport.responses[("GET", url)] = [
            FakeResponse(200, self._chart_json(), url)
        ]
        result = {"total": 1, "start": 0, "count": 1, "quotes": [make_quote("AAA.WA", 1.0)]}
        self.transport.responses[("POST", SCREENER_URL)] = [
            FakeResponse(200, json.dumps({"finance": {"result": [result]}}), SCREENER_URL)
        ]

        self.session.fetch_screener_page(0)
        self.session.fetch_chart("AAA.WA", variant="daily")
        self.assertEqual(self.transport.request_count, 4)


if __name__ == "__main__":
    unittest.main()