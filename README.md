# GraphMind Agent

> Knowledge Graph Construction & Grounded Question-Answering Agent

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.x-4581C3?logo=neo4j&logoColor=white)](https://neo4j.com/)
[![Tests](https://img.shields.io/badge/tests-7%20passed-brightgreen)](#测试)

一个面向非结构化文档的通用知识图谱构建与可追溯问答流程。项目将本地文档转换为实体—关系图谱，写入 Neo4j，并在回答问题时先检索图谱证据，再调用兼容 OpenAI Chat Completions 协议的大语言模型生成回答。

**English summary:** A domain-neutral pipeline that extracts entities and relations from unstructured documents, stores them in Neo4j, retrieves graph evidence for a question, and generates a grounded answer with traceable evidence.


## 项目能力

- 读取 `.txt`、`.md`、`.html`、`.htm` 文档
- 调用大语言模型抽取实体、类型、属性与关系
- 规范化并合并重复实体和关系，输出结构化 JSON
- 将知识图谱导入 Neo4j
- 从问题中提取检索词，在图谱中召回相关三元组
- 基于检索证据生成回答，并返回可核对的证据列表
- 仅保存相对来源引用，避免把本机绝对路径写入产物

## 工程亮点

- **结构化输出约束**：模型响应经过 JSON 提取与 Pydantic 数据校验后才进入图谱流程。
- **稳定标识与图谱去重**：实体采用规范化内容哈希生成稳定 ID，跨文档结果统一合并。
- **可追溯回答**：回答结果同时保留证据三元组与来源引用，便于复核生成依据。
- **失败安全设计**：没有检索到图谱证据时直接返回证据不足，不让模型脱离上下文生成答案。
- **配置与代码分离**：模型服务和 Neo4j 凭据只从环境变量读取，仓库不保存敏感配置。
- **领域中立设计**：不预设具体行业本体，可通过抽取提示词和数据模型扩展到不同文本集合。

## 技术栈

| 模块 | 技术 |
| --- | --- |
| 开发语言 | Python 3.10+ |
| 数据建模 | Pydantic 2 |
| 图数据库 | Neo4j 5.x / Cypher |
| 模型调用 | OpenAI Chat Completions 兼容接口 |
| HTTP 客户端 | Requests |
| 配置管理 | python-dotenv / 环境变量 |
| 测试 | Pytest |

## 流程

```text
本地文档
   │
   ▼
文档读取与清洗 ──► LLM 实体/关系抽取 ──► 规范化与去重
                                              │
                                              ▼
                                         Graph JSON
                                              │
                                              ▼
问题 ──► 检索词提取 ──► Neo4j 图谱检索 ──► 证据约束回答
```

详细设计见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

## 目录结构

```text
.
├─ src/kg_qa_agent/
│  ├─ cli.py          # 命令行入口
│  ├─ ingest.py       # 文档发现与清洗
│  ├─ extractor.py    # 通用实体/关系抽取
│  ├─ graph.py        # 图谱合并、导入与检索
│  ├─ qa.py           # 证据约束问答流程
│  ├─ llm.py          # OpenAI 兼容接口客户端
│  ├─ models.py       # 数据模型
│  └─ config.py       # 环境变量配置
├─ tests/             # 不依赖网络与数据库的单元测试
├─ docs/              # 架构与公开审查说明
├─ .env.example       # 配置模板，不含真实凭据
└─ pyproject.toml
```

## 快速开始

### 1. 环境要求

- Python 3.10+
- 可访问的 OpenAI Chat Completions 兼容模型服务
- Neo4j 5.x（导入图谱和问答阶段需要）

### 2. 安装

```bash
python -m venv .venv
```

Windows PowerShell：

```powershell
.venv\Scripts\Activate.ps1
python -m pip install -e .
```

### 3. 配置

复制 `.env.example` 为 `.env`，填写自己的服务配置：

```dotenv
LLM_BASE_URL=https://your-provider.example/v1
LLM_API_KEY=replace-with-your-key
LLM_MODEL=replace-with-model-name
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=replace-with-your-password
```

`.env` 已被忽略，不应提交到 GitHub。

### 4. 构建知识图谱

输入目录可包含多个受支持的文本文件：

```bash
kg-qa extract --input path/to/documents --output output/graph_bundle.json
```

导入 Neo4j：

```bash
kg-qa import --bundle output/graph_bundle.json
```

### 5. 智慧问答

```bash
kg-qa ask "请说明相关概念之间的关系" --output output/answer.json
```

终端输出回答；可选的 JSON 文件同时保存证据三元组与来源引用。若图谱未检索到证据，流程会明确返回“当前知识图谱中没有足够证据”，而不是要求模型凭空补全。

## 数据格式

图谱产物主要包含：

- `sources`：文档标识、标题、相对来源引用
- `entities`：实体标识、名称、类型、描述与属性
- `relations`：起点、关系类型、终点与来源文档

实体和关系类型会统一为大写下划线形式，例如 `CONCEPT`、`RELATED_TO`。项目不内置行业本体，可根据公开目标自行扩展抽取提示词和数据模型。

## 测试

```bash
python -m pip install -e .[dev]
pytest
```

测试覆盖标识稳定性、符号规范化、模型响应 JSON 解析、无效关系过滤、图谱去重和相对来源路径处理。外部模型服务与 Neo4j 的可用性需要在实际环境中单独进行集成验证。

## 安全与隐私

- 不包含数据集、业务材料或领域专用本体
- 不包含 `.env`、API Key、Token、账号密码或数据库导出
- 不包含个人姓名、证件或教育信息、电话、邮箱等身份信息
- 不包含本机绝对路径；运行产物只记录相对来源引用
- `output/`、日志、缓存、虚拟环境和 Neo4j 本地文件均默认忽略

公开前核查记录见 [docs/PUBLICATION_REVIEW.md](docs/PUBLICATION_REVIEW.md)。

## 当前边界

- 文档读取目前面向纯文本与 HTML；PDF、Word 等格式需先转为文本或扩展读取器。
- 抽取质量依赖所选模型及文档质量，本项目不声明未经验证的准确率。
- 当前检索采用实体名称/描述与关系类型的关键词匹配，不包含向量检索或混合排序。
- 本仓库未附带数据集，因此首次运行需要使用者提供有权处理的自有文本。

## 项目定位

该仓库用于展示知识图谱构建、LLM 结构化抽取、图数据库检索和证据约束生成的完整工程链路。仓库不附带特定领域数据，因此可以独立审查代码结构，也方便使用者接入有权处理的文本进行验证。

## License

发布前请由项目所有者确认代码权属并选择许可证；本整理版本暂不预设许可证。
