---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: 'ffe28481-c690-4ee9-9d6a-52eb99bacea4'
  PropagateID: 'ffe28481-c690-4ee9-9d6a-52eb99bacea4'
  ReservedCode1: '7e976d91-28d1-47d5-84ec-15e4124613ea'
  ReservedCode2: '7e976d91-28d1-47d5-84ec-15e4124613ea'
---

# Kaoyan AI Toolkit (考研 AI 备考工作台)

> 用 AI 把西综真题榨干：考点分析 → 复习规划 → 思维导图 → 错题复盘。

面向西医综合（306）考研党的一站式 AI 备考工具。上传你自己拥有的真题/资料，工具在本地解析后，调用 DeepSeek 帮你做**考点考频分析**、生成**复习规划**、输出**思维导图**、**错题复盘**。

## 为什么做这个

考研党最常见的困境：真题资料一大堆，但没人帮你整理成"能指导复习"的东西。医考帮的考频分析要付费 VIP 且封闭。这个工具让你**用自己手上的真题，免费生成属于你自己的备考分析**，数据不出你的电脑（除主动调 API 外）。

## 核心功能

- **考点分析**：上传真题文本/PDF → 自动按西综六大科目归类 → 输出考点考频统计 + 科目分布 + 薄弱点诊断（DeepSeek 辅助）
- **复习规划**：输入考试日期 + 每天可用时长 → 生成按科目/优先级分层的周计划（纯本地算法，可离线）
- **思维导图**：把考点分析结果导出为 Markdown / Mermaid 思维导图（可直接在支持 Mermaid 的工具中渲染）
- **错题复盘**：粘贴错题 → AI 生成"错因分析 + 知识点回归 + 同类题预测"
- **Gradio 界面**：浏览器打开即用，无需命令行

## 快速开始

```bash
# 1. 安装
pip install -r requirements.txt

# 2. 配置 DeepSeek API Key（环境变量，不硬编码）
# Windows PowerShell:
$env:DEEPSEEK_API_KEY = "sk-你的key"

# 3. 启动 Web 界面
python app.py
# 浏览器打开 http://127.0.0.1:7860
```

## 命令行用法

```bash
# 考点分析（需要 API）
python -m kaoyan_toolkit.cli analyze 真题.txt -o output/

# 复习规划（纯本地，不需要 API）
python -m kaoyan_toolkit.cli plan --exam-date 2027-12-25 --daily-hours 4 -o output/

# 思维导图（本地）
python -m kaoyan_toolkit.cli mindmap 真题.txt -o output/

# 错题复盘（需要 API）
python -m kaoyan_toolkit.cli review 错题.txt -o output/
```

## 目录结构

```
kaoyan_toolkit/
├── cli.py        # 命令行入口
├── parse.py      # 资料解析（txt/pdf/docx）
├── extract.py    # 考点关键词提取（本地规则 + jieba）
├── analyze.py    # 考频统计（确定性算法）
├── ai.py         # DeepSeek 集成（考点归纳/错题复盘）
├── planner.py    # 复习规划算法（本地）
├── export.py     # 思维导图导出（Markdown/Mermaid）
├── cache.py      # SQLite 缓存（省 API 费用）
└── prompt.py     # 提示词模板（西综考点分析/错题复盘）
```

## 数据合规

- 仓库内**不含任何版权真题内容**，请导入你自己拥有的真题/资料（自用合法数据）
- API Key 只走环境变量，绝不硬编码
- 默认数据本地处理，调用 AI 时界面会明示

## License

MIT License.