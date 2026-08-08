import requests


class ClearbitClient:
    def __init__(self, session):
        self.session = session
        self.base_url = "https://autocomplete.clearbit.com/v1/companies/suggest"

    def suggest(self, query):
        if not query:
            return []
        try:
            response = self.session.get(
                self.base_url,
                params={"query": query},
                timeout=12,
            )
            if response.status_code != 200:
                return []
            data = response.json()
            if not isinstance(data, list):
                return []
            return data
        except requests.RequestException:
            return []

    def best_match(self, name, domain):
        candidates = []
        if domain:
            candidates.extend(self.suggest(domain))
        if name and name.lower() != domain.lower():
            candidates.extend(self.suggest(name))
        if not candidates:
            return None
        if domain:
            for item in candidates:
                item_domain = (item.get("domain") or "").lower()
                if item_domain == domain.lower():
                    return item
        return candidates[0]
