import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "skills" / "douyin-transcript-exporter" / "scripts" / "export_local.py"
SPEC = importlib.util.spec_from_file_location("export_local", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


def sample(**overrides):
    record = {
        "视频链接": "https://www.douyin.com/video/7655189977860862854?previous_page=app_code_link",
        "账号名称": "测试账号",
        "标题": "一个足够明确的测试标题",
        "介绍": "介绍",
        "逐字稿": "这是完整逐字稿正文，里面可以正常出现获取这个词，而且不会被误判为占位内容。",
        "transcript_status": "complete",
        "点赞": "1.6万",
        "评论": "2,301",
        "转发": 42,
        "发表日期": "2026-08-27 10:30",
        "选题方向": ["AI工具"],
        "主题总结": "通过一个可复现的案例说明数据规范化与质量校验如何减少批量导出中的隐性错误。",
    }
    record.update(overrides)
    return record


class ExportLocalTests(unittest.TestCase):
    def test_normalizes_url_counts_and_chinese_aliases(self):
        record = MODULE.normalize(sample())
        self.assertEqual(record["video_id"], "7655189977860862854")
        self.assertEqual(record["url"], "https://www.douyin.com/video/7655189977860862854")
        self.assertEqual(record["likes"], 16000)
        self.assertEqual(record["comments"], 2301)
        self.assertEqual(MODULE.validate(record), [])

    def test_requires_reason_for_failed_transcript(self):
        record = MODULE.normalize(sample(逐字稿="", transcript_status="failed", failure_reason=""))
        self.assertIn("failed 状态必须填写 failure_reason", MODULE.validate(record))

    def test_rejects_specific_placeholder_but_not_common_word(self):
        good = MODULE.normalize(sample())
        bad = MODULE.normalize(sample(逐字稿="完整内容已通过web.fetch获取"))
        self.assertFalse(any("占位" in error for error in MODULE.validate(good)))
        self.assertTrue(any("占位" in error for error in MODULE.validate(bad)))

    def test_deduplicates_by_video_id(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "input.json"
            duplicate = sample(url="https://www.douyin.com/video/7655189977860862854")
            path.write_text(json.dumps([sample(), duplicate], ensure_ascii=False), encoding="utf-8")
            records, warnings = MODULE.load_records(path)
            self.assertEqual(len(records), 1)
            self.assertEqual(len(warnings), 1)

    def test_export_never_overwrites_existing_batch(self):
        with tempfile.TemporaryDirectory() as temp:
            record = MODULE.normalize(sample())
            first = MODULE.export([record], Path(temp), "20260827")
            second = MODULE.export([record], Path(temp), "20260827")
            self.assertNotEqual(first, second)
            self.assertTrue((first / "_all.json").exists())
            self.assertTrue((second / "_all.json").exists())


if __name__ == "__main__":
    unittest.main()
