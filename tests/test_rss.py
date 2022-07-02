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
        super().setUp()
        self.channeldata = CHANNELDATA

    def testGetRecentPackages(self):
        actual = rss.get_recent_packages(self.channeldata, 2)
        expected = [{"example1": self.channeldata["packages"]["example1"]}]
        self.assertDictEqual(actual[0], expected[0])

    def testIso822(self):
        print(":HI")
        self.assertEqual(rss.iso822(0), "Thu, 01 Jan 1970 00:00:00 GMT")
        self.assertEqual(rss.iso822(1656717698.601216), "Fri, 01 Jul 2022 23:21:38 GMT")


if __name__ == "__main__":
    unittest.main()
