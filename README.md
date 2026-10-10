<div align="center">

# 🚀 Trendshift Daily

**全自动 GitHub 趋势榜单智能抓取、结构化 LLM 研判与多渠道投递系统**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Code Style](https://img.shields.io/badge/code%20style-pep8-green.svg)](https://pep8.org/)

[English](./README.en.md) · [简体中文](./README.md)

</div>

---

## 💡 为什么需要 Trendshift Daily？

在海量的开源项目中，传统的 Trending 榜单存在严重的信息过载与痛点：
* **刷榜与僵尸项目泛滥**：许多上榜仓库其实早已停止维护（甚至已归档）；
* **简介空洞无物**：只看官方英文简介或“开源项目”等几个词，根本不知道核心解决了什么痛点；
* **缺乏针对性价值**：无法快速评估该项目对自己当前的业务、架构或运维场景有何实际收益。

**Trendshift Daily** 专为解决这一问题而生！它每天从 [Trendshift](https://trendshift.io/) 自动化汇总 **日榜、周榜、月榜、年榜及 GitHub Trending 历史榜**，结合 GitHub API 过滤僵尸库，并由大模型执行**严格基于证据的中文深度研判**，最终以精美的高信息密度卡片投递到飞书，并预留博客与微信公众号分发接口。

---

## ✨ 核心特性

* 🔍 **五榜聚合与保序去重**：自动抓取日、周、月、年及 Trending 五大榜单，智能保留各榜单最新趋势。
* 🛡️ **严格硬否决规则引擎**：
  * **一票否决**：已归档（Archived）或超过 730 天未更新代码的仓库自动标记不推荐并附带删除线；
  * **依凭强核验**：研判结论必须依凭官方描述、Topics 或 README，严禁无源臆测与大模型幻觉。
* 🧠 **LLM 结构化中文深度研判**：
  * 告别敷衍英文短句，自动提取 40~75 字精准功能定位与技术亮点；
  * 从家庭服务器自动化、常驻 Agent 运维、安全逆向等维度给出针对性价值评估。
* 🎨 **设计感多级折叠卡片**：
  * 专为移动端与 PC 端优化的大盘卡片，所有精选研判与原始榜单**默认优雅折叠**；
  * 彩色视觉标签体系（`🔥【必看】`、`✨【推荐】`、`📌【关注】`、`⚠️【不推荐】`）；
  * 仓库名全量配备可直接点击跳转的 GitHub 超链接。
* 🔌 **多渠道发布器解耦架构**：
  * 内置 **FeishuPublisher**（飞书交互卡片）；
  * 抽象预留 **BlogMarkdownPublisher**（静态博客文章）与 **WeChatMpPublisher**（微信公众号图文）通道。

---

## 🚀 3 分钟快速上手

### 1. 克隆仓库与安装依赖

```bash
git clone https://github.com/iMissNan/trendshift-daily.git
cd trendshift-daily

# 安装依赖
pip install -r requirements.txt
playwright install chromium
```

### 2. 准备配置文件

复制模板配置文件：
```bash
cp config/trendshift.example.yaml config/trendshift.yaml
```

根据你的实际环境修改 `config/trendshift.yaml`：
- 配置大模型 API Endpoint 与 Key；
- 配置飞书机器人的 App ID 与 App Secret。

### 3. 一键运行全流程流水线

```bash
python -m trendshift_daily.pipeline
```

---

## 🏛️ 架构设计

```text
       Trendshift 5 大榜单 (日/周/月/年/Trending)
                        │
                        ▼
       [Playwright 滚动采集器] -> 榜单原文与保序去重
                        │
                        ▼
       [GitHub API 检索器] -> 客观元数据 (Stars, Topics, Pushed_at)
                        │
                        ▼
       [分析引擎 (Analyzer)] -> 硬否决判定 + LLM 深度中文提取
                        │
                        ▼
       [卡片与通道渲染器] -> 飞书卡片 / 博客 Markdown / 公众号 HTML
```

---

## 📄 开源许可证

本项目基于 [MIT 许可证](./LICENSE) 开源。
