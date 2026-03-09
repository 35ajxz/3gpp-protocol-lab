# 3GPP Protocol Lab

一个面向 `TS 38.331 Rel-17` 的独立 3GPP 协议分析与模糊测试实验工程。

本项目目前同时维护两条流水线：

- `bootstrap`：轻依赖、本地可快速重跑的最小闭环。
- `real`：真实文档接入、真实 ASN.1 编译、真实 runtime 产物生成。

## 1. 项目研究背景和要解决的工程/技术问题

### 1.1 研究背景

3GPP 规范，尤其是 `TS 38.331` 这类 RRC 协议规范，存在几个天然难点：

- 文档体量大，章节交叉引用密集，手工梳理成本高。
- 协议逻辑不是简单的线性步骤，而是带状态、定时器、条件守卫和上下文变量的扩展有限状态机（EFSM）。
- 协议消息承载在 ASN.1 定义之上，只有“状态机图”没有“可编码消息”并不能支撑真正的 Fuzz 输入生成。
- 纯文本级 RAG 或关键词检索容易丢失上下文和 clause 关系，导致提取结果不稳定。
- 即使拿到了 EFSM 草稿，如果不能进一步转成可验证、可编码、可回放的输入物，工程价值仍然有限。

### 1.2 本项目要解决的核心问题

本项目聚焦把“规范理解”推进到“工程可执行”这一层，目标不是只做分析报告，而是建立一个可重跑、可校验、可继续扩展的协议实验底座。当前重点解决以下问题：

1. 规范导入问题  
   把真实 `38.331` 文档从本地归档文件转成可切片、可检索、可后续处理的 Markdown 语料。

2. Procedure 切片问题  
   把规范按 `5.3.x` 粒度切成工程上可消费的 procedure 单元，而不是整本长文直接送模型。

3. EFSM 提取问题  
   让模型输出严格受 schema 约束的 JSON，而不是自由文本总结。

4. ASN.1 约束问题  
   从规范正文中提取 `NR-RRC-Definitions`，并通过 `asn1tools` 编译和 roundtrip 验证，确保消息不是“只看起来合理”。

5. runtime 输入生成问题  
   从 EFSM 和 ASN.1 结果出发，生成 `seed -> PDU -> pcap -> replay` 的可执行输入物。

6. 独立工程化问题  
   把工程做成一个单独项目，具备本地命令入口、中文文档、固定目录结构、可追踪输出，不依赖旧工程目录。

## 2. 本项目的技术选型和整体架构

### 2.1 技术选型

- 编排与工程骨架：`Python 3`
  - 用于组织整条流水线，包括导入、切片、验证、seed 生成、runtime 打包和测试。
- AI 语义提取：`Codex CLI` + `JSON Schema`
  - 用于把 3GPP procedure 文本提取成结构化 EFSM。
  - 通过 `--output-schema` 把模型输出限制在工程可消费的 JSON 结构内。
- 规则与约束：`YAML` + Python 校验脚本
  - 用于补足 LLM 不擅长的确定性检查，例如字段约束、路径完整性、消息/定时器/变量覆盖。
- ASN.1 编译与编码验证：`asn1tools`
  - 用于编译 `NR-RRC-Definitions`，并对 `UPER` 编解码进行 roundtrip 验证。
- 检索与关系存储：`SQLite`
  - 用于 bootstrap 路线中的本地检索和结构化关系组织。
- 形式化输出：`Promela / NuSMV`
  - 当前先生成形式化模型文本，为后续接入外部 model checker 预留接口。
- runtime 产物生成：`Scapy` + 本地 UDP 注入脚本
  - 用于把 EFSM/ASN.1 结果转换成 `.uper.bin`、`.pcap` 和可执行 replay 入口。
- 目标系统接入：项目内 `targets/oai/*`
  - 用于承接未来的 OAI/RFSIM 在线注入和更真实的协议测试。

### 2.2 AI 在本项目中的位置

这个项目不是“把整本 3GPP 文档直接扔给模型，然后相信它的回答”，而是把 AI 放在一个受约束的位置上：

1. AI 负责语义理解  
   主要用于把 procedure 文本转换成 EFSM 草稿，尤其处理状态、定时器、条件分支、动作等语义结构。

2. 工程脚本负责确定性执行  
   切片、约束装配、ASN.1 编译、PDU 生成、pcap 封装、runtime 打包都由本地脚本完成，不依赖模型自由发挥。

3. Schema 和验证层负责约束 AI  
   模型输出必须先满足 schema，再通过消息/定时器/变量/步骤顺序等校验，才能进入后续阶段。

4. AI 结果不是终点，而是中间资产  
   EFSM 只是中间表示，后面还要继续进入 `seed -> PDU -> pcap -> replay` 的工程链路。

### 2.3 顶层架构

下面是本项目的顶层设计。它体现的是“AI 辅助 3GPP 协议安全研究与测试”的完整主线，而不是单个脚本的执行顺序：

```text
+----------------------------------------------------------------------------------+
|                       3GPP Protocol Lab 顶层架构                                 |
+----------------------------------------------------------------------------------+
| 目标：把 3GPP 规范文本转成可验证、可编码、可回放、可接目标系统的安全测试资产      |
+----------------------------------------------------------------------------------+

  [A] 规范输入层
      3GPP 文档 / 本地归档 / bootstrap fixture
                           |
                           v
  [B] 语料工程层
      导入 -> 清洗 -> Markdown 化 -> procedure 切片 -> 检索索引
                           |
                           v
  [C] AI 语义提取层
      LLM 读取切片 -> 按 schema 输出 EFSM / 结构化过程语义
                           |
                           v
  [D] 确定性验证与约束层
      schema 校验 -> 覆盖率检查 -> ASN.1 提取/编译 -> roundtrip 验证
                           |
                           v
  [E] 测试资产生成层
      EFSM -> seed -> PDU -> pcap -> runtime manifest -> replay script
                           |
                           v
  [F] 目标执行层
      离线 replay / OAI compose override / 后续在线注入与安全测试
```

### 2.4 分层展开

为了更贴近工程实现，下面把上面的 6 层再展开成“谁负责什么”的视图。

#### 2.4.1 规范输入层 + 语料工程层

```text
[规范输入]
  bootstrap fixture
  real 3GPP 归档文件
        |
        v
[语料工程]
  scripts/docx_3gpp.py
  scripts/ingest_real_spec.py
  scripts/slice_procedures.py
  scripts/retrieve.py
        |
        +--> corpus/raw/*.md
        +--> corpus/slices/*.md
        +--> corpus/real/raw/*.md
        +--> corpus/real/slices/*.md
        +--> outputs/retrieval/last_query.json
```

#### 2.4.2 AI 语义提取层 + 确定性验证层

```text
[procedure slices]
        |
        v
[AI 语义提取]
  scripts/extract_efsm.py        # bootstrap 的确定性提取
  scripts/extract_efsm_llm.py    # real 的 LLM 提取
        |
        +--> outputs/efsm/*.json
        +--> outputs/efsm_real/*.json
        |
        v
[验证与约束]
  scripts/validate_efsm.py
  scripts/validate_efsm_real.py
  scripts/extract_asn1.py
  scripts/validate_asn1.py
  schemas/efsm.schema.json
  schemas/efsm.codex.schema.json
        |
        +--> outputs/reports/*.json
        +--> outputs/reports_real/*.json
        +--> outputs/asn1/*.asn1
        +--> outputs/asn1/validation.json
```

#### 2.4.3 测试资产生成层 + 目标执行层

```text
[已验证的 EFSM + ASN.1]
        |
        v
[测试资产生成]
  scripts/generate_seeds.py
  scripts/build_graph.py
  scripts/export_formal.py
  scripts/check_properties.py
  scripts/generate_paths.py
  scripts/render_mermaid.py
  scripts/build_runtime_bundle.py
        |
        +--> outputs/seeds/*.json
        +--> outputs/graph/3gpp_lab.sqlite
        +--> outputs/formal/promela/*.pml
        +--> outputs/formal/nusmv/*.smv
        +--> outputs/properties/*.json
        +--> outputs/paths/*.json
        +--> outputs/mermaid/*.mmd
        +--> outputs/runtime/*
        |
        v
[目标执行]
  scripts/send_runtime_pdu.py
  outputs/runtime/replay_runtime.sh
  targets/oai/docker-compose.yaml
  outputs/runtime/oai/docker-compose.runtime.yaml
```

### 2.5 核心执行入口

- `scripts/run_pipeline.py`
  - 串起 bootstrap 全链路。
- `scripts/run_real_pipeline.py`
  - 串起真实文档导入、ASN.1 提取/验证、LLM EFSM 提取、runtime 生成。
- `Makefile`
  - 提供 `all / real / test / venv` 等快捷目标。

## 3. 当前已实现的功能或状态

### 3.1 已实现功能

#### Bootstrap 流水线

- 基于本地 Markdown fixture 的 procedure 切片。
- 基于受限 transition DSL 的确定性 EFSM 提取。
- 结构校验、术语覆盖、引用闭包验证。
- 本地检索结果输出。
- SQLite 图谱生成。
- Promela / NuSMV 文本导出。
- 基于图的属性检查。
- 路径规划。
- Mermaid 状态图导出。
- 语义化 seed 生成。

#### Real 流水线

- 从本地 `38331-h60.zip` 解析真实 `38.331` 文档。
- 产出真实 Markdown 和真实 procedure slices。
- 使用 Codex 对真实章节做 schema 约束的 EFSM 提取。
- 从规范中抽取 `NR-RRC-Definitions`。
- 使用 `asn1tools` 编译并完成 UPER roundtrip 验证。
- 生成 runtime seed、PDU、pcap、compose override 和 replay 脚本。
- 运行时完全自包含，不依赖外部旧项目。

### 3.2 当前状态指标

根据当前仓库内已有输出文件，项目状态如下：

- 真实文档导入
  - `outputs/reports_real/real_ingest.json` 显示：
    - `paragraph_count = 49972`
    - `slice_count = 3`
    - 已切出：
      - `5.3.3` RRC connection establishment
      - `5.3.5.11` full configuration
      - `5.3.13` RRC connection resume

- 真实 EFSM 验证
  - `outputs/reports_real/*.json` 当前全部 `pass = true`
  - 三个 real procedure 的 `messages / timers / variables` 覆盖率当前都是 `1.0`

- ASN.1 验证
  - `outputs/asn1/validation.json` 显示：
    - `type_count = 1911`
    - `RRCSetupRequest` nominal/boundary roundtrip 通过
    - `RRCResumeRequest` nominal/boundary roundtrip 通过

- runtime 生成
  - `outputs/runtime/manifest.json` 显示：
    - `entry_count = 13`
    - `compose_check.pass = true`
    - `udp_injector.pass = true`

- 测试
  - `tests/test_pipeline.py` 当前覆盖 bootstrap 主路径的 5 个测试点。

### 3.3 当前边界和未完成项

- 真实流水线目前只覆盖 3 个 procedure，不是全量 `38.331`。
- 真实 EFSM 提取依赖本机已登录的 `codex` CLI。
- 当前 runtime 以离线 replay / 合成 pcap 为主，尚未做在线 OAI RFSIM 注入闭环。
- 当前形式化层仍以“模型导出 + 图检查”为主，尚未接 `SPIN/NuSMV` 实际求解。
- `vendor/3gpp/38331-h60.zip` 是本地输入文件，默认忽略，不随仓库发布。

## 4. 快速开始

### 4.1 环境准备

创建虚拟环境并安装依赖：

```bash
cd 3gpp-protocol-lab
make venv
```

或手工执行：

```bash
cd 3gpp-protocol-lab
python3 -m venv .venv
.venv/bin/pip install pyyaml asn1tools scapy
```

### 4.2 运行 bootstrap 流水线

```bash
cd 3gpp-protocol-lab
python3 scripts/run_pipeline.py
```

### 4.3 运行真实流水线

前提：

- 本机已有 `codex` CLI 且已登录。
- 本地存在 `vendor/3gpp/38331-h60.zip`。

执行：

```bash
cd 3gpp-protocol-lab
.venv/bin/python scripts/run_real_pipeline.py
```

### 4.4 运行测试

```bash
cd 3gpp-protocol-lab
python3 -m unittest discover -s tests
```

## 5. 项目文件目录详细说明

说明：

- 下列清单覆盖当前仓库已纳入版本控制的全部叶子文件。
- `.git/`、`.venv/`、`__pycache__/` 属于 Git 或本地环境/缓存目录，不在正文中逐项展开。
- 最后一节补充了项目约定的本地忽略文件。

```text
3gpp-protocol-lab/                                              # 项目根目录
├── .gitignore                                                  # Git 忽略规则，排除本地环境、缓存与原始 zip
├── Makefile                                                    # 常用命令入口，如 venv / real / test
├── README.md                                                   # 项目总说明文档
├── constraints/                                                # 约束定义目录
│   ├── messages.yaml                                           # 消息字段默认值、边界值与 seed 生成约束
│   └── properties.yaml                                         # bootstrap 属性检查规则
├── corpus/                                                     # 语料与切片目录
│   ├── raw/                                                    # bootstrap 原始语料目录
│   │   └── ts-38.331-rel17-bootstrap.md                        # bootstrap 示例规范文本
│   ├── real/                                                   # 真实规范处理结果目录
│   │   ├── raw/                                                # 真实规范标准化 Markdown 目录
│   │   │   └── ts-38.331-v17.6.0.md                            # 从 38.331 提取后的真实 Markdown 主文档
│   │   └── slices/                                             # 真实规范切片目录
│   │       ├── 5.3.13-rrc-connection-resume.md                 # 真实 `RRC connection resume` 切片
│   │       ├── 5.3.3-rrc-connection-establishment.md           # 真实 `RRC connection establishment` 切片
│   │       └── 5.3.5.11-full-configuration.md                 # 真实 `full configuration` 切片
│   └── slices/                                                 # bootstrap 切片目录
│       ├── 5.3.13-rrc-connection-resume.md                     # bootstrap `RRC resume` 切片
│       ├── 5.3.3-rrc-connection-establishment.md               # bootstrap `RRC establishment` 切片
│       └── 5.3.5.11-full-configuration-procedure.md            # bootstrap `full configuration` 切片
├── docs/                                                       # 其他文档目录
│   └── ROADMAP.md                                              # 当天压缩版路线图
├── outputs/                                                    # 所有已生成输出目录
│   ├── asn1/                                                   # ASN.1 提取、编译与验证输出
│   │   ├── NR-RRC-Definitions.asn1                             # 从规范中提取的 ASN.1 定义
│   │   ├── NR-RRC-Definitions.meta.json                        # ASN.1 提取过程元数据
│   │   ├── validation.json                                     # ASN.1 编解码 roundtrip 验证报告
│   │   └── pdus/                                               # ASN.1 直接产出的示例 PDU
│   │       ├── resume_request_boundary.uper.bin                # `RRCResumeRequest` 边界样本
│   │       ├── resume_request_nominal.uper.bin                 # `RRCResumeRequest` 正常样本
│   │       ├── setup_request_boundary.uper.bin                 # `RRCSetupRequest` 边界样本
│   │       └── setup_request_nominal.uper.bin                  # `RRCSetupRequest` 正常样本
│   ├── efsm/                                                   # bootstrap EFSM 输出目录
│   │   ├── 5.3.13-rrc-connection-resume.json                   # bootstrap `RRC resume` EFSM
│   │   ├── 5.3.3-rrc-connection-establishment.json             # bootstrap `RRC establishment` EFSM
│   │   └── 5.3.5.11-full-configuration-procedure.json          # bootstrap `full configuration` EFSM
│   ├── efsm_real/                                              # 真实文档经 Codex 提取后的 EFSM 输出目录
│   │   ├── 5.3.13-rrc-connection-resume.json                   # real `RRC resume` EFSM
│   │   ├── 5.3.3-rrc-connection-establishment.json             # real `RRC establishment` EFSM
│   │   └── 5.3.5.11-full-configuration.json                    # real `full configuration` EFSM
│   ├── formal/                                                 # 形式化导出目录
│   │   ├── nusmv/                                              # NuSMV 文本模型目录
│   │   │   ├── 5.3.13-rrc-connection-resume.smv                # `RRC resume` NuSMV 模型
│   │   │   ├── 5.3.3-rrc-connection-establishment.smv          # `RRC establishment` NuSMV 模型
│   │   │   └── 5.3.5.11-full-configuration-procedure.smv       # `full configuration` NuSMV 模型
│   │   └── promela/                                            # Promela 文本模型目录
│   │       ├── 5.3.13-rrc-connection-resume.pml                # `RRC resume` Promela 模型
│   │       ├── 5.3.3-rrc-connection-establishment.pml          # `RRC establishment` Promela 模型
│   │       └── 5.3.5.11-full-configuration-procedure.pml       # `full configuration` Promela 模型
│   ├── graph/                                                  # 图谱与关系存储目录
│   │   └── 3gpp_lab.sqlite                                     # SQLite 图谱数据库
│   ├── mermaid/                                                # Mermaid 状态图目录
│   │   ├── 5.3.13-rrc-connection-resume.mmd                    # `RRC resume` Mermaid 图
│   │   ├── 5.3.3-rrc-connection-establishment.mmd              # `RRC establishment` Mermaid 图
│   │   └── 5.3.5.11-full-configuration-procedure.mmd           # `full configuration` Mermaid 图
│   ├── paths/                                                  # 路径规划输出目录
│   │   ├── 5.3.13-rrc-connection-resume.json                   # `RRC resume` 路径规划
│   │   ├── 5.3.3-rrc-connection-establishment.json             # `RRC establishment` 路径规划
│   │   └── 5.3.5.11-full-configuration-procedure.json          # `full configuration` 路径规划
│   ├── properties/                                             # 属性检查输出目录
│   │   ├── 5.3.13-rrc-connection-resume.json                   # `RRC resume` 属性检查结果
│   │   ├── 5.3.3-rrc-connection-establishment.json             # `RRC establishment` 属性检查结果
│   │   └── 5.3.5.11-full-configuration-procedure.json          # `full configuration` 属性检查结果
│   ├── reports/                                                # bootstrap 验证报告目录
│   │   ├── 5.3.13-rrc-connection-resume.json                   # bootstrap `RRC resume` 报告
│   │   ├── 5.3.3-rrc-connection-establishment.json             # bootstrap `RRC establishment` 报告
│   │   └── 5.3.5.11-full-configuration-procedure.json          # bootstrap `full configuration` 报告
│   ├── reports_real/                                           # 真实规范验证报告目录
│   │   ├── 5.3.13-rrc-connection-resume.json                   # real `RRC resume` 验证报告
│   │   ├── 5.3.3-rrc-connection-establishment.json             # real `RRC establishment` 验证报告
│   │   ├── 5.3.5.11-full-configuration.json                    # real `full configuration` 验证报告
│   │   └── real_ingest.json                                    # 真实文档导入统计报告
│   ├── retrieval/                                              # 检索输出目录
│   │   └── last_query.json                                     # 最近一次检索结果
│   ├── runtime/                                                # runtime 打包输出目录
│   │   ├── manifest.json                                       # runtime 汇总清单
│   │   ├── replay_runtime.sh                                   # runtime 回放入口脚本
│   │   ├── oai/                                                # OAI runtime override 目录
│   │   │   └── docker-compose.runtime.yaml                     # 挂载 runtime 产物的 compose override
│   │   ├── pcaps/                                              # 合成 pcap 样本目录
│   │   │   ├── 5.3.13-step-3-boundary.pcap                     # `RRCResumeRequest` 边界 pcap
│   │   │   ├── 5.3.13-step-3-nominal.pcap                      # `RRCResumeRequest` 正常 pcap
│   │   │   ├── 5.3.3-step-1-boundary.pcap                      # `RRCSetupRequest` 边界 pcap
│   │   │   └── 5.3.3-step-1-nominal.pcap                       # `RRCSetupRequest` 正常 pcap
│   │   ├── pdus/                                               # runtime PDU 目录
│   │   │   ├── 5.3.13-step-3-boundary.uper.bin                 # `RRCResumeRequest` 边界 PDU
│   │   │   ├── 5.3.13-step-3-nominal.uper.bin                  # `RRCResumeRequest` 正常 PDU
│   │   │   ├── 5.3.13-step-4-nominal.uper.bin                  # `RRCResume` 正常 PDU
│   │   │   ├── 5.3.3-step-1-boundary.uper.bin                  # `RRCSetupRequest` 边界 PDU
│   │   │   └── 5.3.3-step-1-nominal.uper.bin                   # `RRCSetupRequest` 正常 PDU
│   │   └── seeds/                                              # runtime seed 目录
│   │       ├── 5.3.13-rrc-connection-resume.json               # `RRC resume` runtime seed 包
│   │       ├── 5.3.3-rrc-connection-establishment.json         # `RRC establishment` runtime seed 包
│   │       └── 5.3.5.11-full-configuration.json                # `full configuration` runtime seed 包
│   └── seeds/                                                  # bootstrap seed 输出目录
│       ├── 5.3.13-rrc-connection-resume.json                   # bootstrap `RRC resume` seed 包
│       ├── 5.3.3-rrc-connection-establishment.json             # bootstrap `RRC establishment` seed 包
│       └── 5.3.5.11-full-configuration-procedure.json          # bootstrap `full configuration` seed 包
├── schemas/                                                    # schema 定义目录
│   ├── efsm.codex.schema.json                                  # Codex 输出约束 schema
│   └── efsm.schema.json                                        # 通用 EFSM schema
├── scripts/                                                    # 主实现脚本目录
│   ├── __init__.py                                             # scripts 包初始化文件
│   ├── build_graph.py                                          # 生成 SQLite 图谱
│   ├── build_runtime_bundle.py                                 # 生成 runtime seeds / PDU / pcap / replay
│   ├── check_properties.py                                     # 执行图属性检查
│   ├── common.py                                               # 公共路径与读写工具函数
│   ├── docx_3gpp.py                                            # 解析 3GPP docx 的辅助逻辑
│   ├── export_formal.py                                        # 导出 Promela / NuSMV 模型
│   ├── extract_asn1.py                                         # 从规范中提取 ASN.1
│   ├── extract_efsm.py                                         # bootstrap EFSM 提取器
│   ├── extract_efsm_llm.py                                     # 基于 Codex 的真实 EFSM 提取器
│   ├── generate_paths.py                                       # 生成路径规划结果
│   ├── generate_seeds.py                                       # 生成 bootstrap seeds
│   ├── ingest_real_spec.py                                     # 导入真实规范并切片
│   ├── render_mermaid.py                                       # 导出 Mermaid 图
│   ├── retrieve.py                                             # 执行本地检索
│   ├── run_pipeline.py                                         # bootstrap 总入口
│   ├── run_real_pipeline.py                                    # real 总入口
│   ├── send_runtime_pdu.py                                     # 发送 runtime PDU 的 UDP 注入脚本
│   ├── slice_procedures.py                                     # 对语料进行 procedure 切片
│   ├── validate_asn1.py                                        # ASN.1 编译与 roundtrip 校验
│   ├── validate_efsm.py                                        # bootstrap EFSM 校验
│   └── validate_efsm_real.py                                   # real EFSM 校验
├── targets/                                                    # 目标系统配置目录
│   └── oai/                                                    # OAI 目标配置子目录
│       ├── README.md                                           # OAI 接入说明
│       ├── docker-compose.yaml                                 # OAI 基础 compose 文件
│       ├── gnb.sa.band78.106prb.rfsim.conf                     # OAI gNB 配置
│       ├── mini_nonrf_config.yaml                              # 非射频最小配置
│       ├── mysql-healthcheck.sh                                # OAI MySQL 健康检查脚本
│       ├── nrue.uicc.conf                                      # OAI UE UICC 配置
│       └── oai_db.sql                                          # OAI 初始化数据库脚本
└── tests/                                                      # 测试目录
    └── test_pipeline.py                                        # bootstrap 烟测与回归测试
```

### 5.1 重要目录职责说明

- `constraints/`
  - 存放 seed 字段约束和属性检查规则。
- `corpus/`
  - 存放 bootstrap 语料、真实语料和 procedure 切片结果。
- `outputs/`
  - 存放所有当前已生成的中间产物和最终产物。
- `schemas/`
  - 定义 EFSM 的通用 schema 和 Codex 输出 schema。
- `scripts/`
  - 存放全部编排脚本，是本项目真正的实现主体。
- `targets/oai/`
  - 存放独立 OAI 目标接入配置。
- `tests/`
  - 存放 bootstrap 烟测。

### 5.2 本地忽略文件和目录

以下内容是项目约定的本地文件或环境目录，不随仓库发布：

- `.venv/`
  - 本地 Python 虚拟环境。
- `scripts/__pycache__/`
  - Python 缓存文件。
- `tests/__pycache__/`
  - 测试缓存文件。
- `vendor/3gpp/38331-h60.zip`
  - 本地输入归档文件，用于 real 流水线导入；当前默认忽略，不纳入仓库。

## 6. 当前推荐使用方式

如果你只是想快速看当前结果，优先看这些文件：

- `outputs/reports_real/real_ingest.json`
- `outputs/reports_real/*.json`
- `outputs/asn1/validation.json`
- `outputs/runtime/manifest.json`
- `targets/oai/README.md`

如果你想继续开发，优先看这些脚本：

- `scripts/run_real_pipeline.py`
- `scripts/ingest_real_spec.py`
- `scripts/extract_efsm_llm.py`
- `scripts/validate_asn1.py`
- `scripts/build_runtime_bundle.py`

## 7. 后续建议

下一步如果继续往工程化推进，优先级建议如下：

1. 把 real procedure 从当前 3 个扩到更多 `5.3.x` 子过程。
2. 接入真实 model checker，而不是只保留 Promela/NuSMV 导出。
3. 把 runtime 从离线 replay 推到在线 OAI RFSIM 注入。
4. 对 EFSM 提取增加人工 gold set 和回归评估。
5. 把本地输入 `38331-h60.zip` 的准备流程写成明确脚本或下载说明。

## 8. 附录：术语

- `Bootstrap`
  - 指本项目里的轻依赖最小闭环路线，用于先把切片、提取、验证、seed 生成等主流程跑通。

- `Real`
  - 指接入真实 `38.331` 文档、真实 ASN.1 编译和真实 runtime 产物生成的那条路线。

- `Procedure`
  - 指 3GPP 规范中的一个具体协议过程，例如 `RRC connection resume`、`RRC connection establishment`。

- `Slice`
  - 指从原始规范中按 procedure 粒度裁切出来的一段文本，供后续提取、验证和检索使用。

- `Pipeline`
  - 指一条从输入到输出的串行处理流程，例如 `导入 -> 切片 -> 提取 -> 校验 -> 生成产物`。

- `EFSM`
  - `Extended Finite State Machine`，扩展有限状态机。相比普通状态机，多了变量、条件守卫、定时器和动作。

- `Schema`
  - 这里主要指 JSON Schema，用来约束模型输出结构，防止它随意返回不符合格式的内容。

- `Seed`
  - 用于后续变异、回放或测试的基础输入样本。在本项目里通常是从 EFSM 和约束推导出的消息样本。

- `Mutation`
  - 指对 seed 做变异，例如生成 nominal、boundary 之类不同输入，以覆盖不同协议分支。

- `Runtime`
  - 指可实际执行、可被回放或注入目标系统的运行期产物集合，如 seed、PDU、pcap、replay 脚本等。

- `Replay`
  - 指把之前生成的消息或流量样本重新发送给目标系统，用于复现、测试或注入。

- `PDU`
  - `Protocol Data Unit`，协议数据单元。这里通常指经过 ASN.1 编码后的二进制协议消息。

- `pcap`
  - 数据包捕获文件格式。项目中用它保存合成后的网络流量样本，便于离线分析和回放。

- `ASN.1`
  - `Abstract Syntax Notation One`，一种描述协议消息结构的标准表示法。RRC 消息定义大量依赖它。

- `UPER`
  - `Unaligned Packed Encoding Rules`，ASN.1 的一种编码规则。本项目当前用它生成 RRC 相关二进制消息。

- `Roundtrip`
  - 指“编码一次，再解码回来”的往返验证，用来确认 ASN.1 定义和编码逻辑至少在样本层面是自洽的。

- `Codex CLI`
  - 本项目当前用于大模型提取的命令行入口，通过 schema 约束把规范文本转成结构化 EFSM JSON。

- `Promela`
  - 一种用于形式化建模的语言，通常与 `SPIN` 配合使用。本项目当前先导出文本模型。

- `NuSMV`
  - 一种模型检查工具及其输入语言。本项目当前先导出 `.smv` 文本模型，尚未进入完整求解流程。

- `OAI`
  - `OpenAirInterface`，开源移动通信协议栈/实验平台。本项目当前把它当作后续目标系统接入位点。

- `Compose Override`
  - 指额外叠加到基础 `docker-compose.yaml` 之上的覆盖配置，用来挂载 runtime 产物或改写运行参数。

- `Graph`
  - 本项目里主要指 procedure、状态、转移、引用关系的结构化关系图，目前以 SQLite 形式落地。

- `Model Checker`
  - 用于自动检查状态机模型是否满足某些性质的工具，例如是否存在死锁、不可达状态或非法转移。
