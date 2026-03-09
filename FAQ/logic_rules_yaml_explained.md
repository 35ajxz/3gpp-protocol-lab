# logic_rules.yaml 功能、产生原理与可信性说明

## 问题

详细解释下 `logic_rules.yaml` 文件功能，以及它的产生过程或原理，你怎么保障它的准确性和全面性的？

## 回答

`logic_rules.yaml` 本质上是这个工程里的“协议逻辑测试规则库”。

它不负责提取状态机，也不负责真正执行目标系统；它负责把“要怎么测、什么算错”明确写出来，供逻辑漏洞测试引擎消费。

核心文件是：

- `constraints/logic_rules.yaml`
- `scripts/logic_fuzz.py`
- `scripts/run_logic_campaign.py`

### 它具体干什么

`logic_rules.yaml` 主要定义 4 类东西：

- `initial_state`
  这个过程从哪个协议状态开始执行。比如 `5.3.3` 从 `RRC_IDLE` 开始，`5.3.13` 从 `RRC_INACTIVE` 开始。

- `scenarios`
  定义“基准正确流程”。比如 `resume_nominal` 先发起恢复请求，再启动恢复过程，再接收 `RRCResume`。

- `invariants`
  定义“逻辑上不该错的约束”，也就是判定规则。比如：
  - 进入 `RRC_CONNECTED` 前，必须真的收到了 `RRCResume`
  - 收到 `RRCResume` 后，`T319`/`T319a` 应该被清掉
  - `RRCSetup` 过程里不该接受 `RRCResume`

- `perturbations`
  定义怎么把正确流程扰动成异常序列，比如：
  - 重复最后一步
  - 把最后一步提前到最前面
  - 删除最后一步
  - 在最后一步前插入超时事件
  - 把最后一步换成跨过程消息

所以它的定位不是“协议状态机本体”，而是“围绕状态机做逻辑攻击和判定的规则层”。

### 它是怎么被使用的

执行链路在 `scripts/logic_fuzz.py` 里，流程是：

1. 从 `outputs/efsm_real` 读取真实 EFSM。
2. 从 `constraints/logic_rules.yaml` 读取过程规则。
3. 用 `scenarios` 生成基准用例。
4. 用 `perturbations` 批量生成异常序列。
5. 让 `reference_model` 和 `candidate_target` 分别执行同一批序列。
6. 用 `invariants` 和“参考结果 vs 候选结果”的差异做判定。
7. 输出：
   - `outputs/logic/summary.json`
   - `outputs/logic/findings.json`
   - `outputs/logic/traces`

你可以把它理解成：

- EFSM 回答“协议大概怎么走”
- `logic_rules.yaml` 回答“该从哪里起步、该怎么扰动、什么算漏洞”

### 它的产生过程和原理

这文件不是凭空手写的，也不是完全自动生成的。当前这版是“真实 EFSM 为底，人工固化逻辑规则”的做法。

来源链路是：

1. 真实规范切片  
   比如 `corpus/real/slices/5.3.13-rrc-connection-resume.md`

2. 用 Codex 按 schema 提取 EFSM  
   逻辑在 `scripts/extract_efsm_llm.py`

3. 产出真实 EFSM  
   比如 `outputs/efsm_real/5.3.13-rrc-connection-resume.json`

4. 对 EFSM 做结构和覆盖校验  
   比如 `outputs/reports_real/5.3.13-rrc-connection-resume.json`

5. 在这个 EFSM 基础上，人工提炼出：
   - 正常场景
   - 关键不变量
   - 典型扰动方式

所以它背后的原理是：

- 用真实规范提取“参考状态机”
- 再把安全研究里最关心的逻辑约束显式写成规则
- 让规则驱动批量序列测试和漏洞判定

这比把逻辑全埋进 Python 代码里更好，因为 YAML 更直观、可审计、可扩展。

### 我怎么保障它的准确性

先说结论：当前只能说“有依据、可审计、有限可靠”，不能说“完全保证”。

当前准确性主要靠这几层：

- 规则不是脱离规范乱写的，而是锚定在真实 EFSM 上。  
  比如 `5.3.13` 的 `receive(RRCResume)`、`T319`、`T319a`、`RRC_CONNECTED` 都能在 `outputs/efsm_real/5.3.13-rrc-connection-resume.json` 里对上。

- EFSM 本身先过一轮校验。  
  `scripts/validate_efsm_real.py` 会检查结构、步骤顺序、消息/定时器/变量在原文里的覆盖情况。

- 规则类型是显式且有限的。  
  当前只支持几种明确语义：
  - `require_history_event`
  - `forbid_event`
  - `require_state_after_event`
  - `forbid_state_after_event`
  - `require_timer_cleared`
  - `require_guard_for_final_state`
  这比自由文本判定更稳定。

- 每条异常都有轨迹可回看。  
  不是只给一个 `pass/fail`，而是会落盘到 `outputs/logic/traces` 里，能看每一步前后状态、是否接受、命中了哪条规则。

- 回归测试至少保证链路没漂。  
  `tests/test_logic_campaign.py` 会检查用例数量和关键发现类型。

### 我怎么保障它的全面性

严格说，现在还谈不上“全面保障”。这点要说实话。

当前明显的边界是：

- 只覆盖了 `5.3.3` 和 `5.3.13` 两个过程。
- 每个过程只定义了一个 `nominal` 场景。
- `invariants` 只覆盖了最关键的连接进入、消息接受、定时器清理、异常失败，不是全量协议语义。
- `candidate_target` 还是 `scripts/logic_fuzz.py` 里的人造宽松目标，不是真实 OAI 适配器。
- 规则里还没有给每条不变量显式挂 3GPP 条款号，这会影响审计性。

所以现在这份 YAML 的定位更准确地说是：

- 不是“完整协议规范”
- 而是“第一版可执行的逻辑漏洞测试规则集”

### 如果要把准确性和全面性再抬高，我会这样补

- 给每条 `invariant` 增加 `refs`，直接绑定到具体 clause。
- 给每个过程增加多条 `nominal` 场景，而不是只保留一条主路径。
- 做“规则覆盖率”报告：看 EFSM 的状态、转移、定时器、消息有多少被规则覆盖到。
- 引入人工审阅清单：每个过程至少核对“进入条件、成功条件、失败条件、超时条件、跨过程混淆”五类规则。
- 把 `candidate_target` 换成真实目标适配器，再看真实偏差，不只看模拟偏差。

### 一句话总结

`logic_rules.yaml` 不是协议状态机本身，而是建立在真实 EFSM 之上的“逻辑测试规则层”。

它当前的强项是显式、可读、可执行、可追溯；短板是覆盖面还窄，离“完备规则库”还有距离。
