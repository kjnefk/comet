from datetime import date

import aiohttp

from comet.core.logger import logger
from comet.core.models import settings

DEFAULT_TMDB_READ_ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJlNTkxMmVmOWFhM2IxNzg2Zjk3ZTE1NWY1YmQ3ZjY1MSIsInN1YiI6IjY1M2NjNWUyZTg5NGE2MDBmZjE2N2FmYyIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.xrIXsMFJpI1o1j5g2QpQcFP1X3AfRjFA5FlBFO5Naw8"


def _extract_upcoming_release_date(payload) -> str | None:
    if not isinstance(payload, dict):
        return None

    release_dates = []
    results = payload.get("results")
    if not isinstance(results, list):
        return None
    for result in results:
        if not isinstance(result, dict):
            continue
        releases = result.get("release_dates")
        if not isinstance(releases, list):
            continue
        for release in releases:
            if not isinstance(release, dict) or release.get("type") not in (4, 5):
                continue
            raw_date = release.get("release_date")
            if not isinstance(raw_date, str):
                continue
            date_text = raw_date.split("T", 1)[0]
            try:
                date.fromisoformat(date_text)
            except ValueError:
                continue
            release_dates.append(date_text)

    return min(release_dates) if release_dates else None


def _extract_tmdb_id(payload) -> str | None:
    if not isinstance(payload, dict):
        return None

    for result_key in ("movie_results", "tv_results"):
        results = payload.get(result_key)
        if not isinstance(results, list):
            continue
        for result in results:
            if not isinstance(result, dict):
                continue
            result_id = result.get("id")
            if isinstance(result_id, bool) or not isinstance(result_id, int):
                continue
            if result_id > 0:
                return str(result_id)
    return None


class TMDBApi:
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.base_url = "https://api.themoviedb.org/3"
        self.headers = {
            "Authorization": f"Bearer {settings.TMDB_READ_ACCESS_TOKEN if settings.TMDB_READ_ACCESS_TOKEN else DEFAULT_TMDB_READ_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }

    async def get_upcoming_movie_release_date(self, tmdb_id: str):
        try:
            url = f"{self.base_url}/movie/{tmdb_id}/release_dates"
            async with self.session.get(url, headers=self.headers) as response:
                if response.status != 200:
                    return None

                data = await response.json()

            return _extract_upcoming_release_date(data)
        except Exception as e:
            logger.error(f"TMDB: Error getting movie release date for {tmdb_id}: {e}")
            return None

    async def get_episode_air_date(self, tmdb_id: str, season: int, episode: int):
        try:
            url = f"{self.base_url}/tv/{tmdb_id}/season/{season}/episode/{episode}"
            async with self.session.get(url, headers=self.headers) as response:
                if response.status != 200:
                    return None

                data = await response.json()
                return data.get("air_date")
        except Exception as e:
            logger.error(
                f"TMDB: Error getting episode air date for {tmdb_id} S{season}E{episode}: {e}"
            )
            return None

    async def get_tmdb_id_from_imdb(self, imdb_id: str):
        try:
            url = f"{self.base_url}/find/{imdb_id}?external_source=imdb_id"
            async with self.session.get(url, headers=self.headers) as response:
                if response.status != 200:
                    text = await response.text()
                    logger.error(
                        f"TMDB: Failed to get TMDB ID from IMDB ID {imdb_id}: {text}"
                    )
                    return None

                data = await response.json()

            return _extract_tmdb_id(data)
        except Exception as e:
            logger.error(f"TMDB: Error converting IMDB ID {imdb_id}: {e}")
            return None

    async def has_watch_providers(self, tmdb_id: str):
        try:
            url = f"{self.base_url}/movie/{tmdb_id}/watch/providers"
            async with self.session.get(url, headers=self.headers) as response:
                if response.status != 200:
                    return None

                data = await response.json()
                return bool(data.get("results"))
        except Exception as e:
            logger.error(f"TMDB: Error getting watch providers for {tmdb_id}: {e}")
            return None
