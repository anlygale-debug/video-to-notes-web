import unittest
from unittest.mock import patch

from vtn.adapters.images import _validate_thumbnail_url
from vtn.domain.errors import DomainError


class ThumbnailUrlValidationTests(unittest.TestCase):
    @patch(
        "socket.getaddrinfo",
        return_value=[(None, None, None, None, ("8.8.8.8", 443))],
    )
    def test_allows_douyin_cover_host(self, _getaddrinfo):
        url = "https://p3-sign.douyinpic.com/tos-cn-p-0015/cover.jpeg"

        self.assertEqual(_validate_thumbnail_url(url), url)

    def test_rejects_douyin_cover_lookalike_host(self):
        with self.assertRaises(DomainError):
            _validate_thumbnail_url(
                "https://p3-sign.douyinpic.com.attacker.test/cover.jpeg"
            )


if __name__ == "__main__":
    unittest.main()
