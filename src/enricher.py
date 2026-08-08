from src.clearbit_client import ClearbitClient
from src.domain_utils import normalize_domain, normalize_name, parse_input_row
from src.web_scraper import WebScraper


OUTPUT_FIELDS = [
    "input-company-name",
    "input-company-domain",
    "company-name",
    "company-domain",
    "company-linkedin-url",
    "company-industry",
    "company-headcount",
    "company-headquarters",
    "company-description",
    "ceo-founder-name",
    "ceo-founder-title",
    "match-confidence",
    "enrichment-source",
]


class CompanyEnricher:
    def __init__(self, session):
        self.clearbit = ClearbitClient(session)
        self.scraper = WebScraper(session)

    def enrich_row(self, raw_name, raw_domain):
        input_name = normalize_name(raw_name)
        input_domain = normalize_domain(raw_domain)
        parsed_name, parsed_domain = parse_input_row(raw_name, raw_domain)
        result = {
            "input-company-name": input_name,
            "input-company-domain": input_domain,
            "company-name": parsed_name,
            "company-domain": parsed_domain,
            "company-linkedin-url": "",
            "company-industry": "",
            "company-headcount": "",
            "company-headquarters": "",
            "company-description": "",
            "ceo-founder-name": "",
            "ceo-founder-title": "",
            "match-confidence": "low",
            "enrichment-source": "",
        }
        sources = []
        clearbit_match = self.clearbit.best_match(parsed_name, parsed_domain)
        if clearbit_match:
            result["company-name"] = clearbit_match.get("name") or result["company-name"]
            result["company-domain"] = clearbit_match.get("domain") or result["company-domain"]
            sources.append("clearbit")
            result["match-confidence"] = "medium"
        domain_for_scrape = result["company-domain"] or parsed_domain
        site_data = self.scraper.fetch_site_data(domain_for_scrape)
        if site_data:
            if site_data.get("company_name"):
                result["company-name"] = site_data["company_name"]
            if site_data.get("description"):
                result["company-description"] = site_data["description"]
            if site_data.get("linkedin_url"):
                result["company-linkedin-url"] = site_data["linkedin_url"]
            if site_data.get("industry"):
                result["company-industry"] = site_data["industry"]
            if site_data.get("headquarters"):
                result["company-headquarters"] = site_data["headquarters"]
            if site_data.get("ceo_founder_name"):
                result["ceo-founder-name"] = site_data["ceo_founder_name"]
                result["ceo-founder-title"] = site_data.get("ceo_founder_title", "")
            sources.append("website")
        if not result["company-linkedin-url"] and result["company-name"]:
            slug = self._linkedin_slug(result["company-name"])
            if slug:
                result["company-linkedin-url"] = f"https://www.linkedin.com/company/{slug}"
                sources.append("linkedin-heuristic")
        result["match-confidence"] = self._score_confidence(
            input_name,
            input_domain,
            result["company-name"],
            result["company-domain"],
            clearbit_match,
            site_data,
        )
        result["enrichment-source"] = "+".join(dict.fromkeys(sources))
        return result

    def _linkedin_slug(self, company_name):
        slug = company_name.lower()
        slug = slug.replace("&", "and")
        for token in (",", ".", "'", '"', "(", ")", "!", "?", ":", ";"):
            slug = slug.replace(token, "")
        slug = "-".join(part for part in slug.split() if part)
        slug = slug.replace("--", "-").strip("-")
        return slug[:80]

    def _score_confidence(self, input_name, input_domain, out_name, out_domain, clearbit_match, site_data):
        score = 0
        if clearbit_match:
            score += 2
        if site_data:
            score += 2
        if input_domain and out_domain and normalize_domain(input_domain) == normalize_domain(out_domain):
            score += 2
        if input_name and out_name and input_name.lower() in out_name.lower():
            score += 1
        if input_name and out_name and out_name.lower() in input_name.lower():
            score += 1
        if score >= 5:
            return "high"
        if score >= 3:
            return "medium"
        return "low"
