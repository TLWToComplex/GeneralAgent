# 模型服务（GPU 版）— Docker 一键部署指南

> **适用环境：** Ubuntu 22.04 LTS（x86_64 / ARM64）｜ Docker 29.1.0+ / Compose v2.40.0+ ｜ NVIDIA GPU（建议 ≥ 6 张）  
> **最后更新：** 2026-09-16  
> 本包为整体部署四部分之一（**GA-app / model-service / llm-ops / langfuse**），用 **一个 compose** 编排 5 个服务：大语言模型、向量模型、重排模型、MinerU 文档解析（以上 4 个为 GPU 推理服务）与 FunASR 语音识别（CPU）。**完全独立部署**，与 GA 应用系统通过 HTTP / websocket 对接，互不影响。

---

> [!IMPORTANT]
> **本部署包同时支持 x86_64 与 ARM64（aarch64）两种架构**：部署/卸载脚本通过 `uname -m` 自动识别架构，自动选择 compose 文件（x86 → `docker-compose.yml`，ARM64 → `docker-compose.arm64.yml`，后者每个服务已固定 `platform: linux/arm64`）与镜像 tar（x86 → `*.tar`，ARM64 → `*-arm64.tar`，导入后镜像标签一致），非 x86_64/aarch64 架构直接报错退出。  
> **ARM64 + NVIDIA GPU（Grace-Hopper / Jetson 等）注意**：nvidia-container-toolkit 与 compose 的 GPU 预留语法和 x86 完全一致；但 **vLLM / MinerU / FunASR 的 arm64+CUDA 镜像官方发布较少，通常需自行构建**。

## 一、部署包清单

```
model-service/
├── docker-compose.yml        # 5 个服务编排（4 GPU + 1 CPU，x86_64）
├── docker-compose.arm64.yml  # 同上，ARM64（platform: linux/arm64）
├── import-and-start.sh       # 一键部署脚本（自动识别架构）
├── uninstall-and-clean.sh    # 一键卸载脚本（自动识别架构）
├── deployment_guide.md       # 本文档
├── mineru/mineru.json        # MinerU 配置（脚本自动分发到 /data/mineru/）
└── images/                   # x86 用 *.tar，ARM64 用 *-arm64.tar
    ├── mineru                     # MinerU GPU 版镜像
    ├── vllm-openai-v0.20.0        # llm + embedding + reranker（共用）
    └── funasr                     # funasr 语音识别（ASR）镜像
```

## 二、服务、端口与 GPU 分配

| 服务（容器名） | 模型 | 镜像 | 宿主机端口 | 接口 | GPU(device_ids) |
|----------------|------|------|-----------|------|-----------------|
| llm（vllm-qwen3.8-27b） | Qwen3.8-27B | `vllm/vllm-openai:v0.20.0` | **8666** | `/v1`（OpenAI 兼容） | **0,1,2,3**（张量并行 4 卡） |
| embedding（Qwen3-Embedding-4B） | Qwen3-Embedding-4B | `vllm/vllm-openai:v0.20.0` | **6667** | `/v1` | **4** |
| reranker（Qwen3-Reranker-4B） | Qwen3-Reranker-4B | `vllm/vllm-openai:v0.20.0` | **6657** | `/v1` | **4**（与 embedding 共卡） |
| mineru-router | MinerU | `mineru:latest` | **18002** | `/health`、`/file_parse` | **5** |
| funasr（funasr-online-server） | FunASR | `funasr:20260520` | **10095 / 10096** | websocket（语音识别 ASR） | 无（CPU 推理） |

> GPU 6、7 预留空闲。如服务器 GPU 数量/编号不同，请修改对应架构的 compose 文件（`docker-compose.yml` / `docker-compose.arm64.yml`）中各服务的 `device_ids`（llm 的卡数需与 `--tensor-parallel-size` 一致）。
> funasr 默认不占用 GPU（CPU 推理），不影响「≥ 6 张卡」的硬性要求；如需 GPU 加速可在该服务下自行添加 `deploy.resources.reservations.devices`。

各服务模型名称（`served-model-name`）：`qwen3.8-27b` / `Qwen3-Embedding-4B` / `Qwen3-Reranker-4B`。

## 三、部署前提

1. **NVIDIA GPU + 驱动**：`nvidia-smi` 可正常输出（脚本硬性检查，无 GPU 直接报错退出）；默认编排需 ≥ 6 张卡。
2. **nvidia-container-toolkit**（容器内使用 GPU 的必要组件）：
   ```bash
   sudo apt-get install -y nvidia-container-toolkit
   sudo nvidia-ctk runtime configure --runtime=docker
   sudo systemctl restart docker
   ```
3. **模型文件**（体积大，不随部署包分发，需提前放到对应宿主机目录，脚本会逐一检查是否齐全非空）：

   | 服务 | 模型目录（宿主机） |
   |------|-------------------|
   | llm | `/data/llm/model/Qwen3.8-27B/` |
   | embedding | `/data/embedding/model/Qwen3-Embedding-4B/` |
   | reranker | `/data/reranker/model/Qwen3-Reranker-4B/` |
   | mineru | `/data/mineru/models/PDF-Extract-Kit-1___0/` 与 `/data/mineru/models/MinerU2___5-Pro-2604-1___2B/` |
   | funasr | `/data/funasr/models/` |

   > MinerU 模型可在有网环境执行 `mineru-models-download -s modelscope -m all` 下载后拷贝到服务器。
   > FunASR 模型（语音识别 ASR）需提前放到 `/data/funasr/models/`，挂载到容器内 `/workspace/models`。

## 四、部署步骤

### 步骤 1：传输部署包与模型

```bash
ssh user@your-server "mkdir -p /data/deploy/model-service/images \
  /data/llm/model /data/embedding/model /data/reranker/model /data/mineru/models /data/funasr/models"

# 脚本 + 配置 + 镜像
scp -r model-service/* user@your-server:/data/deploy/model-service/

# 各模型（按上表放到对应目录）
scp -r <本地>/Qwen3.8-27B          user@your-server:/data/llm/model/
scp -r <本地>/Qwen3-Embedding-4B   user@your-server:/data/embedding/model/
scp -r <本地>/Qwen3-Reranker-4B    user@your-server:/data/reranker/model/
scp -r <本地>/{PDF-Extract-Kit-1___0,MinerU2___5-Pro-2604-1___2B} user@your-server:/data/mineru/models/
scp -r <本地>/funasr-models/*       user@your-server:/data/funasr/models/
```

### 步骤 2：执行一键部署

```bash
cd /data/deploy/model-service
sudo bash import-and-start.sh
```

脚本自动完成（5 步）：

| 步骤 | 操作 |
|------|------|
| 1/5 | 环境检查：**架构识别（选择 compose 文件与 tar 后缀）**/ root / Docker / Compose / **GPU 与 nvidia 运行时（缺失即报错退出）** / GPU 数量 ≥ 6 / 端口（8666,6667,6657,18002,10095,10096）占用 |
| 2/5 | 创建数据目录 + 分发 `mineru.json`（已存在保留不覆盖）+ **逐一检查 6 个模型目录完整性** |
| 3/5 | 导入 3 个对应架构的镜像 tar 并统一打标签（本地已有镜像自动跳过；llm/embedding/reranker 共用 vllm-openai:v0.20.0） |
| 4/5 | `docker compose up -d` 启动 5 个服务（自动使用对应架构的 compose 文件） |
| 5/5 | 轮询各 GPU 服务 `/health` 等待就绪（27B 张量并行加载较慢，最长等待 20 分钟）；funasr 为 websocket 服务无 HTTP 健康端点，仅随 `docker compose ps` 确认 running |

### 步骤 3：验证部署

```bash
docker compose ps                              # 5 个服务应为 running / healthy
curl http://localhost:8666/health              # llm
curl http://localhost:6667/health              # embedding
curl http://localhost:6657/health              # reranker
curl http://localhost:18002/health             # mineru-router
docker compose logs -f funasr                  # funasr（websocket，无 HTTP 健康端点，看日志确认监听 10095）
docker compose logs -f llm                     # 查看日志
```

> funasr 为 websocket 服务，不能用 `curl /health` 探测；用 `docker compose ps` 确认 `funasr-online-server` 为 running，并查看其日志确认 10095/10096 端口已监听。

llm 接口连通性测试：

```bash
curl http://localhost:8666/v1/chat/completions -H "Content-Type: application/json" -d '{
  "model": "qwen3.8-27b",
  "messages": [{"role": "user", "content": "你好，介绍一下你自己"}],
  "temperature": 0.7, "max_tokens": 1024, "stream": false,
  "chat_template_kwargs": {"enable_thinking": false}
}'
```

### 步骤 4：接入 GA 应用系统（可选）

**① 模型平台**——编辑 `/data/GA-kb-chat/kb_config.yaml` 的 `MODEL_PLATFORMS`，将 `api_base_url` 指向本包：

| 用途 | api_base_url | 模型名 |
|------|--------------|--------|
| LLM / KG-LLM | `http://<服务器IP>:8666/v1` | `qwen3.8-27b` |
| Embedding | `http://<服务器IP>:6667/v1` | `Qwen3-Embedding-4B` |
| Rerank | `http://<服务器IP>:6657/v1` | `Qwen3-Reranker-4B` |

> 业务后端 `/data/GA-service-backend/config.yaml` 中 `travel_planner.llm.api_base_url` 等如需使用本地大模型，同样指向 `http://<服务器IP>:8666/v1`。

**② MinerU 文档解析**——解析链路为 **kb-chat → ai-doc-processor(`:18200/api/parse_to_markdown`) → mineru-router(`:18002`)**，需配置两处：

```yaml
# /data/GA-document-processor/config.yaml
mineru:
  base_url: "http://<服务器IP>:18002"
```
```yaml
# /data/GA-kb-chat/kb_config.yaml
ENABLE_MINERU: true
MINERU_URL: http://<服务器IP>:18200/api/parse_to_markdown
```

重启相关服务：

```bash
cd <GA-app部署目录>
docker compose restart app-ai-doc-processor app-GA-kb-chat
```

## 五、配置说明

### MinerU `/data/mineru/mineru.json`

| 配置项 | 说明 |
|--------|------|
| `models-dir.pipeline` / `models-dir.vlm` | 容器内模型路径（`/models/...`，与 volume 挂载对应，一般无需修改） |
| `bucket_info` | 如需 S3 存储则填写，否则留空 |
| `llm-aided-config.title_aided` | LLM 辅助标题识别，当前文件解析流程不需要，保持 `enable: false` |

### vLLM 服务（llm / embedding / reranker）关键参数（在对应架构 compose 文件的 `command` 中，两份建议同步修改）

| 参数 | 说明 |
|------|------|
| `--tensor-parallel-size 4` | 仅 llm：张量并行卡数，**必须与 `device_ids` 卡数一致** |
| `--gpu-memory-utilization` | 显存占比（llm 0.9；emb/rer 0.45，共卡时两者之和需 ≤ 1） |
| `--max-model-len 262144` | 仅 llm：最大上下文长度，显存不足时调小 |
| `--max-num-seqs 16` | 仅 embedding：并发序列数 |
| `device_ids` | 各服务占用的 GPU 编号，按实际服务器调整 |

修改后执行 `docker compose up -d` 重建生效。

### FunASR 语音识别（funasr）

| 配置项 | 说明 |
|--------|------|
| 模型目录 | 宿主机 `/data/funasr/models` 挂载到容器 `/workspace/models`，模型需提前放好 |
| `FUNASR_OFFLINE=1` | 以离线（非在线流式）模式运行；按需调整 |
| 端口 | `10095`（websocket 服务端口）、`10096`（备用端口） |
| GPU | 默认 CPU 推理；如需 GPU 加速，在 compose 的 funasr 服务下添加 `deploy.resources.reservations.devices`（参照其它服务写法） |

## 六、常用运维命令

```bash
cd /data/deploy/model-service
# ARM64 服务器请为下列 docker compose 命令追加 -f docker-compose.arm64.yml（下同）

docker compose ps                          # 查看状态
docker compose logs -f <服务名>            # 查看日志（llm/embedding/reranker/mineru-router/funasr）
docker compose restart <服务名>            # 重启单个服务
docker compose down                        # 停止全部（模型与配置保留）
docker compose up -d                       # 重新启动

# 更新某个镜像：
docker load -i images/<镜像>.tar
docker tag <原始镜像名:标签> <目标镜像名:标签>   # 名称不一致时
docker compose up -d --force-recreate --no-deps <服务名>
```

## 七、一键卸载

```bash
cd /data/deploy/model-service
sudo bash uninstall-and-clean.sh
```

| 步骤 | 操作 | 确认方式 |
|------|------|---------|
| 1/5 | 停止并删除 5 个服务容器 | 首次统一确认 |
| 2/5 | 删除 mineru / vllm-openai / funasr 镜像 | 自动执行 |
| 3/5 | 清理 Docker 网络 | 自动执行 |
| 4/5 | 删除 `/data/{llm,embedding,reranker,mineru,funasr}`（**含模型文件**；计划重装复用时选 N 跳过） | **二次确认** ⚠ |
| 5/5 | Docker 系统级深度清理（作用于整个 Docker，共用服务器时谨慎） | **二次确认** ⚠ |

> 卸载脚本只清理本模型服务栈，不影响 GA 应用系统与 Langfuse。

## 八、常见问题

**Q1: 启动报错 `could not select hardware driver for this capabilities`**  
未安装 nvidia-container-toolkit 或安装后未重启 Docker，按「部署前提」第 2 条处理。

**Q2: llm 起不来 / 报张量并行相关错误**  
`--tensor-parallel-size` 必须等于 `device_ids` 中的卡数（默认 4）；确认这 4 张卡空闲且显存足够（27B + 262144 上下文占用较高，不足时调小 `--max-model-len` 或 `--gpu-memory-utilization`）。

**Q3: embedding 与 reranker 共用 GPU4 显存不足 (CUDA out of memory)**  
两者各占 `--gpu-memory-utilization 0.45`；仍不足时把其中一个迁到空闲卡（如 `device_ids: ["6"]`），或降低占比。

**Q4: 容器 running 但 /health 一直不通**  
首次启动需加载模型（llm 可达数分钟）；超时查看 `docker compose logs -f <服务名>`，常见原因为模型目录缺失/路径不符。

**Q5: 与 GA 应用系统有依赖吗？**  
没有。本包独立运行；应用系统通过 HTTP 单向调用（模型 8666/6667/6657、解析 18002），本包不可用时应用系统其余功能不受影响。

**Q6: funasr 怎么用 / 为什么 curl 不通？**  
funasr 是 websocket 语音识别服务（端口 10095/10096），没有 HTTP `/health` 端点，`curl` 探测不通属正常。用 `docker compose ps` 确认 `funasr-online-server` 为 running、`docker compose logs -f funasr` 确认端口已监听即可；客户端通过 websocket 协议接入。funasr 默认 CPU 推理、不占用 GPU，不影响「≥ 6 张卡」要求。

## 九、参考资料

- vLLM 官方文档：<https://docs.vllm.ai/>
- MinerU 官方文档：<https://opendatalab.github.io/MinerU/zh/>
