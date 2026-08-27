# 数据契约与质量门槛

采集、去重、飞书写入和本地导出都使用同一份记录模型。

## 记录字段

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `video_id` | string | 是 | 抖音视频数字 ID，批内唯一 |
| `url` | string | 是 | 标准链接 `https://www.douyin.com/video/<video_id>` |
| `author_name` | string | 是 | 账号名称 |
| `title` | string | 是 | 视频标题 |
| `description` | string | 否 | 页面介绍/文案；页面确实没有时可为空 |
| `transcript` | string | 条件必填 | `transcript_status=complete` 时必须为真实正文 |
| `transcript_status` | enum | 是 | `complete`、`not_requested`、`no_speech` 或 `failed` |
| `failure_reason` | string | 条件必填 | 逐字稿失败或采集不完整时的简短原因 |
| `likes` | integer/null | 是 | 无法可靠读取时为 `null`，不可猜为 0 |
| `comments` | integer/null | 是 | 同上 |
| `shares` | integer/null | 是 | 同上 |
| `publish_date` | string | 是 | `YYYY-MM-DD HH:MM`，页面无时区则保留平台展示时间 |
| `topics` | string[] | 否 | 1–3 个选题标签 |
| `summary` | string | 否 | 30–80 个汉字的一句话总结 |

输入 JSON 可以使用以下中文别名：`账号名称`、`标题`、`介绍`、`逐字稿`、`点赞`、`评论`、`转发`、`发表日期`、`选题方向`、`主题总结`。

## 逐字稿状态

- `complete`：正文已取得并通过检查。
- `not_requested`：用户明确不需要逐字稿。
- `no_speech`：确认视频没有可转写口播。
- `failed`：尝试过但未取得可靠正文，必须填写 `failure_reason`。

空正文不能标记为 `complete`。有正文不能标记为 `not_requested`、`no_speech` 或 `failed`。

明确的伪正文包括：`完整内容已通过web.fetch获取`、`内容已获取`、`获取完整内容`、`逐字稿已获取`。只匹配这些完整短语及明显变体；“获取”单独出现是正常词语。

## 规范化与去重

1. 从任意标准视频 URL 中提取数字 `video_id`，移除查询参数，生成标准 URL。
2. 同一批按 `video_id` 去重，而不是按原始 URL 字符串去重。
3. 互动数支持整数、千分位和中文单位：`1.6万 → 16000`、`2.3亿 → 230000000`。无法判断时为 `null`。
4. 重复记录默认保留首次出现的记录并报告后续重复项，不能静默覆盖。需要合并字段时先显式解决冲突，再重新验证。

## 质量门槛

导出或写入前全量检查：

- `video_id` 唯一，且与 `url` 中 ID 一致。
- 作者、标题、发布时间非空。
- 互动数为非负整数或 `null`。
- `transcript_status` 与正文、失败原因一致，正文不含明确占位短语。
- 有 `topics` 时数量为 1–3，值非空且不重复。
- 有 `summary` 时长度为 30–80 个汉字或字符。

失败项不伪装成成功项。可以导出带 `failed` 状态的记录以便续跑，但结构错误、主键冲突或伪正文必须阻止写入。
