"""Proactive job discovery engine for automated remote job searching."""

import logging
import urllib.parse
from dataclasses import dataclass
from typing import List
import requests
from bs4 import BeautifulSoup

from ingestion.extractor import DEFAULT_HEADERS

logger = logging.getLogger("ai_job_hunter.discovery")


@dataclass
class DiscoveredJob:
    title: str
    company: str
    url: str
    location: str
    source: str


def search_public_remote_jobs(
    keywords: str = "AI Engineer Cloud Automation Google Workspace",
    limit: int = 5,
) -> List[DiscoveredJob]:
    """
    Search for recent public remote job postings using open API/web feeds
    without requiring authenticated LinkedIn credentials.
    Supports Remotive and public job boards with remote filter.
    """
    discovered: List[DiscoveredJob] = []

    # 1. LinkedIn Public Guest Search (España + 100% Remoto - Prioridad principal)
    try:
        encoded_kw = urllib.parse.quote(keywords)
        # f_WT=2 specifies 100% remote in LinkedIn search parameters
        linkedin_search_url = (
            f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?"
            f"keywords={encoded_kw}&location=Spain&f_WT=2&start=0"
        )
        resp = requests.get(linkedin_search_url, headers=DEFAULT_HEADERS, timeout=12)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            job_cards = soup.select("li")
            for card in job_cards[:limit]:
                title_elem = card.select_one("h3.base-search-card__title")
                company_elem = card.select_one("h4.base-search-card__subtitle")
                link_elem = card.select_one("a.base-card__full-link")

                if title_elem and link_elem:
                    job_url = link_elem.get("href", "").split("?")[0]
                    company_name = company_elem.get_text(strip=True) if company_elem else "Desconocida"
                    title = title_elem.get_text(strip=True)

                    discovered.append(
                        DiscoveredJob(
                            title=title,
                            company=company_name,
                            url=job_url,
                            location="Remoto (España)",
                            source="LinkedIn España",
                        )
                    )
    except Exception as exc:
        logger.debug("Error buscando en endpoint público de LinkedIn: %s", exc)

    # 2. Remotive Open API (Suplementario / Internacional tech si faltan resultados)
    if len(discovered) < limit:
        remaining = limit - len(discovered)
        try:
            query = urllib.parse.quote(keywords.split()[0] if keywords else "AI")
            api_url = f"https://remotive.com/api/remote-jobs?search={query}&limit={remaining * 2}"
            resp = requests.get(api_url, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                jobs = data.get("jobs", [])
                for item in jobs[:remaining]:
                    discovered.append(
                        DiscoveredJob(
                            title=item.get("title", ""),
                            company=item.get("company_name", ""),
                            url=item.get("url", ""),
                            location=item.get("candidate_required_location", "Worldwide / Remote"),
                            source="Remotive Internacional",
                        )
                    )
        except Exception as exc:
            logger.debug("Error buscando en feed de Remotive: %s", exc)

    return discovered
