from comet.core.logger import logger
from comet.scrapers.base import BaseScraper
from comet.scrapers.models import ScrapeRequest


class ZileanScraper(BaseScraper):
    def __init__(self, manager, session, url: str):
        super().__init__(manager, session, url)

    @staticmethod
    def _parse_result(result):
        if not isinstance(result, dict):
            return None
        title = result.get("raw_title")
        info_hash = result.get("info_hash")
        if not isinstance(title, str) or not title:
            return None
        if not isinstance(info_hash, str) or not info_hash:
            return None
        try:
            size = int(result["size"])
        except (KeyError, TypeError, ValueError):
            return None
        return {
            "title": title,
            "infoHash": info_hash.lower(),
            "fileIndex": None,
            "seeders": None,
            "size": size,
            "tracker": "DMM",
            "sources": [],
        }

    async def scrape(self, request: ScrapeRequest):
        torrents = []
        try:
            show = (
                f"&season={request.season}&episode={request.episode}"
                if request.media_type == "series"
                else ""
            )
            async with self.session.get(
                f"{self.url}/dmm/filtered?query={request.title}{show}"
            ) as response:
                data = await response.json()

            if not isinstance(data, list):
                return []

            for result in data:
                parsed = self._parse_result(result)
                if parsed is not None:
                    torrents.append(parsed)
        except Exception as e:
            logger.warning(
                f"Exception while getting torrents for {request.title} with Zilean ({self.url}): {e}"
            )

        return torrents
