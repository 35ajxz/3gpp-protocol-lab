# 3GPP Protocol Lab

一个面向 `TS 38.331 Rel-17` 的独立 3GPP 协议分析与模糊测试实验工程。  
当前工程根目录为 `/home/huazi4ai/3gpp-protocol-lab`，不依赖外部 sibling 项目。

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

- 语言与脚本编排：`Python 3`
  - 用于绝大多数数据处理、切片、验证、runtime 生成逻辑。
- LLM 提取：`Codex CLI`
  - 通过 `codex exec --output-schema` 输出 schema 约束的 EFSM JSON。
- ASN.1 编译与编码验证：`asn1tools`
  - 用于编译 `NR-RRC-Definitions` 并做 `UPER` 编解码 roundtrip。
- pcap 生成：`Scapy`
  - 用于把 runtime PDU 封装成项目内合成的 UDP/pcap 样本。
- 图谱存储：`SQLite`
  - 用于 bootstrap 流水线的本地结构化查询与关系整理。
- 形式化导出：`Promela / NuSMV` 文本导出
  - 当前先导出模型文件和图属性检查结果，尚未接外部 model checker 实跑。
- OAI 接入：项目内 `targets/oai/*`
  - 当前以 compose override 和离线 replay 为主，不强绑外部工程。

### 2.2 整体架构

下面是当前工程的主干架构，使用 ASCII 文本表示：

```text
+--------------------------------------------------------------+
|                    3GPP Protocol Lab                         |
+--------------------------------------------------------------+

  Bootstrap 路线
  ---------------
  corpus/raw/*.md
         |
         v
  scripts/slice_procedures.py
         |
         v
  corpus/slices/*.md
         |
         v
  scripts/extract_efsm.py
         |
         v
  outputs/efsm/*.json
         |
         +--> scripts/validate_efsm.py ------> outputs/reports/*.json
         +--> scripts/retrieve.py -----------> outputs/retrieval/*.json
         +--> scripts/build_graph.py --------> outputs/graph/3gpp_lab.sqlite
         +--> scripts/export_formal.py ------> outputs/formal/promela/*.pml
         |                                    outputs/formal/nusmv/*.smv
         +--> scripts/check_properties.py ---> outputs/properties/*.json
         +--> scripts/generate_paths.py -----> outputs/paths/*.json
         +--> scripts/render_mermaid.py -----> outputs/mermaid/*.mmd
         +--> scripts/generate_seeds.py -----> outputs/seeds/*.json

  Real 路线
  ---------
  vendor/3gpp/38331-h60.zip   (本地输入，默认不纳入版本控制)
         |
         v
  scripts/ingest_real_spec.py
         |
         +--> corpus/real/raw/ts-38.331-v17.6.0.md
         +--> corpus/real/slices/*.md
         +--> outputs/reports_real/real_ingest.json
         |
         +--> scripts/extract_asn1.py --------> outputs/asn1/NR-RRC-Definitions.asn1
         |    scripts/validate_asn1.py -------> outputs/asn1/validation.json
         |
         +--> scripts/extract_efsm_llm.py ----> outputs/efsm_real/*.json
         |    scripts/validate_efsm_real.py --> outputs/reports_real/*.json
         |
         +--> scripts/build_runtime_bundle.py -> outputs/runtime/seeds/*.json
                                                outputs/runtime/pdus/*.uper.bin
                                                outputs/runtime/pcaps/*.pcap
                                                outputs/runtime/oai/docker-compose.runtime.yaml
                                                outputs/runtime/replay_runtime.sh
                                                outputs/runtime/manifest.json
```

### 2.3 核心执行入口

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
cd /home/huazi4ai/3gpp-protocol-lab
make venv
```

或手工执行：

```bash
cd /home/huazi4ai/3gpp-protocol-lab
python3 -m venv .venv
.venv/bin/pip install pyyaml asn1tools scapy
```

### 4.2 运行 bootstrap 流水线

```bash
cd /home/huazi4ai/3gpp-protocol-lab
python3 scripts/run_pipeline.py
```

### 4.3 运行真实流水线

前提：

- 本机已有 `codex` CLI 且已登录。
- 本地存在 `vendor/3gpp/38331-h60.zip`。

执行：

```bash
cd /home/huazi4ai/3gpp-protocol-lab
.venv/bin/python scripts/run_real_pipeline.py
```

### 4.4 运行测试

```bash
cd /home/huazi4ai/3gpp-protocol-lab
python3 -m unittest discover -s tests
```

## 5. 项目文件目录详细说明

说明：

- 下列清单覆盖当前仓库已纳入版本控制的全部叶子文件。
- `.git/`、`.venv/`、`__pycache__/` 属于 Git 或本地环境/缓存目录，不在正文中逐项展开。
- 最后一节补充了项目约定的本地忽略文件。

```text
3gpp-protocol-lab/
├── .gitignore
├── Makefile
├── README.md
├── constraints/
│   ├── messages.yaml
│   └── properties.yaml
├── corpus/
│   ├── raw/
│   │   └── ts-38.331-rel17-bootstrap.md
│   ├── real/
│   │   ├── raw/
│   │   │   └── ts-38.331-v17.6.0.md
│   │   └── slices/
│   │       ├── 5.3.13-rrc-connection-resume.md
│   │       ├── 5.3.3-rrc-connection-establishment.md
│   │       └── 5.3.5.11-full-configuration.md
│   └── slices/
│       ├── 5.3.13-rrc-connection-resume.md
│       ├── 5.3.3-rrc-connection-establishment.md
│       └── 5.3.5.11-full-configuration-procedure.md
├── docs/
│   └── ROADMAP.md
├── outputs/
│   ├── asn1/
│   │   ├── NR-RRC-Definitions.asn1
│   │   ├── NR-RRC-Definitions.meta.json
│   │   ├── validation.json
│   │   └── pdus/
│   │       ├── resume_request_boundary.uper.bin
│   │       ├── resume_request_nominal.uper.bin
│   │       ├── setup_request_boundary.uper.bin
│   │       └── setup_request_nominal.uper.bin
│   ├── efsm/
│   │   ├── 5.3.13-rrc-connection-resume.json
│   │   ├── 5.3.3-rrc-connection-establishment.json
│   │   └── 5.3.5.11-full-configuration-procedure.json
│   ├── efsm_real/
│   │   ├── 5.3.13-rrc-connection-resume.json
│   │   ├── 5.3.3-rrc-connection-establishment.json
│   │   └── 5.3.5.11-full-configuration.json
│   ├── formal/
│   │   ├── nusmv/
│   │   │   ├── 5.3.13-rrc-connection-resume.smv
│   │   │   ├── 5.3.3-rrc-connection-establishment.smv
│   │   │   └── 5.3.5.11-full-configuration-procedure.smv
│   │   └── promela/
│   │       ├── 5.3.13-rrc-connection-resume.pml
│   │       ├── 5.3.3-rrc-connection-establishment.pml
│   │       └── 5.3.5.11-full-configuration-procedure.pml
│   ├── graph/
│   │   └── 3gpp_lab.sqlite
│   ├── mermaid/
│   │   ├── 5.3.13-rrc-connection-resume.mmd
│   │   ├── 5.3.3-rrc-connection-establishment.mmd
│   │   └── 5.3.5.11-full-configuration-procedure.mmd
│   ├── paths/
│   │   ├── 5.3.13-rrc-connection-resume.json
│   │   ├── 5.3.3-rrc-connection-establishment.json
│   │   └── 5.3.5.11-full-configuration-procedure.json
│   ├── properties/
│   │   ├── 5.3.13-rrc-connection-resume.json
│   │   ├── 5.3.3-rrc-connection-establishment.json
│   │   └── 5.3.5.11-full-configuration-procedure.json
│   ├── reports/
│   │   ├── 5.3.13-rrc-connection-resume.json
│   │   ├── 5.3.3-rrc-connection-establishment.json
│   │   └── 5.3.5.11-full-configuration-procedure.json
│   ├── reports_real/
│   │   ├── 5.3.13-rrc-connection-resume.json
│   │   ├── 5.3.3-rrc-connection-establishment.json
│   │   ├── 5.3.5.11-full-configuration.json
│   │   └── real_ingest.json
│   ├── retrieval/
│   │   └── last_query.json
│   ├── runtime/
│   │   ├── manifest.json
│   │   ├── replay_runtime.sh
│   │   ├── oai/
│   │   │   └── docker-compose.runtime.yaml
│   │   ├── pcaps/
│   │   │   ├── 5.3.13-step-3-boundary.pcap
│   │   │   ├── 5.3.13-step-3-nominal.pcap
│   │   │   ├── 5.3.3-step-1-boundary.pcap
│   │   │   └── 5.3.3-step-1-nominal.pcap
│   │   ├── pdus/
│   │   │   ├── 5.3.13-step-3-boundary.uper.bin
│   │   │   ├── 5.3.13-step-3-nominal.uper.bin
│   │   │   ├── 5.3.13-step-4-nominal.uper.bin
│   │   │   ├── 5.3.3-step-1-boundary.uper.bin
│   │   │   └── 5.3.3-step-1-nominal.uper.bin
│   │   └── seeds/
│   │       ├── 5.3.13-rrc-connection-resume.json
│   │       ├── 5.3.3-rrc-connection-establishment.json
│   │       └── 5.3.5.11-full-configuration.json
│   └── seeds/
│       ├── 5.3.13-rrc-connection-resume.json
│       ├── 5.3.3-rrc-connection-establishment.json
│       └── 5.3.5.11-full-configuration-procedure.json
├── schemas/
│   ├── efsm.codex.schema.json
│   └── efsm.schema.json
├── scripts/
│   ├── __init__.py
│   ├── build_graph.py
│   ├── build_runtime_bundle.py
│   ├── check_properties.py
│   ├── common.py
│   ├── docx_3gpp.py
│   ├── export_formal.py
│   ├── extract_asn1.py
│   ├── extract_efsm.py
│   ├── extract_efsm_llm.py
│   ├── generate_paths.py
│   ├── generate_seeds.py
│   ├── ingest_real_spec.py
│   ├── render_mermaid.py
│   ├── retrieve.py
│   ├── run_pipeline.py
│   ├── run_real_pipeline.py
│   ├── send_runtime_pdu.py
│   ├── slice_procedures.py
│   ├── validate_asn1.py
│   ├── validate_efsm.py
│   └── validate_efsm_real.py
├── targets/
│   └── oai/
│       ├── README.md
│       ├── docker-compose.yaml
│       ├── gnb.sa.band78.106prb.rfsim.conf
│       ├── mini_nonrf_config.yaml
│       ├── mysql-healthcheck.sh
│       ├── nrue.uicc.conf
│       └── oai_db.sql
└── tests/
    └── test_pipeline.py
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
