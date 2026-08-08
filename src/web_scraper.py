import json
import re

from bs4 import BeautifulSoup


LEADERSHIP_KEYWORDS = (
    "ceo",
    "chief executive officer",
    "founder",
    "co-founder",
    "president",
    "managing director",
)


class WebScraper:
    def __init__(self, session):
        self.session = session

    def fetch_site_data(self, domain):
        if not domain:
            return {}
        urls = [f"https://{domain}", f"http://{domain}"]
        for url in urls:
            try:
                response = self.session.get(
                    url,
                    timeout=15,
                    allow_redirects=True,
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                if response.status_code >= 400:
                    continue
                return self._parse_html(response.text, response.url)
            except Exception:
                continue
        return {}

    def _parse_html(self, html, final_url):
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        og = {}
        for tag in soup.find_all("meta"):
            prop = tag.get("property") or tag.get("name") or ""
            content = tag.get("content") or ""
            if prop:
                og[prop.lower()] = content
        structured = self._extract_json_ld(soup)
        leadership = self._extract_leadership(soup, structured)
        description = (
            og.get("og:description")
            or og.get("description")
            or structured.get("description")
            or ""
        )
        linkedin = structured.get("linkedin") or og.get("og:see_also") or ""
        if "linkedin.com/company" not in linkedin.lower():
            linkedin = self._find_linkedin_link(soup)
        company_name = structured.get("name") or og.get("og:site_name") or self._clean_title(title)
        return {
            "company_name": company_name,
            "description": description[:500],
            "linkedin_url": linkedin,
            "industry": structured.get("industry", ""),
            "headquarters": structured.get("headquarters", ""),
            "ceo_founder_name": leadership.get("name", ""),
            "ceo_founder_title": leadership.get("title", ""),
            "final_url": final_url,
        }

    def _extract_json_ld(self, soup):
        result = {}
        for script in soup.find_all("script", type="application/ld+json"):
            if not script.string:
                continue
            try:
                payload = json.loads(script.string)
            except json.JSONDecodeError:
                continue
            items = payload if isinstance(payload, list) else [payload]
            for item in items:
                if not isinstance(item, dict):
                    continue
                item_type = item.get("@type", "")
                if item_type in ("Organization", "Corporation", "LocalBusiness", "Company"):
                    result["name"] = result.get("name") or item.get("name", "")
                    result["description"] = result.get("description") or item.get("description", "")
                    result["industry"] = result.get("industry") or item.get("industry", "")
                    address = item.get("address")
                    if isinstance(address, dict):
                        parts = [
                            address.get("addressLocality", ""),
                            address.get("addressRegion", ""),
                            address.get("addressCountry", ""),
                        ]
                        result["headquarters"] = result.get("headquarters") or ", ".join(
                            part for part in parts if part
                        )
                    same_as = item.get("sameAs")
                    links = same_as if isinstance(same_as, list) else [same_as] if same_as else []
                    for link in links:
                        if isinstance(link, str) and "linkedin.com/company" in link.lower():
                            result["linkedin"] = link
                if item_type == "Person":
                    job = (item.get("jobTitle") or "").lower()
                    if any(keyword in job for keyword in LEADERSHIP_KEYWORDS):
                        result.setdefault("person_name", item.get("name", ""))
                        result.setdefault("person_title", item.get("jobTitle", ""))
        return result

    def _extract_leadership(self, soup, structured):
        if structured.get("person_name"):
            return {
                "name": structured.get("person_name", ""),
                "title": structured.get("person_title", ""),
            }
        text_blocks = []
        for tag in soup.find_all(["h1", "h2", "h3", "h4", "p", "li", "span", "div"]):
            content = tag.get_text(" ", strip=True)
            if content and len(content) < 180:
                text_blocks.append(content)
        for block in text_blocks:
            lower = block.lower()
            if any(keyword in lower for keyword in LEADERSHIP_KEYWORDS):
                match = re.search(
                    r"([A-Z][a-z]+(?:\s+[A-Z][a-z\.]+){0,3})\s*[-,–|]?\s*(CEO|Chief Executive Officer|Founder|Co-Founder|President|Managing Director)",
                    block,
                )
                if match:
                    return {"name": match.group(1).strip(), "title": match.group(2).strip()}
        return {"name": "", "title": ""}

    def _find_linkedin_link(self, soup):
        for anchor in soup.find_all("a", href=True):
            href = anchor["href"]
            if "linkedin.com/company" in href.lower():
                return href.split("?")[0]
        return ""

    def _clean_title(self, title):
        if not title:
            return ""
        cleaned = re.split(r"[\|\-–—:]", title)[0].strip()
        return cleaned[:120]
