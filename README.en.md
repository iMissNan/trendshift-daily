<div align="center">

# 🚀 Trendshift Daily

**Automated GitHub Trending Aggregator, Structured LLM Analyzer & Multi-Channel Distribution System**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Code Style](https://img.shields.io/badge/code%20style-pep8-green.svg)](https://pep8.org/)

[English](./README.en.md) · [简体中文](./README.md)

</div>

---

## 💡 Why Trendshift Daily?

In the vast sea of open-source projects, traditional Trending lists suffer from severe information overload:
* **Spam & Zombie Projects**: Many trending repos are abandoned or already archived;
* **Hollow Descriptions**: Relying solely on brief official descriptions or generic terms makes it hard to grasp the actual value;
* **Lack of Contextual Value**: Difficult to assess how a repository benefits your specific development or self-hosted server scenarios.

**Trendshift Daily** solves this! Every day, it automatically aggregates the **Daily, Weekly, Monthly, Yearly, and GitHub Trending historical charts** from [Trendshift](https://trendshift.io/), filters out zombie projects using GitHub API, conducts **evidence-based deep structured analysis** with LLM, and delivers beautiful, high-density interactive cards to Feishu/Lark, with built-in channels for blogs and WeChat Official Accounts.

---

## ✨ Features

* 🔍 **5-Board Aggregation & Deduplication**: Scrapes Daily, Weekly, Monthly, Yearly, and Trending charts while preserving ranking orders.
* 🛡️ **Strict Rule Engine & Veto Filter**:
  * **One-Vote Veto**: Repos archived or inactive for >730 days are automatically rejected with strikethrough tags;
  * **Evidence Verification**: Analysis must cite official descriptions, topics, or README sections, preventing hallucinations.
* 🧠 **Structured In-Depth Analysis**:
  * Delivers 40~75 words of clear functional highlights and mechanism explanations;
  * Evaluates tailored value for self-hosted servers, autonomous agents, and DevOps tooling.
* 🎨 **Foldable & Interactive Cards**:
  * High-density dashboard optimized for mobile and desktop viewing with **default collapsed panels**;
  * Semantic color tags (`🔥 [Must Read]`, `✨ [Recommended]`, `📌 [Follow]`, `⚠️ [Rejected]`);
  * Direct one-click GitHub links for every repository.
* 🔌 **Decoupled Multi-Channel Architecture**:
  * Built-in **FeishuPublisher** (Lark Interactive Cards);
  * Extensible interfaces for **BlogMarkdownPublisher** (Static Blogs) and **WeChatMpPublisher** (WeChat Articles).

---

## 🚀 Quick Start in 3 Minutes

### 1. Clone & Install

```bash
git clone https://github.com/iMissNan/trendshift-daily.git
cd trendshift-daily

# Install dependencies
pip install -r requirements.txt
playwright install chromium
```

### 2. Prepare Configuration

Copy the example configuration:
```bash
cp config/trendshift.example.yaml config/trendshift.yaml
```

Update `config/trendshift.yaml` with your actual LLM endpoints and Feishu credentials.

### 3. Run Pipeline

```bash
python -m trendshift_daily.pipeline
```

---

## 📄 License

This project is licensed under the [MIT License](./LICENSE).
