# OAI 接入说明

这一版已经不再只是“交接说明”。
真实流水线会直接生成本项目自己的 runtime bundle，位置在：

- `outputs/runtime/seeds/`
- `outputs/runtime/pdus/`
- `outputs/runtime/pcaps/`
- `outputs/runtime/oai/docker-compose.runtime.yaml`
- `outputs/runtime/replay_runtime.sh`

## 本项目内的 OAI 资产

这些文件现在直接放在本项目目录里：

- `/home/huazi4ai/3gpp-protocol-lab/targets/oai/docker-compose.yaml`
- `/home/huazi4ai/3gpp-protocol-lab/targets/oai/mini_nonrf_config.yaml`
- `/home/huazi4ai/3gpp-protocol-lab/targets/oai/gnb.sa.band78.106prb.rfsim.conf`
- `/home/huazi4ai/3gpp-protocol-lab/targets/oai/nrue.uicc.conf`
- `/home/huazi4ai/3gpp-protocol-lab/targets/oai/oai_db.sql`
- `/home/huazi4ai/3gpp-protocol-lab/targets/oai/mysql-healthcheck.sh`

## 当前映射关系

1. `outputs/efsm_real/*.json`
   - 作为真实 procedure 的状态与分支抽象。
2. `outputs/runtime/seeds/*.json`
   - 作为消息级 fuzz 输入与 mutation class 描述。
3. `outputs/runtime/pdus/*.uper.bin`
   - 作为真实 ASN.1 编码后的 UE 侧消息样本。
4. `outputs/runtime/pcaps/*.pcap`
   - 作为项目内自生成的离线载荷样本。
5. `outputs/runtime/oai/docker-compose.runtime.yaml`
   - 作为挂载 runtime bundle 的 compose override。
6. `scripts/send_runtime_pdu.py`
   - 作为项目内 UDP PDU 注入器。

## 推荐执行方式

1. 先验证 compose：

```bash
docker compose \
  -f /home/huazi4ai/3gpp-protocol-lab/targets/oai/docker-compose.yaml \
  -f /home/huazi4ai/3gpp-protocol-lab/outputs/runtime/oai/docker-compose.runtime.yaml \
  config --quiet
```

2. 用 UDP PDU 注入器先验证生成的 `.uper.bin`：

```bash
/home/huazi4ai/3gpp-protocol-lab/outputs/runtime/replay_runtime.sh \
  /home/huazi4ai/3gpp-protocol-lab/outputs/runtime/pdus/<your-file>.uper.bin
```

## 当前边界

- 当前生成的是“真实输入物 + 独立注入路径”，不是强耦合在线注入器。
- `RRCSetupRequest` 和 `RRCResumeRequest` 都能落为真实 UPER PDU，并进一步封装成项目内自生成的 UDP/pcap 载荷。
- 本项目不再依赖任何外部 sibling 工程目录。
