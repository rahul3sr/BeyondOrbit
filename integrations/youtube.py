"""Live official discovery adapter. Not verified against live credentials."""
import json
import urllib.parse
import urllib.request


def discover(query, api_key):
    if not query.strip() or not api_key:
        raise ValueError("Query and authorized YouTube Data API key required")
    params = urllib.parse.urlencode(dict(part="snippet", type="video", q=query,
                                         maxResults=10, key=api_key))
    # Do not log the URL: it contains credentials. Caller handles sanitized failures.
    try:
        with urllib.request.urlopen("https://www.googleapis.com/youtube/v3/search?"+params, timeout=30) as r:
            return json.load(r)
    except Exception:
        raise RuntimeError("YouTube discovery failed; inspect authorization and network settings") from None


def publish(*args, **kwargs):
    raise RuntimeError("Publishing disabled pending official OAuth integration and authorized private-upload testing")
