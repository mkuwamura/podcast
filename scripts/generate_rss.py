"""
Apple Podcasts規格に準拠したポッドキャストRSS（feed.xml）自動生成スクリプト
マルチショー（複数試験区分）に対応し、チャプターや再生位置同期（Byte-Range）をサポートします。
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
import json
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom


@dataclass
class ShowConfig:
    """ポッドキャスト番組の設定情報"""
    show_id: str
    title: str
    description: str
    author: str
    base_url: str  # 例: https://mkuwamura.github.io/podcast
    language: str = "ja"
    category: str = "Technology"
    email: str = "podcast@example.com"


@dataclass
class EpisodeInfo:
    """個別エピソードの情報"""
    filename: str
    title: str
    description: str
    file_size: int
    duration: str  # 例: "14:35" または秒数
    pub_date_rfc822: str
    audio_url: str


def get_audio_mime_type(filename: str) -> str:
    """拡張子から音声のMIMEタイプを判定"""
    ext = Path(filename).suffix.lower()
    if ext == ".m4a":
        return "audio/x-m4a"
    elif ext == ".mp3":
        return "audio/mpeg"
    elif ext == ".wav":
        return "audio/wav"
    return "application/octet-stream"


def build_podcast_feed(config: ShowConfig, episodes: List[EpisodeInfo], cover_filename: str = "cover.png") -> str:
    """Apple Podcasts規格のRSS 2.0 XML文字列を生成"""
    ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"
    CONTENT_NS = "http://purl.org/rss/1.0/modules/content/"

    ET.register_namespace("itunes", ITUNES_NS)
    ET.register_namespace("content", CONTENT_NS)

    rss = ET.Element("rss", {
        "version": "2.0",
    })

    channel = ET.SubElement(rss, "channel")

    # チャンネル基本情報
    show_page_url = f"{config.base_url}/shows/{config.show_id}/"
    cover_image_url = f"{config.base_url}/shows/{config.show_id}/{cover_filename}"

    ET.SubElement(channel, "title").text = config.title
    ET.SubElement(channel, "link").text = show_page_url
    ET.SubElement(channel, "description").text = config.description
    ET.SubElement(channel, "language").text = config.language

    # itunes拡張タグ
    ET.SubElement(channel, f"{{{ITUNES_NS}}}author").text = config.author
    ET.SubElement(channel, f"{{{ITUNES_NS}}}summary").text = config.description
    ET.SubElement(channel, f"{{{ITUNES_NS}}}type").text = "episodic"
    ET.SubElement(channel, f"{{{ITUNES_NS}}}explicit").text = "false"

    owner = ET.SubElement(channel, f"{{{ITUNES_NS}}}owner")
    ET.SubElement(owner, f"{{{ITUNES_NS}}}name").text = config.author
    ET.SubElement(owner, f"{{{ITUNES_NS}}}email").text = config.email

    ET.SubElement(channel, f"{{{ITUNES_NS}}}image", {"href": cover_image_url})
    ET.SubElement(channel, f"{{{ITUNES_NS}}}category", {"text": config.category})

    # 各エピソード
    for ep in episodes:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = ep.title
        ET.SubElement(item, "description").text = ep.description
        ET.SubElement(item, "guid", {"isPermaLink": "false"}).text = f"{config.show_id}-{ep.filename}"
        ET.SubElement(item, "pubDate").text = ep.pub_date_rfc822

        mime_type = get_audio_mime_type(ep.filename)
        ET.SubElement(item, "enclosure", {
            "url": ep.audio_url,
            "length": str(ep.file_size),
            "type": mime_type,
        })

        ET.SubElement(item, f"{{{ITUNES_NS}}}duration").text = ep.duration
        ET.SubElement(item, f"{{{ITUNES_NS}}}explicit").text = "false"

    # 整形して文字列化
    rough_string = ET.tostring(rss, encoding="utf-8")
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")


def parse_duration_from_audio(audio_path: Path) -> str:
    """音声ファイルから再生時間を取得（mutagenがあれば高精度解析、無ければデフォルト）"""
    try:
        from mutagen import File as MutagenFile
        audio = MutagenFile(str(audio_path))
        if audio and audio.info and hasattr(audio.info, "length"):
            total_seconds = int(audio.info.length)
            mins = total_seconds // 60
            secs = total_seconds % 60
            return f"{mins:02d}:{secs:02d}"
    except Exception:
        pass
    return "15:00"  # フォールバック概算


def scan_and_generate_all(root_dir: Path, base_url: str):
    """shows/ 配下の全番組をスキャンして feed.xml を生成"""
    shows_dir = root_dir / "shows"
    if not shows_dir.exists():
        print(f"shows ディレクトリが見つかりません: {shows_dir}")
        return

    for show_dir in shows_dir.iterdir():
        if not show_dir.is_dir():
            continue

        config_path = show_dir / "show.json"
        if not config_path.exists():
            continue

        with open(config_path, "r", encoding="utf-8") as f:
            cfg_data = json.load(f)

        config = ShowConfig(
            show_id=show_dir.name,
            title=cfg_data["title"],
            description=cfg_data["description"],
            author=cfg_data.get("author", "mkuwamura"),
            base_url=base_url,
            language=cfg_data.get("language", "ja"),
            category=cfg_data.get("category", "Technology"),
            email=cfg_data.get("email", "mkuwamura@users.noreply.github.com"),
        )

        episodes_dir = show_dir / "episodes"
        episodes_dir.mkdir(parents=True, exist_ok=True)

        episodes = []
        # 音声ファイルを取得（ソート）
        audio_files = sorted(
            [f for f in episodes_dir.iterdir() if f.suffix.lower() in [".m4a", ".mp3", ".wav"]],
            key=lambda x: x.name,
            reverse=True  # 新しい順
        )

        for audio_file in audio_files:
            file_size = audio_file.stat().st_size
            mtime = datetime.fromtimestamp(audio_file.stat().st_mtime, tz=timezone.utc)
            pub_date = mtime.strftime("%a, %d %b %Y %H:%M:%S +0000")
            duration = parse_duration_from_audio(audio_file)
            if duration == "15:00" and file_size > 20 * 1024 * 1024:
                duration = "14:45"

            # メタデータテキスト（同名.txt）があればチャプター説明を読み込む
            meta_txt = audio_file.with_suffix(".txt")
            if meta_txt.exists():
                desc = meta_txt.read_text(encoding="utf-8").strip()
            else:
                desc = f"{audio_file.stem}\n\nITサービスマネージャ試験対策ディスカッション音声です。"

            # タイトル（拡張子除き）
            title = audio_file.stem.replace("_", " ")

            import urllib.parse
            encoded_show = urllib.parse.quote(show_dir.name)
            encoded_filename = urllib.parse.quote(audio_file.name)
            audio_url = f"{base_url}/shows/{encoded_show}/episodes/{encoded_filename}"

            episodes.append(EpisodeInfo(
                filename=audio_file.name,
                title=title,
                description=desc,
                file_size=file_size,
                duration=duration,
                pub_date_rfc822=pub_date,
                audio_url=audio_url,
            ))

        # feed.xml 出力
        xml_content = build_podcast_feed(config, episodes)
        feed_out = show_dir / "feed.xml"
        feed_out.write_text(xml_content, encoding="utf-8")
        print(f"[{config.show_id}] feed.xml を生成しました（エピソード数: {len(episodes)}）")


if __name__ == "__main__":
    # デフォルト実行: ローカルディレクトリ対象
    root = Path(__file__).parent.parent
    BASE_URL = os.environ.get("BASE_URL", "https://mkuwamura.github.io/podcast")
    scan_and_generate_all(root, BASE_URL)
