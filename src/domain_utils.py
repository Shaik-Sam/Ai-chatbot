import re
from urllib.parse import urlparse


DOMAIN_PATTERN = re.compile(
    r"^(?:https?://)?(?:www\.)?([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+)$",
    re.IGNORECASE,
)


def looks_like_domain(value):
    if not value:
        return False
    cleaned = value.strip().lower()
    if " " in cleaned:
        return False
    if cleaned.startswith("http://") or cleaned.startswith("https://"):
        cleaned = urlparse(cleaned).netloc or cleaned
    cleaned = cleaned.replace("www.", "")
    return bool(DOMAIN_PATTERN.match(cleaned))


def normalize_domain(value):
    if not value:
        return ""
    cleaned = value.strip().lower()
    if cleaned.startswith("http://") or cleaned.startswith("https://"):
        parsed = urlparse(cleaned)
        cleaned = parsed.netloc or parsed.path
    cleaned = cleaned.split("/")[0]
    cleaned = cleaned.split("?")[0]
    cleaned = cleaned.replace("www.", "")
    return cleaned


def normalize_name(value):
    if not value:
        return ""
    return " ".join(value.strip().split())


def parse_input_row(name, domain):
    name = normalize_name(name)
    domain = normalize_domain(domain)
    if not domain and looks_like_domain(name):
        domain = normalize_domain(name)
        if domain == normalize_domain(name):
            name = ""
    return name, domain
