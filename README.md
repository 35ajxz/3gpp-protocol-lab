# 3GPP Protocol Lab

这是一个面向 `TS 38.331 Rel-17` 的本地协议分析与模糊测试实验工程。
当前独立工程根目录固定为 `/home/huazi4ai/3gpp-protocol-lab`，不再依赖任何外部 sibling 项目。
它现在同时包含两条流水线：

- `bootstrap`：当天可跑通的轻依赖本地骨架。
- `real`：接入真实 `38.331` 文档、Codex 提取、ASN.1 编译与项目内独立 OAI/runtime bundle。

## 当前已经落地的能力

`bootstrap` 流水线：
- 基于本地 Markdown fixture 的 procedure 切片
- 基于受限 transition DSL 的确定性 EFSM 抽取
- 结构校验、术语覆盖、引用闭包校验
- 本地检索、SQLite 图谱、Promela/NuSMV 导出
- 属性检查、路径规划、Mermaid 图导出
- 语义 seed 生成

`real` 流水线：
- 从下载到本机的 `38331-h60.zip` 中解析真实 `.docx`
- 生成真实规范 Markdown 与真实 procedure slices
- 用 `codex exec --output-schema` 对真实章节做结构化 EFSM 抽取
- 从规范中抽取 `NR-RRC-Definitions`，并用 `asn1tools` 编译
- 对 `RRCSetupRequest`、`RRCResumeRequest` 做真实 UPER 编解码往返校验
- 基于真实 EFSM 生成 runtime seeds、UPER PDU 和项目内自生成 pcap
- 生成独立 OAI compose override 与项目内 UDP PDU 注入脚本

## 目录结构

```text
3gpp-protocol-lab/
├── corpus/
│   ├── raw/                         # bootstrap 原始语料
│   ├── slices/                      # bootstrap procedure 切片
│   └── real/
│       ├── raw/                     # 从 38.331 docx 归一化出的真实 Markdown
│       └── slices/                  # 真实 procedure 切片
├── constraints/                     # seed 字段约束
├── docs/                            # 中文项目说明
├── outputs/
│   ├── efsm/                        # bootstrap EFSM
│   ├── efsm_real/                   # Codex 提取的真实 EFSM
│   ├── reports/                     # bootstrap 校验报告
│   ├── reports_real/                # 真实 EFSM 校验报告
│   ├── asn1/                        # 真实 ASN.1 与编译校验结果
│   └── runtime/                     # runtime seeds / pdu / pcap / OAI override
├── schemas/                         # EFSM schema
├── scripts/                         # 全部流水线脚本
├── targets/
│   └── oai/                         # 项目内独立 OAI 接入说明与配置
└── tests/                           # bootstrap 烟测
```

## 快速开始

运行 bootstrap 流水线：

```bash
cd /home/huazi4ai/3gpp-protocol-lab
python3 scripts/run_pipeline.py
```

运行真实流水线：

```bash
cd /home/huazi4ai/3gpp-protocol-lab
.venv/bin/python scripts/run_real_pipeline.py
```

运行 bootstrap 测试：

```bash
cd /home/huazi4ai/3gpp-protocol-lab
python3 -m unittest discover -s tests
```

## 当前覆盖的真实 procedure

- `5.3.3` RRC connection establishment
- `5.3.5.11` full configuration procedure
- `5.3.13` RRC connection resume

真实流水线不会再依赖人工写好的 transition DSL。
它直接从 `38.331 V17.6.0` 文档切片，再由 Codex 输出与本工程 EFSM 兼容的 JSON。

## 关键输出

运行 `run_pipeline.py` 后会得到：
- `outputs/efsm/*.json`
- `outputs/reports/*.json`
- `outputs/retrieval/*.json`
- `outputs/graph/3gpp_lab.sqlite`
- `outputs/formal/promela/*.pml`
- `outputs/formal/nusmv/*.smv`
- `outputs/properties/*.json`
- `outputs/paths/*.json`
- `outputs/mermaid/*.mmd`
- `outputs/seeds/*.json`

运行 `run_real_pipeline.py` 后会额外得到：
- `corpus/real/raw/ts-38.331-v17.6.0.md`
- `corpus/real/slices/*.md`
- `outputs/efsm_real/*.json`
- `outputs/reports_real/*.json`
- `outputs/asn1/NR-RRC-Definitions.asn1`
- `outputs/asn1/validation.json`
- `outputs/runtime/seeds/*.json`
- `outputs/runtime/pdus/*.uper.bin`
- `outputs/runtime/pcaps/*.pcap`
- `outputs/runtime/oai/docker-compose.runtime.yaml`
- `outputs/runtime/replay_runtime.sh`

## 运行约束

- 真实流水线依赖本机已经登录的 `codex` CLI。
- `ASN.1` 与 `pcap` 相关脚本使用项目内 `.venv`。
- 当前 runtime 仍以离线 replay / pcap 变异为主，没有强行把整套 OAI RFSIM 全栈拉起。
- 当前 runtime 完全自包含，不依赖其他外部 sibling 项目。
- GraphRAG / MCP 暂时没有接入，这一版优先把真实协议资产和 runtime 输入物做实。
