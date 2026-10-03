<p align="center"><img src=".github/readme/banner.svg" alt="Social Data Toolkit — 抖音逐字稿与结构化导出" width="100%"></p>

<h1 align="center">Social Data Toolkit · 抖音逐字稿与结构化导出</h1>

<p align="center">把公开视频信息与逐字稿整理为结构化数据，支持本地导出与飞书工作流。</p>

<p align="center"><img src="https://img.shields.io/badge/docs-%E4%B8%AD%E6%96%87-f472b6?style=flat-square&amp;labelColor=172033" alt="docs: 中文"> <img src="https://img.shields.io/badge/maintainer-QIANLING--0831-f472b6?style=flat-square&amp;labelColor=172033" alt="maintainer: QIANLING-0831"> </p>

<p align="center"><a href="#使用前提">使用前提</a> &nbsp; · &nbsp; <a href="#本地输出">本地输出</a> &nbsp; · &nbsp; <a href="#使用方式">使用方式</a> &nbsp; · &nbsp; <a href="#主要改进">主要改进</a></p>

---

## 项目概览

| 方向 | 内容 |
| --- | --- |
| **数据整理** | 稳定视频主键与标准化字段 |
| **状态清晰** | 区分成功、未请求、无口播与失败 |
| **本地输出** | 逐条 Markdown 与汇总 JSON |

用于整理、校验和导出社交媒体公开数据的 Skill 集合。本仓库基于
[jinchenma94/social-media-data-tools](https://github.com/jinchenma94/social-media-data-tools)
继续改进，并保留上游 Git 历史。

目前包含：

- `douyin-transcript-exporter`：导出抖音视频的标题、文案、互动数据与完整逐字稿；支持稳定主键去重、失败状态记录、断点续跑、飞书增量写入，以及经过校验的本地 Markdown/JSON 输出。

## 使用前提

`douyin-transcript-exporter` 必须在豆包工作中执行，因为逐字稿获取依赖豆包工作内置的相关能力。

采集抖音主页的公开视频信息时，Skill 会打开豆包工作内置浏览器，需要登录一个抖音账号。建议使用抖音小号：该账号仅用于读取公开主页的视频信息，不涉及视频下载；逐字稿获取也不依赖该账号。

请仅处理你有权访问和使用的内容，并遵守适用的平台规则与法律要求。

## 本地输出

选择本地输出时，结果会保存为：

```text
douyin_data/
└── {博主昵称}_{采集日期}_{视频数量}条/
    ├── 01_{视频ID}.md
    ├── 02_{视频ID}.md
    └── _all.json  # 规范化后的汇总数据
```

每个 Markdown 文件包含视频基本信息、介绍或文案、选题方向、主题总结、逐字稿及其状态。仓库自带零依赖校验/导出脚本：

```bash
python skills/douyin-transcript-exporter/scripts/export_local.py input.json --validate-only
python skills/douyin-transcript-exporter/scripts/export_local.py input.json --output-root douyin_data
```

运行仓库测试：

```bash
python -m unittest discover -s tests -v
```

## 使用方式

将 [skills/douyin-transcript-exporter](skills/douyin-transcript-exporter) 导入豆包工作的 Skill 环境后调用，并提供抖音博主主页链接、单条视频链接或分享短链。需要写入飞书多维表格时，再提供目标表格链接；明确选择本地保存时无需提供。

安装时可直接使用以下提示词：

```text
请打开下面的 GitHub 仓库，找到其中的 douyin-transcript-exporter Skill，阅读相关文件并完成安装：
https://github.com/QIANLING-0831/make-social-media-data-tools
安装完成后，请告诉我安装结果。
```

## 主要改进

- 以 `video_id` 作为稳定主键，统一短链、带查询参数链接和标准链接的去重行为。
- 明确区分逐字稿成功、未请求、无口播和失败，失败原因不再混入正文。
- 对互动数、日期、AI 扩展字段和占位内容执行自动质量检查。
- 本地导出遇到同名批次时自动创建新目录，不覆盖既有结果。
- GitHub Actions 自动运行单元测试和 Python 语法检查。

## 上游与许可

上游仓库目前未提供明确的开源许可证。本仓库保留原提交历史与署名；使用、修改或再分发前，请自行确认已获得相应授权。
