import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path

FEED_URL = "https://l9o.dev/posts/index.xml"
README = Path(__file__).parent / "README.md"
START = "<!-- blog starts -->"
END = "<!-- blog ends -->"
MAX_POSTS = 5


def fetch_feed():
    with urllib.request.urlopen(FEED_URL, timeout=30) as response:
        return response.read()


def parse_posts(feed_xml, limit=MAX_POSTS):
    posts = [
        (
            item.findtext("title", "").strip(),
            item.findtext("link", "").strip(),
            parsedate_to_datetime(item.findtext("pubDate", "")).date(),
        )
        for item in ET.fromstring(feed_xml).iter("item")
    ]
    posts.sort(key=lambda post: post[2], reverse=True)
    return posts[:limit]


def escape_link_text(text):
    return text.replace("[", r"\[").replace("]", r"\]")


def render_posts(posts):
    return "\n".join(
        f"- [{escape_link_text(title)}]({link}) ({date:%b %Y})"
        for title, link, date in posts
    )


def replace_section(readme, content):
    if START not in readme or END not in readme:
        raise ValueError(f"README must contain {START} and {END}")
    before, rest = readme.split(START, 1)
    _, after = rest.split(END, 1)
    return f"{before}{START}\n{content}\n{END}{after}"


def main(readme=README, fetch=fetch_feed):
    posts = parse_posts(fetch())
    if not posts:
        raise SystemExit("Feed has no posts; leaving README untouched")
    readme.write_text(replace_section(readme.read_text(), render_posts(posts)))


if __name__ == "__main__":
    main()
