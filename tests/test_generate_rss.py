import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
import tempfile
import json
import shutil
import sys

# scripts ディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from generate_rss import build_podcast_feed, ShowConfig, EpisodeInfo


class TestGenerateRSS(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.show_dir = self.test_dir / "shows" / "test_show"
        self.episodes_dir = self.show_dir / "episodes"
        self.episodes_dir.mkdir(parents=True)

        # ダミーのカバー画像と音声ファイルを作成
        self.cover_file = self.show_dir / "cover.png"
        self.cover_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        self.audio_file = self.episodes_dir / "01_test_episode.m4a"
        self.audio_file.write_bytes(b"\x00" * 1024)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_build_podcast_feed_structure(self):
        """Apple Podcasts準拠のRSS構造が正しく生成されるかを検証"""
        config = ShowConfig(
            show_id="test_show",
            title="テストポッドキャスト",
            description="テスト説明文",
            author="Test Author",
            base_url="https://mkuwamura.github.io/podcast",
            language="ja",
            category="Technology",
        )

        episode = EpisodeInfo(
            filename="01_test_episode.m4a",
            title="第1回 変更管理の基礎",
            description="00:00 イントロ\n02:00 本編ディスカッション\n05:00 まとめ",
            file_size=1024,
            duration="05:00",
            pub_date_rfc822="Sat, 31 Oct 2026 06:00:00 +0000",
            audio_url="https://mkuwamura.github.io/podcast/shows/test_show/episodes/01_test_episode.m4a",
        )

        xml_str = build_podcast_feed(config, [episode], cover_filename="cover.png")

        # XML構文解析チェック
        root = ET.fromstring(xml_str)
        self.assertEqual(root.tag, "rss")
        self.assertEqual(root.attrib.get("version"), "2.0")

        channel = root.find("channel")
        self.assertIsNotNone(channel)
        self.assertEqual(channel.find("title").text, "テストポッドキャスト")

        # itunes名前空間のタグチェック
        itunes_author = channel.find("{http://www.itunes.com/dtds/podcast-1.0.dtd}author")
        self.assertIsNotNone(itunes_author)
        self.assertEqual(itunes_author.text, "Test Author")

        # エピソードチェック
        items = channel.findall("item")
        self.assertEqual(len(items), 1)

        item = items[0]
        self.assertEqual(item.find("title").text, "第1回 変更管理の基礎")
        enclosure = item.find("enclosure")
        self.assertIsNotNone(enclosure)
        self.assertEqual(enclosure.attrib.get("type"), "audio/x-m4a")
        self.assertEqual(enclosure.attrib.get("length"), "1024")
        self.assertIn("01_test_episode.m4a", enclosure.attrib.get("url"))

        # チャプター記述チェック
        description = item.find("description")
        self.assertIn("00:00 イントロ", description.text)


if __name__ == "__main__":
    unittest.main()
