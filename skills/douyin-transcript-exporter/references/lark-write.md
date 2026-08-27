# 飞书多维表格写入

仅在用户提供飞书 wiki/base 链接时读取本页。所有写入使用 `--as user`，不要打印访问令牌或完整认证响应。

## 连接与权限

1. 查找系统 `lark-cli`，确认版本为 1.0.88 或更高。
2. 运行身份检查：

   ```bash
   lark-cli api GET /open-apis/authen/v1/user_info --as user
   ```

3. 解析目标链接：

   ```bash
   lark-cli base +url-resolve --url "<表格URL>" --as user
   ```

保存返回的 `base_token`、`table_id` 和可选 `view_id`。无权限时停止写入，告知用户当前身份并请其授权；不要尝试切换到未知测试账号。

## 字段映射

先读取字段：

```bash
lark-cli base +field-list --base-token <token> --table-id <id> --as user
```

| 内部字段 | 默认飞书字段 | 类型与值 |
|---|---|---|
| `author_name` | 账号名称 | 单选，`["名称"]` |
| `title` | 标题 | text |
| `description` | 介绍 | text |
| `transcript` | 逐字稿 | text |
| `likes` | 点赞 | number 或空值 |
| `comments` | 评论 | number 或空值 |
| `shares` | 转发 | number 或空值 |
| `publish_date` | 发表日期 | datetime，`YYYY-MM-DD HH:MM` 或毫秒时间戳 |
| `url` | 视频链接 | text |
| `topics` | 选题方向 | 多选，字符串数组 |
| `summary` | 主题总结 | text |

`video_id` 是内部稳定主键。目标表没有“视频ID”字段时，仍从“视频链接”中提取 ID 做去重；用户允许添加辅助字段时，可创建 text 类型的“视频ID”。`transcript_status` 和 `failure_reason` 默认保留在本地检查点；目标表已有对应字段时再写入。

缺少基础字段时，先向用户说明将添加哪些字段，再创建。不要自动删除字段、改变已有字段类型或重命名含数据的主字段。AI 扩展字段不存在时默认跳过；只有用户明确要求才创建。

主字段不能删除。确需把空白默认主字段改为“标题”时，先确认该列为空并获得用户同意，再用完整字段定义更新。

## 增量去重

读取现有记录的全部分页，不要只读取默认第一页：

```bash
lark-cli base +record-list --base-token <token> --table-id <id> --limit 500 --as user
```

从“视频ID”或“视频链接”提取 `video_id`，与本批规范化记录比较。默认行为：

- 已存在：跳过并计数。
- 不存在：加入待创建列表。
- 用户明确要求更新：仅更新用户指定字段，保留其他字段。

“重新导入”“覆盖”可能涉及删除旧记录。列出将删除的账号范围和记录数并再次确认后才能执行；“全量”仅表示采集范围，不自动授权删除或重复追加。

## 批量写入

长逐字稿先写入 UTF-8 JSON 文件，再用相对路径传给 CLI，避免 shell 转义和命令长度问题：

```bash
lark-cli base +record-batch-create --base-token <token> --table-id <id> \
  --json @./records.json --as user
```

- 每批最多 200 条，串行提交。
- 保存每批返回的 record ID，便于验证和精确重试。
- 遇到并发冲突时等待后重试该批，最多两次；不要重新提交已成功批次。
- 数值未知时省略字段或按目标字段支持的空值写入，不能把未知写成 0。

## 写后验证

读取本次创建或更新的全部记录，并依据 [data-contract.md](data-contract.md) 检查：

1. 返回记录数与成功 ID 数一致。
2. `video_id` 唯一且与视频链接一致。
3. 标题、账号、发布时间和视频链接存在。
4. 互动数字段为 number 或空值。
5. 逐字稿正文、状态和失败原因一致，正文不含明确占位短语。
6. “选题方向”只使用目标字段已有选项。

只重试失败记录。验证结束后报告新增、更新、重复跳过、失败和修复数量。

## 常见错误

| 错误/现象 | 处理 |
|---|---|
| 131006 / 91403 无权限 | 请用户授权当前身份或切换正确账号 |
| 1254015 类型不匹配 | 按 `field-list` 返回的真实类型修正 CellValue |
| 1254045 字段不存在 | 刷新字段列表，不凭名称猜测 |
| 1254104 超过批量上限 | 拆为每批不超过 200 条 |
| 1254291 并发冲突 | 串行等待后只重试失败批次 |
| 主字段不能删除 | 保留主字段；满足安全条件时经确认后重命名 |
