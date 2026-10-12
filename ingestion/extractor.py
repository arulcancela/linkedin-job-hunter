"""Web extractor for LinkedIn and generic job postings."""

import re
import urllib.parse

import requests
from bs4 import BeautifulSoup

# Browser-like headers to minimize anti-scraping blocks on guest view endpoints
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Linux"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


class ExtractionError(Exception):
    """Raised when URL extraction fails or gets blocked by anti-bot defenses."""

    def __init__(self, message: str, url: str, status_code: int | None = None):
        super().__init__(message)
        self.url = url
        self.status_code = status_code


def _clean_linkedin_url(url: str) -> str:
    """Normalize LinkedIn job URL removing tracking parameters."""
    parsed = urllib.parse.urlparse(url)
    # Match patterns like /jobs/view/123456789/
    match = re.search(r"/jobs/view/(\d+)", parsed.path)
    if match:
        job_id = match.group(1)
        return f"https://www.linkedin.com/jobs/view/{job_id}/"
    return url


def _extract_linkedin_job_content(html: str) -> str | None:
    """Parse LinkedIn HTML to extract job details."""
    soup = BeautifulSoup(html, "html.parser")

    # Common LinkedIn guest job description containers
    selectors = [
        "div.show-more-less-html__markup",
        "section.show-more-less-html",
        "div.description__text",
        "div.decorated-job-posting__details",
        "main.main-content",
        "div.core-section-container",
    ]

    for selector in selectors:
        element = soup.select_one(selector)
        if element:
            text = element.get_text(separator="\n", strip=True)
            if len(text) > 150:
                # Also try to grab title and company if present
                title_elem = soup.select_one("h1.top-card-layout__title, h1.topcard__title")
                company_elem = soup.select_one(
                    "a.topcard__org-name-link, span.topcard__flavor, a.sub-nav-cta__optional-url"
                )
                header_info = ""
                if title_elem:
                    header_info += f"Puesto: {title_elem.get_text(strip=True)}\n"
                if company_elem:
                    header_info += f"Empresa: {company_elem.get_text(strip=True)}\n\n"

                return f"{header_info}{text}"

    return None


def _extract_generic_web_content(html: str) -> str:
    """Extract clean text content from generic job boards."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove script, style, nav, footer, ads
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "aside"]):
        tag.decompose()

    # Priority target: article or main tags
    main_content = soup.find("main") or soup.find("article") or soup.find("body")
    if main_content:
        text = main_content.get_text(separator="\n", strip=True)
    else:
        text = soup.get_text(separator="\n", strip=True)

    # Clean redundant blank lines
    cleaned_lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(cleaned_lines)


def extract_job_from_url(url: str, timeout: int = 15) -> tuple[str, str]:
    """
    Attempt to extract job description text from a URL.

    Returns:
        Tuple[str, str]: (cleaned_url, extracted_text)

    Raises:
        ExtractionError: If page cannot be reached, blocks with 429/999/auth, or yields insufficient text.
    """
    clean_url = _clean_linkedin_url(url)

    try:
        session = requests.Session()
        session.headers.update(DEFAULT_HEADERS)
        response = session.get(clean_url, timeout=timeout, allow_redirects=True)
    except requests.RequestException as exc:
        raise ExtractionError(
            f"Error de conexión al conectar con {clean_url}: {exc}",
            url=clean_url,
        ) from exc

    if response.status_code in (429, 999):
        raise ExtractionError(
            f"LinkedIn bloqueó la petición automática (HTTP {response.status_code}). "
            "Se requiere pasar el contenido mediante texto pegado (--paste).",
            url=clean_url,
            status_code=response.status_code,
        )

    if response.status_code != 200:
        raise ExtractionError(
            f"El servidor respondió con código HTTP {response.status_code}.",
            url=clean_url,
            status_code=response.status_code,
        )

    html_content = response.text

    # Check for authentication redirect wall
    if "linkedin.com/login" in response.url or "authwall" in response.url:
        raise ExtractionError(
            "LinkedIn redirigió al muro de autenticación (authwall). "
            "Usa el modo manual (--paste) para copiar el texto de la oferta.",
            url=clean_url,
            status_code=401,
        )

    extracted_text = None
    if "linkedin.com" in clean_url:
        extracted_text = _extract_linkedin_job_content(html_content)

    if not extracted_text:
        extracted_text = _extract_generic_web_content(html_content)

    # Validate extracted text length
    if not extracted_text or len(extracted_text.strip()) < 120:
        raise ExtractionError(
            "No se pudo extraer texto suficiente de la oferta en la URL especificada. "
            "Es posible que la página requiera JavaScript dinámico o sesión activa. "
            "Por favor, utiliza el modo interactivo (--paste).",
            url=clean_url,
        )

    return clean_url, extracted_text.strip()
