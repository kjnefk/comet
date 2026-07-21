import unittest

from RTN import (
    DefaultRanking,
    SettingsModel,
    Torrent,
    check_fetch,
    get_rank,
    parse,
    sort_torrents,
)

from comet.services.ranking import rank_worker


class RankWorkerTests(unittest.TestCase):
    def test_combined_worker_matches_individual_rtn_calls(self):
        titles = [
            "Oppenheimer.2023.2160p.REMUX.DV.HDR10Plus.TrueHD.7.1.HEVC",
            "The.Walking.Dead.S05E03.720p.WEB-DL.x264-ASAP",
            "Some.Movie.2020.CAM.XVID.MP3",
        ]
        torrents = {
            f"{index:040x}": {
                "title": title,
                "parsed": parse(title),
                "size": index * 1_000_000,
            }
            for index, title in enumerate(titles, 1)
        }
        settings = SettingsModel()
        ranking = DefaultRanking()

        expected = set()
        for info_hash, torrent in torrents.items():
            fetchable, _ = check_fetch(torrent["parsed"], settings)
            rank = get_rank(torrent["parsed"], settings, ranking)
            if not fetchable or rank < settings.options["remove_ranks_under"]:
                continue
            expected.add(
                Torrent(
                    infohash=info_hash,
                    raw_title=torrent["title"],
                    data=torrent["parsed"],
                    fetch=fetchable,
                    rank=rank,
                    lev_ratio=0.0,
                )
            )

        actual = rank_worker(torrents, settings, ranking, 50, 0, True)

        self.assertEqual(actual, sort_torrents(expected, 50))


if __name__ == "__main__":
    unittest.main()
