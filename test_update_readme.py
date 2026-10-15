import tempfile
import unittest
from datetime import date
from pathlib import Path

from update_readme import main, parse_posts, render_posts, replace_section


def item(title, slug, pub_date):
    return (
        f"<item><title>{title}</title>"
        f"<link>https://l9o.dev/posts/{slug}/</link>"
        f"<pubDate>{pub_date}</pubDate>"
        f"<guid>https://l9o.dev/posts/{slug}/</guid>"
        f"<description>&lt;p&gt;Summary&lt;/p&gt;</description></item>"
    )


def feed(*items):
    return (
        '<?xml version="1.0" encoding="utf-8" standalone="yes"?>'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>'
        "<title>Posts on l9o.dev</title><link>https://l9o.dev/posts/</link>"
        "<generator>Hugo</generator>"
        '<atom:link href="https://l9o.dev/posts/index.xml" rel="self" type="application/rss+xml"/>'
        + "".join(items)
        + "</channel></rss>"
    ).encode()


PING = item("Thou shall only ping once", "thou-shall-only-ping-once", "Fri, 26 Dec 2025 00:00:00 -0500")
SIGLENT = item(
    "Remote Code Execution on the Siglent SDS1104X-E",
    "remote-code-execution-on-the-siglent-sds1104x-e",
    "Tue, 23 Dec 2025 00:00:00 -0500",
)
MARINER = item(
    "Controlling an Elegoo Mars Pro remotely",
    "controlling-an-elegoo-mars-pro-remotely",
    "Sun, 18 Oct 2020 00:00:00 -0400",
)

README = """Hi! I'm Luiz.

### Recent writing

<!-- blog starts -->
- [Old post](https://l9o.dev/posts/old/) (Jan 2019)
<!-- blog ends -->

### Say hi
"""


class ParsePostsTest(unittest.TestCase):
    def test_parses_hugo_feed(self):
        self.assertEqual(
            parse_posts(feed(PING, SIGLENT)),
            [
                ("Thou shall only ping once", "https://l9o.dev/posts/thou-shall-only-ping-once/", date(2025, 12, 26)),
                (
                    "Remote Code Execution on the Siglent SDS1104X-E",
                    "https://l9o.dev/posts/remote-code-execution-on-the-siglent-sds1104x-e/",
                    date(2025, 12, 23),
                ),
            ],
        )

    def test_sorts_newest_first(self):
        titles = [title for title, _, _ in parse_posts(feed(MARINER, PING, SIGLENT))]
        self.assertEqual(
            titles,
            [
                "Thou shall only ping once",
                "Remote Code Execution on the Siglent SDS1104X-E",
                "Controlling an Elegoo Mars Pro remotely",
            ],
        )

    def test_limits_number_of_posts(self):
        self.assertEqual(len(parse_posts(feed(PING, SIGLENT, MARINER), limit=2)), 2)

    def test_empty_feed(self):
        self.assertEqual(parse_posts(feed()), [])


class RenderPostsTest(unittest.TestCase):
    def test_renders_markdown_list(self):
        self.assertEqual(
            render_posts(parse_posts(feed(PING, MARINER))),
            "- [Thou shall only ping once](https://l9o.dev/posts/thou-shall-only-ping-once/) (Dec 2025)\n"
            "- [Controlling an Elegoo Mars Pro remotely]"
            "(https://l9o.dev/posts/controlling-an-elegoo-mars-pro-remotely/) (Oct 2020)",
        )

    def test_escapes_brackets_in_titles(self):
        posts = [("Fixing [WIP] bugs", "https://l9o.dev/posts/wip/", date(2026, 1, 1))]
        self.assertEqual(render_posts(posts), r"- [Fixing \[WIP\] bugs](https://l9o.dev/posts/wip/) (Jan 2026)")


class ReplaceSectionTest(unittest.TestCase):
    def test_replaces_only_between_markers(self):
        updated = replace_section(README, "- new")
        self.assertIn("<!-- blog starts -->\n- new\n<!-- blog ends -->", updated)
        self.assertNotIn("Old post", updated)
        self.assertTrue(updated.startswith("Hi! I'm Luiz.\n\n### Recent writing\n\n"))
        self.assertTrue(updated.endswith("\n\n### Say hi\n"))

    def test_is_idempotent(self):
        once = replace_section(README, "- new")
        self.assertEqual(replace_section(once, "- new"), once)

    def test_missing_markers(self):
        with self.assertRaises(ValueError):
            replace_section("Hi! I'm Luiz.\n", "- new")


class MainTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.readme = Path(directory.name) / "README.md"
        self.readme.write_text(README)

    def test_updates_readme_from_feed(self):
        main(self.readme, fetch=lambda: feed(SIGLENT, PING))
        self.assertEqual(
            self.readme.read_text(),
            README.replace(
                "- [Old post](https://l9o.dev/posts/old/) (Jan 2019)",
                "- [Thou shall only ping once](https://l9o.dev/posts/thou-shall-only-ping-once/) (Dec 2025)\n"
                "- [Remote Code Execution on the Siglent SDS1104X-E]"
                "(https://l9o.dev/posts/remote-code-execution-on-the-siglent-sds1104x-e/) (Dec 2025)",
            ),
        )

    def test_empty_feed_leaves_readme_untouched(self):
        with self.assertRaises(SystemExit):
            main(self.readme, fetch=lambda: feed())
        self.assertEqual(self.readme.read_text(), README)

    def test_fetch_failure_leaves_readme_untouched(self):
        def failing_fetch():
            raise OSError("network unreachable")

        with self.assertRaises(OSError):
            main(self.readme, fetch=failing_fetch)
        self.assertEqual(self.readme.read_text(), README)


if __name__ == "__main__":
    unittest.main()
