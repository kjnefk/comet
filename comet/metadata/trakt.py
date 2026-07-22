import aiohttp


def _extract_aliases(payload) -> dict[str, list[str]]:
    if not isinstance(payload, list):
        return {}

    aliases: dict[str, list[str]] = {}
    seen: dict[str, set[str]] = {}
    for entry in payload:
        if not isinstance(entry, dict):
            continue

        title = entry.get("title")
        country = entry.get("country")
        if not isinstance(title, str) or not title:
            continue

        key = country if isinstance(country, str) and country else "ez"
        country_seen = seen.setdefault(key, set())
        if title in country_seen:
            continue
        country_seen.add(title)
        aliases.setdefault(key, []).append(title)

    return aliases


async def get_trakt_aliases(
    session: aiohttp.ClientSession, media_type: str, media_id: str
):
    try:
        async with session.get(
            f"https://api.trakt.tv/{'movies' if media_type == 'movie' else 'shows'}/{media_id}/aliases",
            headers={"trakt-api-key": ""},
        ) as response:
            if response.status != 200:
                return {}
            data = await response.json()

        return _extract_aliases(data)
    except Exception:
        pass

    return {}
