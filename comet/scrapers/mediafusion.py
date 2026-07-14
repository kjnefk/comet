import logging
from comet.core.logger import log_scraper_error
from comet.scrapers.base import BaseScraper
from comet.scrapers.helpers.mediafusion import mediafusion_config
from comet.scrapers.models import ScrapeRequest

# Setup logger for the module
logger = logging.getLogger(__name__)

class MediaFusionScraper(BaseScraper):
    def __init__(
        self,
        manager,
        session,
        url: str,
        password: str | None = None,
    ):
        super().__init__(manager, session, url)
        self.password = password

    async def scrape(self, request: ScrapeRequest):
        torrents = []
        try:
            headers = mediafusion_config.get_headers_for_password(self.password)

            async with self.session.get(
                f"{self.url}/stream/{request.media_type}/{request.media_id}.json",
                headers=headers,
            ) as response:
                results = await response.json()

            streams = results.get("streams", [])
            if not streams:
                return []

            for torrent in streams:
                try:
                    title_full = torrent.get("description", "Unknown Title")
                    lines = title_full.split("\n")

                    title = lines[0].replace("📂 ", "").replace("/", "")

                    seeders = None
                    if len(lines) > 1 and "👤" in lines[1]:
                        try:
                            seeders = int(lines[1].split("👤 ")[1].split("\n")[0])
                        except (ValueError, IndexError):
                            seeders = None

                    tracker = "Unknown"
                    if len(lines) > 0 and "🔗" in lines[-1]:
                        tracker = lines[-1].split("🔗 ")[1]

                    torrents.append(
                        {
                            "title": title,
                            "infoHash": torrent.get("infoHash", "").lower(),
                            "fileIndex": torrent.get("fileIdx"),
                            "seeders": seeders,
                            "size": torrent.get("behaviorHints", {}).get("videoSize"),
                            "tracker": f"MediaFusion|{tracker}",
                            "sources": torrent.get("sources", []),
                        }
                    )
                except Exception as e:
                    # Log the specific stream failure so you can debug API changes
                    logger.warning(
                        f"MediaFusion: Failed to parse a stream for {request.media_id}. "
                        f"Error: {e}. Stream data: {torrent}"
                    )
                    continue
                    
        except Exception as e:
            log_scraper_error("MediaFusion", self.url, request.media_id, e)

        return torrents