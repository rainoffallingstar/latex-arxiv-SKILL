# 学术综述论文写作框架 (Codex SKILL)

[English](README.md) · 简体中文

一个端到端、issue 驱动的 **Codex SKILL**，用于撰写带有已验证引文的学术综述论文。支持多文献来源、多学科领域、Typst（主力）和 LaTeX（传统）模板、可配置引用风格，以及通过 pandoc 生成 Markdown 输出。

## 能力

| 维度 | 支持 |
|------|------|
| **输出格式** | Typst（主力）、LaTeX（传统）、Markdown（通过 pandoc） |
| **文献来源** | arXiv、PubMed、OpenAlex、Europe PMC、bioRxiv、paper-search |
| **学科领域** | 计算机科学、生物医学、物理学、化学、工程学、数学、社会科学、环境科学 |
| **模板** | Typst：通用学术 + 生物医学；LaTeX：IEEEtran、article、biomedical（传统） |
| **引用风格** | IEEE 编号 (ieee.csl) 或 著者-年份 (apa.csl) |
| **工作流** | 门禁制：配置 → 计划 → issues CSV → 逐节写作 → QA → 编译 |

## 这里有什么

- **主 SKILL**：`academic-paper-writer` 位于 `.codex/skills/academic-paper-writer/SKILL.md`。
- **辅助脚本**：脚手架、文献注册中心、计划、校验、编译等位于 `scripts/`。
- **配置系统**：`paper-config.yml` 根据主题领域驱动输出格式、模板选择、引用风格和文献来源偏好。
- **示例输出**：`example/` 中的已生成论文（含编译后的 PDF）。

## 快速开始（2 条 prompt → 可编译的论文）

### 示例 1：计算机科学主题（Typst，IEEE 编号引用）

**Prompt 1：**
```
write a review article about recent advances in transformer architectures
```

Agent 自动检测领域（computer-science），生成 `paper-config.yml`（Typst 输出 + IEEE 编号引用），进行文献检索，搭建章节框架，提供候选标题，并创建 `plan/` 文件。

**Prompt 2：**
```
I will let you choose the best title and proceed
```

Agent 完成全文写作并编译为 PDF。

### 示例 2：生物医学主题（Typst，著者-年份引用）

**Prompt 1：**
```
write a review article about CRISPR gene editing for cancer therapy
```

Agent 自动检测领域（biomedical），生成 `paper-config.yml`（Typst 输出 + APA 著者-年份引用），推荐 PubMed + Europe PMC + OpenAlex + paper-search 作为文献源。

**Prompt 2：**
```
approved, proceed
```

Agent 使用生物医学 Typst 模板搭建项目，初始化多源文献注册中心，开始写作循环。

### 示例 3：Markdown 输出

```bash
python3 scripts/compile_paper.py --project-dir <paper_dir> --format markdown
```

先编译 Typst 为 PDF，再通过 pandoc 转换为 Markdown。

## 论文配置

框架自动检测主题领域并生成 `paper-config.yml`。你可以检查并手动调整：

```bash
python3 scripts/paper_config.py detect --topic "你的主题"
python3 scripts/paper_config.py generate --topic "你的主题" --output paper-config.yml
```

生物医学论文的示例配置：

```yaml
topic: CRISPR 基因编辑在癌症治疗中的应用
domain: biomedical
output_format: typst
template_class: article
citation_style: author-year
preferred_sources: [pubmed, europepmc, openalex, paper-search]
section_framework: [引言, 疾病概述, 分子机制, ...]
```

## 工作流（门禁制）

```
Gate 0: paper-config.yml + 研究快照 + 草案计划 → 用户审批
Gate 1: issues CSV（执行合同）
Phase 2: 逐 issue 写作循环（研究 → 写作 → 验证 → 更新）
Phase 3: QA + 跨源去重 + 编译 → 交付
```

完整门禁工作流见 [SKILL.md](.codex/skills/academic-paper-writer/SKILL.md)。

## 环境要求

| 需求 | 说明 |
|------|------|
| Python 3.8+ | 脚本运行要求 |
| PyYAML | `pip install -r requirements.txt` |
| Typst | `brew install typst`（主力编译器） |
| Pandoc | `brew install pandoc`（可选，用于 Markdown 转换） |
| LaTeX | `pdflatex` + `bibtex`（可选，传统模式） |
| paper-search | `brew install paper-search`（可选，统一文献检索） |

已在 macOS + Codex CLI 上测试通过。
