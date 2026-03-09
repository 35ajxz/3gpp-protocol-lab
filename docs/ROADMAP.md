# 当天压缩版路线图

这个工程原本按 6 周拆分，现在被压成了同一天内可执行的两层实现。

## 第一层：bootstrap 骨架

1. 语料导入：先使用本地 Markdown fixture。
2. procedure 切片：按 `5.3.x` 粒度切出章节。
3. EFSM schema：先把唯一中间表示定死。
4. 抽取：使用确定性 transition parser。
5. 校验：做结构、术语覆盖、引用闭包。
6. 检索：先用本地 query ranking。
7. 图谱：先落 SQLite。
8. 形式化导出：先生成 Promela/NuSMV 文本。
9. 属性检查：先做基于图的 reachability / dead-end 检查。
10. 覆盖规划：先做 transition / 2-switch path。
11. 可视化：导出 Mermaid。
12. seed：生成语义化 JSON seeds。

## 第二层：真实协议能力

1. 真实文档导入：从 `38331-h60.zip` 解析 `.docx`。
2. 真实切片：产出 `5.3.3`、`5.3.5.11`、`5.3.13` 的真实 slices。
3. 模型抽取：用 `codex exec --output-schema` 输出真实 EFSM JSON。
4. ASN.1 抽取：从规范正文抽出 `NR-RRC-Definitions`。
5. ASN.1 编译：用 `asn1tools` 编译并做 `RRCSetupRequest`、`RRCResumeRequest` 往返校验。
6. runtime bundle：把真实 EFSM 转成 seeds、UPER PDU、pcap 变异产物和 OAI override。

## 当前状态

已完成：
- bootstrap 全链路
- 真实 `38.331` 文档接入
- Codex 真实抽取链路
- 真实 ASN.1 编译链路
- 独立 OAI/runtime bundle 产物链路
- 新独立工程根目录 `/home/huazi4ai/3gpp-protocol-lab`

仍然保留的边界：
- 还没有强制把整套 OAI RFSIM 在线跑起来
- GraphRAG / MCP 仍然未接入
- 形式化验证目前仍以文本导出和图检查为主，没有外部模型检查器实跑
- 为保证独立性，这一版不再与任何外部 sibling 项目建立路径或运行时耦合
