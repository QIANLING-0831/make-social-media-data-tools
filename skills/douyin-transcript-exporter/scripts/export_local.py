#!/usr/bin/env python3
"""Validate, normalize and export Douyin records using only the stdlib."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ALIASES = {
    "账号名称": "author_name", "标题": "title", "介绍": "description",
    "逐字稿": "transcript", "点赞": "likes", "评论": "comments",
    "转发": "shares", "发表日期": "publish_date", "选题方向": "topics",
    "主题总结": "summary", "视频链接": "url", "逐字稿状态": "transcript_status",
    "失败原因": "failure_reason",
}
PLACEHOLDERS = ("完整内容已通过web.fetch获取", "内容已获取", "获取完整内容", "逐字稿已获取")
STATUSES = {"complete", "not_requested", "no_speech", "failed"}
VIDEO_ID_RE = re.compile(r"(?:/video/)?(\d{8,})")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")


class DataError(ValueError):
    pass


def text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def parse_count(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise DataError("布尔值不是有效互动数")
    if isinstance(value, int):
        result = value
    elif isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            raise DataError(f"无法转换为整数: {value!r}")
        result = int(value)
    else:
        raw = text(value).replace(",", "").replace("，", "")
        match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([万亿]?)", raw)
        if not match:
            raise DataError(f"无法识别互动数: {value!r}")
        multiplier = {"": 1, "万": 10_000, "亿": 100_000_000}[match.group(2)]
        result = int(float(match.group(1)) * multiplier)
    if result < 0:
        raise DataError("互动数不能为负数")
    return result


def video_id_from(record: dict[str, Any]) -> str:
    candidates = (text(record.get("video_id")), text(record.get("url")))
    for candidate in candidates:
        match = VIDEO_ID_RE.search(candidate)
        if match:
            return match.group(1)
    raise DataError("缺少有效的 video_id 或视频 URL")


def normalize(raw: dict[str, Any]) -> dict[str, Any]:
    record = {ALIASES.get(key, key): value for key, value in raw.items()}
    video_id = video_id_from(record)
    transcript = text(record.get("transcript"))
    status = text(record.get("transcript_status"))
    if not status:
        status = "complete" if transcript else "failed"
    topics = record.get("topics", [])
    if isinstance(topics, str):
        topics = [item.strip() for item in re.split(r"[、,，]", topics) if item.strip()]
    elif topics is None:
        topics = []
    elif not isinstance(topics, list):
        raise DataError("topics 必须是数组或分隔字符串")

    return {
        "video_id": video_id,
        "url": f"https://www.douyin.com/video/{video_id}",
        "author_name": text(record.get("author_name")),
        "title": text(record.get("title")),
        "description": text(record.get("description")),
        "transcript": transcript,
        "transcript_status": status,
        "failure_reason": text(record.get("failure_reason")),
        "likes": parse_count(record.get("likes")),
        "comments": parse_count(record.get("comments")),
        "shares": parse_count(record.get("shares")),
        "publish_date": text(record.get("publish_date")),
        "topics": [text(item) for item in topics if text(item)],
        "summary": text(record.get("summary")),
    }


def validate(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in ("author_name", "title", "publish_date"):
        if not record[field]:
            errors.append(f"{field} 不能为空")
    if record["transcript_status"] not in STATUSES:
        errors.append(f"未知 transcript_status: {record['transcript_status']!r}")
    transcript = record["transcript"]
    if record["transcript_status"] == "complete" and not transcript:
        errors.append("complete 状态必须包含逐字稿正文")
    if record["transcript_status"] != "complete" and transcript:
        errors.append("非 complete 状态不能包含逐字稿正文")
    if record["transcript_status"] == "failed" and not record["failure_reason"]:
        errors.append("failed 状态必须填写 failure_reason")
    if any(phrase in transcript for phrase in PLACEHOLDERS):
        errors.append("逐字稿包含占位短语")
    if record["publish_date"] and not DATE_RE.fullmatch(record["publish_date"]):
        errors.append("publish_date 必须为 YYYY-MM-DD HH:MM")
    if len(record["topics"]) > 3 or len(set(record["topics"])) != len(record["topics"]):
        errors.append("topics 必须是 1–3 个不重复标签")
    if record["summary"] and not 30 <= len(record["summary"]) <= 80:
        errors.append("summary 长度必须为 30–80 个字符")
    return errors


def load_records(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(raw, list):
        raise DataError("输入 JSON 顶层必须是数组")
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    warnings: list[str] = []
    for index, item in enumerate(raw, 1):
        if not isinstance(item, dict):
            raise DataError(f"第 {index} 条记录不是对象")
        try:
            record = normalize(item)
        except DataError as exc:
            raise DataError(f"第 {index} 条记录: {exc}") from exc
        if record["video_id"] in seen:
            warnings.append(f"跳过重复 video_id {record['video_id']}（第 {index} 条）")
            continue
        seen.add(record["video_id"])
        problems = validate(record)
        if problems:
            raise DataError(f"video_id {record['video_id']}: " + "；".join(problems))
        records.append(record)
    if not records:
        raise DataError("没有可导出的记录")
    return records, warnings


def safe_name(value: str) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip(" ._")
    return value[:60] or "unknown"


def unique_batch_dir(root: Path, base_name: str) -> Path:
    candidate = root / base_name
    suffix = 2
    while candidate.exists():
        candidate = root / f"{base_name}_{suffix}"
        suffix += 1
    return candidate


def markdown(record: dict[str, Any]) -> str:
    topics = "、".join(record["topics"]) or "无"
    transcript = record["transcript"] or f"（{record['transcript_status']}：{record['failure_reason'] or '无正文'}）"
    count = lambda value: "未知" if value is None else str(value)
    return f"""# {record['title']}

## 基本信息

- **账号名称**：{record['author_name']}
- **发表日期**：{record['publish_date']}
- **视频链接**：{record['url']}
- **点赞**：{count(record['likes'])}
- **评论**：{count(record['comments'])}
- **转发**：{count(record['shares'])}
- **逐字稿状态**：{record['transcript_status']}

## 介绍/文案

{record['description'] or '无'}

## 选题方向

{topics}

## 主题总结

{record['summary'] or '无'}

## 逐字稿

{transcript}
"""


def export(records: list[dict[str, Any]], root: Path, date: str) -> Path:
    authors = {record["author_name"] for record in records}
    author = next(iter(authors)) if len(authors) == 1 else "多个账号"
    batch = unique_batch_dir(root, f"{safe_name(author)}_{date}_{len(records)}条")
    batch.mkdir(parents=True)
    width = max(2, len(str(len(records))))
    for index, record in enumerate(records, 1):
        (batch / f"{index:0{width}d}_{record['video_id']}.md").write_text(
            markdown(record), encoding="utf-8"
        )
    (batch / "_all.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return batch


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="UTF-8 JSON record array")
    parser.add_argument("--output-root", type=Path, default=Path("douyin_data"))
    parser.add_argument("--date", default=datetime.now().strftime("%Y%m%d"), help="YYYYMMDD")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    try:
        if not re.fullmatch(r"\d{8}", args.date):
            raise DataError("--date 必须为 YYYYMMDD")
        records, warnings = load_records(args.input)
        for warning in warnings:
            print(f"WARNING: {warning}", file=sys.stderr)
        print(f"验证通过：{len(records)} 条唯一记录")
        if not args.validate_only:
            batch = export(records, args.output_root, args.date)
            print(f"已导出：{batch.resolve()}")
        return 0
    except (DataError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
