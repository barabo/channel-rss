import unittest
import sys
import time

sys.path[0] = sys.path[0].rsplit("/", 1)[0]

import rss

DAY = 24 * 60 * 60
CHANNELDATA = {
    "channeldata_version": 1,
    "packages": {
        "example1": {
            "description": "Long description.",
            "dev_url": None,
            "doc_source_url": None,
            "doc_url": "https://anaconda.org/anaconda/example1",
            "home": "http://example1.org/",
            "license": "LGPL",
            "source_git_url": None,
            "source_url": "http://example1.org/package_sources.zip/download",
            "subdirs": ["win-32", "win-64"],
            "summary": "Short description",
            "timestamp": time.time() - 1 * DAY,
            "version": "123",
        },
        "example2": {
            "description": "Long description.",
            "dev_url": None,
            "doc_source_url": None,
            "doc_url": "https://anaconda.org/anaconda/example2",
            "home": "http://www.example2.com/",
            "license": "LGPL",
            "source_git_url": None,
            "source_url": "http://example2.com/src.tar.gz",
            "subdirs": ["win-32", "osx-64", "osx-64", "linux-64"],
            "summary": "Short description",
            "timestamp": time.time() - 3 * DAY,
            "version": "1.2.3.4",
        },
    },
}


class rssTest(unittest.TestCase):
    def setUp(self) -> None:
        self.channeldata = CHANNELDATA
        rss.time.time = lambda: 1656741161.774336
        self.maxDiff = None

    def tearDown(self) -> None:
        rss.time.time = time.time

    def testGetRecentPackages(self):
        actual = rss.get_recent_packages(self.channeldata, 2)
        expected = [{"example1": self.channeldata["packages"]["example1"]}]
        self.assertDictEqual(actual[0], expected[0])

    def testGetChannel(self):
        packages = rss.get_recent_packages(self.channeldata, 2)
        actual = rss.get_channel("example", packages, 2)
        expected = {
            "title": "anaconda.org/example",
            "link": "https://conda.anaconda.org/example",
            "description": "An anaconda.org community with 1 package updates in the past 2 days.",
            "pubDate": rss.iso822(time.time()),
            "lastBuildDate": rss.iso822(time.time()),
        }
        self.assertDictEqual(actual, expected)

    def testGetTitle(self):
        actual = rss.get_title("example2", "213", ["win-32", "linux-s390x"])
        expected = "example2 213 [linux-s390x, win-32]"
        self.assertEqual(actual, expected)

    def testIso822(self):
        self.assertEqual(rss.iso822(0), "Thu, 01 Jan 1970 00:00:00 GMT")
        self.assertEqual(rss.iso822(1656717698.601216), "Fri, 01 Jul 2022 23:21:38 GMT")


if __name__ == "__main__":
    unittest.main()
