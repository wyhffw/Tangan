# 糖安食助 · 开发方案（交给 AI 持续开发用）

> 本文是"糖安食助"项目的唯一开发依据。执行开发的 AI 模型请**从头到尾读完本文**，再按"第 9 节 分阶段任务"顺序推进。
> 每完成一个任务，就在第 9 节对应条目前把 `[ ]` 改成 `[x]`，并在第 13 节"开发日志"追加一行记录。
>
> 2026-10-29 修订：在本仓库从零实现，不复制 `personnal-Agent`；不采用多 Agent；补充营养口径、结构化输出、降级、鉴权库、时区、单位换算和数据版权。

---

## 0. 给执行 AI 的工作守则（必须遵守）

1. **不要修改以下两个目录，也不要从中复制代码当底座**：
   - `D:\javawebworkspace\personnal-Agent`
   - `D:\javawebworkspace\aiops`
   本项目在 `tangan-shizhu` 里从零写。确认后再入库、流式输出这类交互，按本文重新实现。
2. 所有新代码都写在 `D:\javawebworkspace\tangan-shizhu` 中。
3. 运行环境是 Windows + PowerShell：
   - 命令之间用 `;` 连接，**不能用 `&&`**。
   - Python 虚拟环境放在 `backend\.venv`，运行时用 `.\.venv\Scripts\python`。
4. 一次只做一个任务，做完要：
   - 跑通该任务的验收标准（第 9 节每个任务都写了）。
   - 跑 `pytest`（后端）或 `npm run test`（前端），保证全部通过。
   - `git commit`，提交信息格式见第 11 节。
5. 遇到下列情况**停下来问用户**，不要自己猜：
   - 需要 API Key、虚拟机密码等凭据。
   - 虚拟机上的 PostgreSQL / Neo4j 连不上。
   - 需要删除数据、重建数据库。
   - 需要改变本文中已经确定的技术选型。
6. 涉及健康建议的数据（GI 值、禁忌规则、营养素含量）**不能凭空编造数值**。不确定的数值标注 `source: "待核对"`，由用户小组人工核对。
7. 密钥只放 `.env`，`.env` 必须在 `.gitignore` 中；仓库里只提交 `.env.example`。

---

## 1. 项目定位

**一句话**：面向慢病人群（MVP 只做 **2 型糖尿病**）的个性化饮食助手。它根据用户的健康档案和冰箱里现有的食材推荐食谱，并给出**有依据、可解释**的营养说明。

**核心卖点（答辩重点）**：大模型不直接给饮食建议。推荐结果要先经过三层约束，最后才由大模型负责"解释"：

1. **规则引擎**：硬性过滤，例如高 GI 主食、过敏原。
2. **知识图谱**：结构化匹配，例如 疾病 → 推荐/禁忌 → 食材 → 食谱。
3. **RAG**：从权威指南（卫健委《成人糖尿病食养指南（2023 年版）》）中检索依据。
4. **LLM**：只根据给定的食谱 id 和检索片段，生成结构化解释（见第 4.1 节）。营养数字由后端填入。
5. **输出后校验**：核对食谱 id 和引用 id，不从自由文本里抽食材名。

**合规声明**：所有页面和回答末尾都要附上"本系统仅供饮食参考，不能替代医生诊疗建议"。

### 1.1 六大功能模块（来自开题 PPT）

| 编号 | 模块 | MVP 是否包含 |
|---|---|---|
| M1 | 健康档案 | ✅ |
| M2 | 智能食谱推荐 | ✅ |
| M3 | 可解释营养报告 | ✅ |
| M4 | 冰箱食材管理 | ✅ |
| M5 | 智能购物清单 | ✅ |
| M6 | 自然语言问答 | ✅ |
| 加分 | 拍照识别食材 / 小票、语音提问 | 第 5 阶段，可选 |

### 1.2 小组分工（来自 PPT，供生成文档、答辩材料时参考）

| 成员 | 角色 | 主要负责的目录 |
|---|---|---|
| 刘屹（组长） | 后端 | `backend/app/api`、`backend/app/services` |
| 董策 | 数据 / Neo4j | `data/`、`backend/app/graph` |
| 王宇华 | 规则引擎 | `backend/app/rules` |
| 陈鸿杰 | LLM / RAG | `backend/app/agent`、`backend/app/rag` |
| 李栓宝 | 前端 / 部署 | `frontend/`、`deploy/` |

---

## 2. 已确定的决策（不要更改）

| 项 | 决定 |
|---|---|
| 仓库 | `D:\javawebworkspace\tangan-shizhu`，单仓库，前端和后端都在这里从零实现 |
| 代码来源 | 不复制 `personnal-Agent` 或 `aiops` 的代码 |
| 编排 | 一条 LangGraph 工作流。不使用多 Agent，不引入 CrewAI、AutoGen、微软 Agent Framework、Google ADK |
| LangChain | 使用 LangGraph 1.x（会带上 `langchain-core`）。业务代码不使用 Chain、AgentExecutor。模型调用用 OpenAI 官方 SDK 的兼容接口 |
| PostgreSQL、Neo4j | 运行在用户的虚拟机上（192.168.88.x 网段），本机不装 |
| 大模型 | 主力：DeepSeek 或通义千问（OpenAI 兼容接口），具体模型名写在 `.env` 并钉住。推荐解释在云端失败时用模板，不调用本机 7B。问答在云端失败时可以再试本机 Ollama `qwen2.5:7b-instruct`，仍失败则返回暂时无法回答 |
| 向量模型 | `bge-m3`（Ollama，本机）。不用 4B/8B 嵌入模型 |
| 向量库 | Chroma（本机文件存储，`backend/data/chroma`） |
| 鉴权 | PyJWT；密码哈希用 `pwdlib[argon2]` |
| 依赖 | `requirements.txt` 和前端 lock 文件锁版本 |
| 观测 | `recommend_logs` + 本地结构化日志。不接 LangSmith |
| MVP 范围 | M1 ~ M6，病种只做 2 型糖尿病，使用者年龄 ≥ 18 岁 |
| Redis / RabbitMQ | 可选，不算答辩完成标准。定时任务用 APScheduler，缓存先用进程内字典 |
| 时区 | `Asia/Shanghai`。餐次日期和“今天”都按此时区 |
| 部署 | 开发阶段本机直接运行。Docker Compose + Nginx 放在第 6 阶段，不阻塞前面的功能 |

---

## 3. 环境现状与准备

### 3.1 本机已有

- Windows，RTX 4060 8GB，16GB 内存。
- Node v20.17.0。
- Python 3.10 及以上。
- Ollama，已有模型 `qwen2.5:7b-instruct`、`nomic-embed-text`、`moondream`。
- Whisper large-v3 模型位于 `D:\models\whisper`（第 5 阶段语音功能用）。

### 3.2 本机缺少（不要安装，除非用户要求）

- Docker、PostgreSQL、psql。

### 3.3 需要用户提供（开发 AI 第一次遇到时向用户索要）

- 虚拟机 IP（以下写作 `<VM_IP>`）、SSH 登录方式。
- PostgreSQL 用户名和密码；Neo4j 密码。
- DeepSeek 或通义千问的 API Key。

### 3.4 虚拟机上要装的服务

推荐在虚拟机上用 Docker 运行（虚拟机是 Linux，装 Docker 很方便）：

| 服务 | 镜像 | 端口 | 用途 |
|---|---|---|---|
| PostgreSQL 16 | `postgres:16` | 5432 | 业务数据 |
| Neo4j 5 Community | `neo4j:5-community` | 7474（浏览器）、7687（Bolt） | 知识图谱 |

开发 AI 在 `deploy/vm/docker-compose.vm.yml` 中写好这两个服务，用户自己到虚拟机上执行 `docker compose up -d`。

本机执行 `ollama pull bge-m3`，下载向量模型。

---

## 4. 总体架构

```
┌──────────── 前端 Vue3 + Element Plus + ECharts（frontend/）────────────┐
│ 登录 | 健康档案 | 我的冰箱 | 今日推荐 | 营养报告 | 购物清单 | 问答 | 知识图谱 │
└──────────────────────────────┬────────────────────────────────────────┘
                               │ HTTP / 流式（axios 与 fetch，JWT）
┌──────────────────────────────▼────────────────────────────────────────┐
│                      FastAPI 后端（backend/app）                       │
│  api/  ──►  services/  ──►  repositories/（SQLAlchemy）──► PostgreSQL   │
│                │                                                       │
│                ├──► rules/  规则引擎（YAML 规则）                        │
│                ├──► graph/  Neo4j 查询 ───────────────────► Neo4j       │
│                ├──► rag/    指南检索 ────────────────────► Chroma        │
│                └──► agent/  LangGraph 单工作流 ───────────► LLM          │
│                          （节点是函数，不是多个 Agent；                   │
│                           推荐失败时用模板，问答才试 Ollama）            │
└───────────────────────────────────────────────────────────────────────┘
```

### 4.1 推荐流程（PPT 第 9 页的 7 步，用 LangGraph 实现）

```
load_profile ─► load_inventory ─► rule_filter ─► graph_match ─► rag_retrieve ─► llm_explain ─► post_validate
   读档案          读冰箱库存       规则过滤候选     图谱匹配打分     检索指南依据     生成解释        规则二次校验
```

| 节点 | 输入 | 输出 | 说明 |
|---|---|---|---|
| `load_profile` | user_id | 疾病、过敏原、忌口、BMI、每日热量目标 | 从 PostgreSQL 读取。空腹血糖和糖化血红蛋白只随档案返回，不进入规则变量 |
| `load_inventory` | user_id | 未过期库存，数量已换算成克 | 临期食材打上 `expiring=True`。换算表见第 7.1 节 |
| `rule_filter` | 候选食谱 | 通过的食谱、规则 delta、被拒原因 | 过敏原直接排除；忌口只减分。见第 7.3 节 |
| `graph_match` | 通过的食谱 | 按最终分排序的 Top-N | 分数在 `services/scoring.py` 一处计算，见下方公式。Neo4j 不可用时图谱分为 0，并在响应里标记 `graph: "down"` |
| `rag_retrieve` | Top-N + 疾病 | 指南片段（含片段 id、文件名、页码） | Chroma 不可用时片段为空，推荐继续，标记 `rag: "down"` |
| `llm_explain` | 食谱 id、规则消息、片段 | JSON：`recipe_id`、`reason`、`citation_ids` | 只解释给定食谱。不生成热量、GI、GL。云端失败时用模板，不调用本机 7B |
| `post_validate` | JSON + 本次候选 | 最终结果 | `recipe_id` 必须属于本次候选；`citation_ids` 必须来自本次检索；解释里出现的食材必须属于该食谱。不通过则丢掉该项。营养、GI 分级、估测 GL 由后端写入响应 |

最终分（权重是代码里的常量，不是医学剂量）：

```
最终分 = 库存命中分 + 临期分 + 图谱推荐分 − 缺失食材分 + 规则 delta
```

`reject` 在打分之前执行。Neo4j 关闭时，图谱推荐分为 0。

`only_inventory=true` 且通过规则的菜不足 3 道时：严格结果照实返回，并附带被拒原因；另外给出放宽库存后的候选，标出需购买的食材。两组不要混在同一个列表里。

云端模型超时或没有 Key 时，`llm_explain` 使用模板："推荐理由：含库存食材 X、Y；主食 GI 分级为……；依据见检索片段"。没有检索片段时不写指南条号。**推荐不能因为模型、Neo4j 或 Chroma 不可用而整个接口失败。** 规则引擎不可用时才返回错误。

### 4.2 不采用多 Agent

推荐和问答都不做多 Agent 协作。

节点是普通函数：读库、跑规则、查图谱、检索、调用一次模型、再校验。步骤事先写死，不存在“下一步交给哪个专家”的决策。问答里的四类路由是分类器，分完类调用上面的服务或报告服务，不是四个互相委托的 Agent。

多 Agent 适合事先拆不开、需要分工协商的任务。这里拆分已经固定。再拆成营养师、安全审核、购物清单等角色互相调用，会多几次模型往返，也让某一次回答有机会绕过规则引擎。健康场景要的是每次都走同一条约束链。

以后若单独做用药或运动处方，也仍然用受约束的分发调用现有服务，不让多个模型自由对话。依赖里不要加入 CrewAI、AutoGen 等多 Agent 框架。

---

## 5. 目录结构

```
tangan-shizhu/
├── PLAN.md                      # 本文
├── AGENTS.md                    # 第 0 节守则的精简版，供 Cursor 自动读取
├── README.md                    # 启动说明
├── .gitignore
├── backend/
│   ├── .env.example
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/                 # 数据库迁移
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── core/                # config、logging、audit、health、security(JWT)、llm 工厂
│   │   ├── middleware/          # request_id
│   │   ├── db/                  # SQLAlchemy engine、session、Base
│   │   ├── models/              # ORM 模型
│   │   ├── schemas/             # Pydantic 请求 / 响应模型
│   │   ├── repositories/        # 数据访问
│   │   ├── services/            # 业务逻辑
│   │   ├── api/v1/              # 路由：auth、profile、foods、recipes、inventory、
│   │   │                        #       recommend、report、shopping、chat、graph、admin
│   │   ├── rules/               # 规则引擎 + rules/*.yaml
│   │   ├── graph/               # Neo4j 客户端、Cypher 查询、导入脚本
│   │   ├── rag/                 # 指南切块、bge-m3 索引、检索
│   │   ├── agent/               # LangGraph：推荐图、问答路由、档案确认流程
│   │   └── tools/               # ocr / vlm / speech（第 5 阶段）
│   ├── scripts/                 # 数据导入：import_foods.py、import_recipes.py、
│   │                            #   build_graph.py、ingest_guidelines.py、seed_demo.py
│   └── tests/
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── api/                 # axios 封装 + 各模块接口
│   │   ├── stores/              # Pinia：user、profile、inventory
│   │   ├── router/
│   │   ├── views/               # 每个页面一个文件，见第 8 节
│   │   ├── components/
│   │   └── utils/
│   └── tests/                   # Vitest
├── data/
│   ├── raw/                     # 本地原始数据；指南 PDF 和整本成分表不提交进 Git
│   ├── processed/               # 清洗后的 CSV / JSON
│   └── README.md                # 每个数据文件的来源说明
├── deploy/
│   ├── vm/docker-compose.vm.yml # 虚拟机上的 PostgreSQL + Neo4j
│   ├── docker-compose.yml       # 第 6 阶段：全量部署
│   └── nginx/nginx.conf
└── docs/
    ├── contracts.md             # 食谱营养字段、规则上下文、分数权重（阶段 2 冻结）
    ├── api.md                   # 接口说明（也可直接用 FastAPI 的 /docs）
    └── defense/                 # 答辩材料：架构图、演示脚本
```

### 5.1 从零实现的基础设施

全部在本仓库新写，包含：

- `core/config.py`：`DATABASE_URL`、`NEO4J_*`、`LLM_PROVIDER`、`LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL`、`JWT_SECRET`、`APP_TIMEZONE=Asia/Shanghai`。
- `core/logging_setup.py`、`core/audit.py`、`core/health.py`：健康检查包含 PostgreSQL、Neo4j、Chroma、LLM。连不上的组件记为 down，`/health` 本身仍返回 200。
- `core/security.py`：PyJWT 与 `pwdlib[argon2]`。
- `core/llm.py`：OpenAI 兼容客户端工厂。
- `middleware/request_id.py`。
- `rag/`：切块、`bge-m3` 索引、按片段 id 检索。元数据保留 `source`（文件名）、`page`（页码）、`chunk_id`。
- `agent/`：第 4.1 节的推荐图、第 6.6 节的问答路由、第 6.1 节的档案确认流程。
- 健康场景不接入网络搜索。

### 5.2 前端

在 `frontend/` 用 Vite 从零创建 Vue 3 + TypeScript 工程。依赖使用 Vue 3.5、Vite 5、Element Plus 2.9 这一代的当前稳定版，并写入 lock 文件：Element Plus、ECharts、Pinia、vue-router、axios、markdown-it、dompurify、Vitest。不从其他项目复制页面。

---

## 6. 功能详细设计

### 6.1 M1 健康档案

**字段**：性别、出生年份、身高、体重（自动算 BMI）、活动水平（轻 / 中 / 重）、疾病（MVP 只有"2 型糖尿病"，但用多选设计）、空腹血糖（可选）、糖化血红蛋白（可选）、过敏原（多选 + 自定义）、忌口 / 不喜欢的食材、饮食偏好（口味、菜系）、每日热量目标（按身高体重和活动水平自动计算，可手动修改）。

**使用边界**：

- 按 `APP_TIMEZONE` 的当前年份计算，未满 18 岁不能保存档案，也不提供食谱。
- 空腹血糖、糖化血红蛋白只作为档案记录。推荐和规则上下文不读取这两项，页面上写明“不参与饮食推荐”。
- 档案或问答中出现肾病、妊娠时，不生成个体化食谱，固定回复请就医或咨询医生 / 营养师。

**两种录入方式**：

1. 表单填写（主要方式）。
2. 对话录入（本仓库自己实现确认流程）：
   - 用户在问答页说"我对虾过敏，不吃香菜"。
   - 后端抽取出草稿 `{allergies: ["虾"], dislikes: ["香菜"]}`，返回 `pending_profile_id` 和预览。
   - 前端显示预览卡片；用户回复"确认"后写入档案，回复"取消"则丢弃，回复其他内容则视为纠正，由 LLM 修改草稿后再次预览。
   - **任何健康信息都不能未经确认就写入档案。**

**热量目标计算**：按《中国居民膳食指南》的简化方法，用理想体重（身高 cm − 105）× 每公斤所需热量（按活动水平和 BMI 取 20 ~ 35 kcal）。这是课程项目用的估算，不是临床营养处方。公式写在 `services/nutrition.py` 中，注释写明出处和“简化估算”，并附单元测试。具体系数在核对指南前标注 `source: "待核对"`。

### 6.2 M2 智能食谱推荐

- 入口：选择餐次（早 / 中 / 晚 / 加餐），可勾选"只用冰箱里的食材"。餐次日期按 `Asia/Shanghai`。
- 输出：最多 3 ~ 5 道菜。每道包括：菜名、图片（可选）、所需食材（标出"库存已有"和"需购买"）、每份营养（热量、碳水、蛋白质、脂肪、膳食纤维）、主食 GI 分级、`gl_estimate`（必须带 `gl_is_approximate: true`）、推荐理由、指南引用。
- 营养口径：
  - 热量和宏量营养素由食物成分表按克数相加。
  - 主食展示 GI 分级（高 / 中 / 低）。分界写在规则 YAML 里，`source` 未核对时前端要显示“待核对”，不把示例阈值当成已证实的临床标准。
  - 混合餐 GL 只作为粗估值。一盘菜的升糖不是食材 GI 按克加权，响应里固定带近似标记。
  - 食谱未列出用油时，按 `data/processed/cooking_oil.csv` 的烹饪方式默认用油克数，计入热量和脂肪，并标明“烹调油为估算”。该表的克数在核对前全部 `source: "待核对"`。食谱已写明用油则用食谱用量，不重复加。
- 被规则拒绝的菜在"为什么不推荐"折叠面板中展示 `rule_id`、原因和出处。
- “只用冰箱食材”不足 3 道时，按第 4.1 节分成“严格结果”和“放宽后需购买”两组。
- 支持"换一批"（排除已展示的食谱）和"加入今日计划"。加入计划以用户、日期、餐次、食谱去重。

### 6.3 M3 可解释营养报告

- **单餐 / 单日报告**：将今日计划中的食谱营养相加，与每日目标对比（ECharts 环形图 + 柱状图），并给出超标或不足提示。
- **周报告**：近 7 天的热量趋势折线图，以及碳水供能比、膳食纤维达标天数。
- **解释**：每条提示都要说明依据。供能比的目标区间必须来自指南原文和页码；页码未核对前，只展示后端算出的比例，不写具体目标区间。
- 数值、GI 分级和粗估 GL 由后端计算。LLM 只把已经算好的数字和检索片段组织成文字，报告接口同样校验引用 id。
- 周报和日报的“今天”使用 `Asia/Shanghai`。

### 6.4 M4 冰箱食材管理

- 增删改查：食材（从食物库下拉搜索选择，用 `foods.id` 关联）、数量、单位、购买日期、保质期 / 到期日。
- 单位：入库时用 `food_unit_conversions` 把数量换成克。换算表里没有的单位直接拒绝，请用户改成克，不猜测。
- 临期提醒：到期前 2 天标黄，已过期标红。APScheduler 每天按 `Asia/Shanghai` 检查一次，结果在首页显示。进程内只运行一个调度器（uvicorn 单 worker）。不把 RabbitMQ 当作这项功能的完成条件。
- 推荐时优先使用临期食材。
- 第 5 阶段（可选）：拍照识别食材或购物小票。识别结果先预览，用户确认后才入库。

### 6.5 M5 智能购物清单

- 从"今日 / 本周计划"中的食谱生成：所需食材克数 − 库存克数 = 需购买的克数。展示时能换回常见单位的，附上单位；换不回的用克。
- 按类别分组（蔬菜、肉蛋、主食……），可勾选"已购买"；勾选后可一键加入冰箱库存。
- 支持手动添加条目。
- 生成时同样经过规则过滤：不会把过敏原放进清单。

### 6.6 M6 自然语言问答

- 示例问题："糖尿病能吃西瓜吗？""冰箱里有鸡蛋和番茄，晚上做什么？""这周我碳水吃多了吗？"
- 用 LangGraph 实现单工作流 `route → prepare → respond`。`route` 只做分类，然后调用已有服务，不把问题转给另一个 Agent。路由分为 4 类：
  1. `knowledge`：知识问答 → 先查图谱关系，GI 数值从 PostgreSQL 读取，再用 RAG 检索指南，最后由 LLM 回答并附引用 id。
  2. `recommend`：推荐请求 → 调用第 4.1 节的推荐流程。
  3. `report`：询问自己的饮食数据 → 调用报告服务取数，再由 LLM 解读已算好的数字。
  4. `profile_update`：用户在说自己的健康信息 → 进入第 6.1 节的确认流程。
- 流式输出用 `fetch` 读取响应流，请求头携带 JWT。不用浏览器原生 `EventSource`（它带不上 Authorization）。会话历史存在 PostgreSQL。
- 回答末尾固定附上免责声明。
- 调用 LLM 之前用 `safety.yaml` 拦截：用药和剂量、诊断、急症（胸痛、低血糖等）、肾病、妊娠、未满 18 岁。命中后固定回复“请及时就医 / 咨询医生”，不生成饮食或治疗建议。答辩材料里说明：换一种说法仍可能漏过，所以营养数字始终由后端计算。

### 6.7 知识图谱可视化页（答辩展示用）

- 输入一个食材或疾病，展示其一度和二度关系（ECharts graph，力导向布局）。
- 节点按类型着色。点击食材节点时用 `pg_id` 向 PostgreSQL 取 GI 和营养素，图谱节点上不保存这些数字。

### 6.8 管理端（简化版）

- 角色：`user` 和 `admin`。
- admin 可以：上传指南 PDF 并重建索引、查看数据统计、查看审计日志、重建图谱。

---

## 7. 数据设计

### 7.1 PostgreSQL 表（用 Alembic 管理迁移）

| 表 | 主要字段 |
|---|---|
| `users` | id, username(唯一), password_hash, role, created_at |
| `health_profiles` | id, user_id(唯一), gender, birth_year, height_cm, weight_kg, activity_level, diseases(JSONB), fasting_glucose, hba1c, allergies(JSONB), dislikes(JSONB), preferences(JSONB), daily_kcal_target, updated_at |
| `pending_profile_updates` | id, user_id, session_id, draft(JSONB), created_at |
| `foods` | id, food_code(唯一，可空), name(唯一), alias(JSONB), category, kcal, carb_g, protein_g, fat_g, fiber_g, sodium_mg, gi, gi_source, nutrient_source, per_g(默认 100) |
| `food_unit_conversions` | id, food_id, unit, grams_per_unit |
| `recipes` | id, name, cuisine, meal_types(JSONB), cooking_method, steps(TEXT), servings, image_url, source |
| `recipe_ingredients` | id, recipe_id, food_id, amount_g, is_main |
| `inventory_items` | id, user_id, food_id, quantity, unit, purchased_at, expires_at, created_at |
| `meal_plans` | id, user_id, date, meal_type, recipe_id, servings |
| `shopping_lists` / `shopping_items` | 清单表；条目表含 food_id, amount_g, checked |
| `chat_sessions` / `chat_messages` | 会话和消息（role, content, meta JSONB） |
| `recommend_logs` | id, user_id, request(JSONB), result(JSONB), rejected(JSONB), latency_ms, created_at（答辩时可展示可追溯性） |
| `audit_logs` | actor_id, action, target, detail(JSONB), request_id, created_at |

食谱营养**不单独存储**，由 `recipe_ingredients × foods` 实时计算，再加上烹调油估算，并在服务层做进程内缓存。热量、GI、营养素只以 PostgreSQL 为准。

单元测试 mock 数据库会话。真正读写 JSONB 的测试连虚拟机上的 PostgreSQL，标记 `@pytest.mark.integration`，默认不跑。不用 SQLite 冒充 PostgreSQL。

### 7.2 Neo4j 图谱模型

**节点**：

| 标签 | 属性 |
|---|---|
| `Disease` | name |
| `Nutrient` | name（添加糖、钠等，只用于疾病限制，不存放食物含量） |
| `Food` | name, category, pg_id（对应 PostgreSQL 中 foods.id） |
| `Recipe` | name, pg_id |
| `CookingMethod` | name（蒸、煮、炒、炸……） |

**关系**：

| 关系 | 示例 | 属性 |
|---|---|---|
| `(Disease)-[:AVOID]->(Food)` | 糖尿病 禁忌 白砂糖 | reason, source |
| `(Disease)-[:RECOMMEND]->(Food)` | 糖尿病 推荐 燕麦 | reason, source |
| `(Disease)-[:LIMIT]->(Nutrient)` | 糖尿病 限制 添加糖 | max_per_day, unit, source |
| `(Recipe)-[:CONTAINS]->(Food)` | 番茄炒蛋 包含 鸡蛋 | |
| `(Recipe)-[:COOKED_BY]->(CookingMethod)` | | |
| `(Disease)-[:AVOID_METHOD]->(CookingMethod)` | 糖尿病 少用 油炸 | reason |
| `(Food)-[:SUBSTITUTE]->(Food)` | 白米 可替换为 糙米 | reason |

**同步方式**：PostgreSQL 是食材、食谱和营养数字的主数据。`scripts/build_graph.py` 只同步 id、名称、类别和关系。疾病关系来自 `data/processed/disease_relations.csv`，人工整理，每行带 source。不使用模型自动生成推荐或禁忌。`CONTAINS` 不写克数，用量以 PostgreSQL 为准。

### 7.3 规则引擎（`backend/app/rules/`）

规则写在 YAML 中，引擎用 Python 实现。示例（**数值仅为格式示意，须对照指南核对后再使用**）：

```yaml
# rules/diabetes.yaml
disease: 2型糖尿病
rules:
  - id: DM-001
    type: reject            # reject = 直接排除；warn = 保留但提示；score = 加 / 减分
    target: recipe
    when: "main_staple_gi >= 70"
    message: "主食为高 GI 食物（GI≥70），不适合糖尿病人群"
    source: "成人糖尿病食养指南（2023 年版），第 X 页（待核对）"
  - id: DM-002
    type: warn
    target: recipe
    when: "added_sugar_g > 10"
    message: "添加糖较多"
    source: "待核对"
  - id: DM-003
    type: score
    target: recipe
    when: "fiber_g >= 5"
    delta: 2
    message: "膳食纤维丰富"
    source: "待核对"
```

```yaml
# rules/common.yaml   过敏原为 reject；忌口为 score（负分），对所有用户生效
# rules/safety.yaml   用药与剂量、诊断、急症、肾病、妊娠、未成年 → 固定回复"请就医"
```

**引擎要求**：

- `when` 表达式使用 `simpleeval`，不用 Python `eval`。变量只来自引擎上下文：食谱营养、主食 GI、食材列表、过敏原、忌口。上下文里没有空腹血糖和糖化血红蛋白。字段名以 `docs/contracts.md` 为准。
- 每条规则返回 `rule_id`、`message`、`source`。
- 过敏原是 `reject`。忌口是负的 `score`，不淘汰整道菜。
- `post_validate` 按第 4.1 节核对 id，不从模型原文抽取食材名。
- 每条规则至少 1 个单元测试。

### 7.4 原始数据来源与规模（MVP）

| 数据 | 来源 | MVP 规模 | 处理脚本 |
|---|---|---|---|
| 食物营养成分 | 《中国食物成分表》（标准版第 6 版）中人工摘录并注明出处的常见食材。不把整本表或来源不明的全量爬取文件提交进 Git | 300 种；做不到时先 30 种 | `scripts/import_foods.py` |
| GI 值 | 成分表的 GI 部分、悉尼大学 GI 数据库中允许引用的条目。每条写 `gi_source`，并遵守该数据库的引用要求 | 覆盖主食、水果、常见蔬菜 | 同上 |
| 食谱 | 许可证允许再利用的公开中文食谱（导入前先确认仓库许可证）。下厨房等站点的爬取数据不用 | 150 道，食材必须能匹配 `foods` 表；做不到时先 20 道 | `scripts/import_recipes.py`（别名表 + 人工映射表） |
| 指南文本 | 国家卫健委《成人糖尿病食养指南（2023 年版）》PDF，放在本机 `data/raw/`，该 PDF 写入 `.gitignore` | 1 份 | `scripts/ingest_guidelines.py` |
| 疾病-食材关系 | 从指南人工整理，禁止用模型生成 | 50 ~ 100 条 | `data/processed/disease_relations.csv` |
| 单位换算 | 人工整理，每行是食材、单位、每单位克数 | 覆盖种子食材的常见单位 | `data/processed/unit_conversions.csv` |
| 烹调油 | 人工整理的烹饪方式默认用油克数，核对前 `source` 为“待核对” | 蒸、煮、炒、炸等 | `data/processed/cooking_oil.csv` |

**执行 AI 对数据的处理原则**：

- 只下载许可证允许再利用的数据，并在 `data/README.md` 写明来源链接和获取日期。成分表用人工摘录，不提交整本。指南 PDF 放在 `data/raw/` 并写入 `.gitignore`。
- 疾病关系、单位换算、烹调油默认值由人工整理。不用模型生成这些表。
- 正式数据没到齐时，先做 **30 种食材 + 20 道食谱的种子数据**（`scripts/seed_demo.py`），让流程能端到端跑通，并在 `data/README.md` 列出待补充清单。

---

## 8. 前端页面

| 路由 | 页面 | 主要组件 |
|---|---|---|
| `/login`、`/register` | 登录注册 | 表单 |
| `/` | 首页 | 今日热量进度环、临期食材提醒、快捷入口、免责声明 |
| `/profile` | 健康档案 | 分步表单（基本信息 → 疾病指标 → 过敏忌口 → 偏好），BMI 和热量目标自动计算。未满 18 岁不能保存。血糖和糖化血红蛋白旁注明“不参与饮食推荐” |
| `/fridge` | 我的冰箱 | 表格 + 到期状态色标 + 新增对话框（食材远程搜索下拉）。未知单位不能提交 |
| `/recommend` | 今日推荐 | 餐次选择、推荐卡片、严格结果与放宽结果分开展示、"为什么不推荐"折叠面板、加入计划。GL 显示为粗估，待核对的 GI 阈值要标出来 |
| `/recipe/:id` | 食谱详情 | 食材、步骤、营养表、图谱关系小图 |
| `/report` | 营养报告 | 日 / 周切换，ECharts 环形图、柱状图、折线图，文字解读 |
| `/shopping` | 购物清单 | 分组列表、勾选、一键入库 |
| `/chat` | 问答 | `fetch` 流式消息、Markdown 渲染（markdown-it + dompurify）、引用折叠、健康信息确认卡片 |
| `/graph` | 知识图谱 | 搜索框 + ECharts 力导向图 |
| `/admin` | 管理 | 指南上传、重建索引 / 图谱、数据统计、审计日志 |

**通用要求**：

- 普通接口用 axios，拦截器自动携带 JWT；收到 401 时跳转登录页。问答流式接口在 `src/api/` 里用 `fetch` 读流，并带上同一个 JWT。
- 所有列表要处理加载中、空数据和错误三种状态。
- 风格保持简洁，主色用绿色系（健康主题）。
- 页面底部固定显示免责声明。

---

## 9. 分阶段任务（按顺序执行）

> 对应 PPT 中的 16 周计划。每个阶段结束时，系统都应该处于**可以启动、可以演示**的状态。

### 阶段 1：脚手架（第 1 ~ 2 周）

- [x] **1.1 初始化仓库**：创建第 5 节的目录结构、`.gitignore`、`README.md`、`AGENTS.md`，然后 `git init`。
  - 验收：目录结构与第 5 节一致；`.env` 和 `data/raw/*.pdf` 被 git 忽略。
- [x] **1.2 后端骨架**：创建 `backend/.venv`，编写锁版本的 `requirements.txt`（fastapi、uvicorn、sqlalchemy 2、psycopg[binary]、alembic、pydantic-settings、pyjwt、pwdlib[argon2]、neo4j、langgraph、openai、chromadb、simpleeval、apscheduler、pypdf、pytest、httpx、ruff）。不加入 python-jose、passlib、langchain、langchain-openai、langchain-ollama，也不加入多 Agent 框架。编写 `app/main.py`，提供 `/api/v1/health`。
  - 验收：`uvicorn app.main:app` 能启动，`/docs` 页面可以打开。
- [x] **1.3 基础设施**：按第 5.1 节从零实现 config、logging、audit、health、security、request_id、rag 骨架。
  - 验收：`pytest` 通过；健康检查能列出各组件状态（连不上的显示 down，接口本身不报错）。
- [x] **1.4 LLM 工厂**：编写 `core/llm.py`。DeepSeek 使用 `https://api.deepseek.com`，通义千问使用 `https://dashscope.aliyuncs.com/compatible-mode/v1`，模型名从 `.env` 读取。推荐解释只走云端，失败由调用方改用模板。问答可再试 Ollama。
  - 验收：单元测试中 mock 云端失败时，推荐路径不调用 Ollama；问答路径会再试 Ollama。
- [x] **1.5 虚拟机服务**：编写 `deploy/vm/docker-compose.vm.yml`（PostgreSQL 16 + Neo4j 5，数据目录挂载卷）。**向用户索要虚拟机 IP 和密码**，由用户在虚拟机上启动服务。
  - 验收：本机健康检查显示 PostgreSQL 和 Neo4j 都是 up。
- [x] **1.6 前端骨架**：在 `frontend/` 中用 Vite 创建 Vue3 + TypeScript 工程，安装第 5.2 节的依赖并锁版本；搭好布局（侧边菜单 + 顶栏 + 免责声明页脚），配置 `/api` 代理到 `127.0.0.1:8000`。
  - 验收：`npm run dev` 启动后能看到布局，首页能显示后端健康检查的结果。

### 阶段 2：数据层与用户（第 3 ~ 4 周）

- [x] **2.1 ORM 与迁移**：按第 7.1 节编写全部模型，生成 Alembic 初始迁移，并在虚拟机的 PostgreSQL 上执行。
  - 验收：`alembic upgrade head` 成功。单元测试 mock 会话；集成测试连虚拟机 PostgreSQL。不用 SQLite 做 JSONB 测试。
- [x] **2.2 认证**：注册、登录（PyJWT）、`get_current_user` 依赖、admin 角色校验。密码用 `pwdlib[argon2]`。
  - 验收：pytest 覆盖注册、登录、无 token 访问返回 401、普通用户访问 admin 接口返回 403。
- [x] **2.3 种子数据**：编写 `scripts/seed_demo.py`（30 种食材、20 道食谱、常见单位换算、带“待核对”的烹调油表、1 个年满 18 岁的演示用户及其档案）。
  - 验收：执行后数据库中有数据，能用演示账号登录。
- [x] **2.4 正式数据导入**：编写 `import_foods.py` 和 `import_recipes.py`，含食材名标准化；无法匹配的食材输出到 `data/processed/unmatched.csv`。
  - 验收：达到第 7.4 节的规模目标，或在 `data/README.md` 中说明还缺什么数据。来源和许可证写在该文件中。
- [x] **2.5 前端登录与路由守卫**。
  - 验收：未登录访问任何页面都会跳转到登录页。
- [x] **2.6 共享约定**：编写 `docs/contracts.md`，冻结食谱营养字段、规则上下文变量名、分数权重、GI 分级字段。阶段 3 开始前完成，之后改字段要同时改这份文档和测试。

### 阶段 3：健康档案、冰箱、规则引擎（第 5 ~ 7 周）

- [x] **3.1 M1 健康档案接口与页面**：包括 BMI 和热量目标计算（`services/nutrition.py`，带单元测试）。未满 18 岁拒绝保存。血糖和糖化血红蛋白不进入推荐。
- [x] **3.2 M4 冰箱接口与页面**：食材远程搜索、单位换算、未知单位拒绝、到期状态、APScheduler 每日检查、首页临期提醒。
- [x] **3.3 规则引擎**：按第 7.3 节实现 `common.yaml`、`diabetes.yaml`、`safety.yaml`，使用 simpleeval，每条规则都有单元测试。
  - 验收：给定一个高 GI 食谱和一个糖尿病用户，引擎返回 reject，并带有 rule_id 和 source。忌口只减分。过敏原被排除。
- [x] **3.4 食谱营养计算服务**：按食材克数汇总营养，计算主食 GI 分级和带近似标记的 GL，并按烹调油表计入估算用油。
  - 验收：用手工计算的样例做单元测试，覆盖“食谱已写明用油”和“使用默认用油”两种情况。

### 阶段 4：知识图谱、RAG、推荐、报告、购物清单（第 8 ~ 11 周）

- [x] **4.1 Neo4j 建图**：编写 `scripts/build_graph.py` 和 `graph/queries.py`（查询食材的关系、疾病的推荐和禁忌、食谱匹配）。节点不写 GI 和营养素含量。
  - 验收：Neo4j 浏览器中能看到第 7.2 节的节点和关系；查询函数有集成测试（Neo4j 不可用时跳过该测试）。
- [x] **4.2 指南 RAG**：编写 `scripts/ingest_guidelines.py`，使用 bge-m3 建索引，检索结果带 `chunk_id` 和页码。PDF 不进 Git。
  - 验收：问"糖尿病每天主食吃多少"，能检索到指南中的相关段落。
- [x] **4.3 推荐流程**：按第 4.1 节用 LangGraph 实现 7 个函数节点，编写 `/api/v1/recommend`，并写入 `recommend_logs`。模型输出是 JSON。
  - 验收：
    - 演示用户得到的推荐里没有过敏原，也没有违反 reject 规则的菜。忌口菜可以出现，但分数更低。
    - 断开云端 LLM 后仍返回模板理由，且测试断言没有调用 Ollama。
    - Neo4j 或 Chroma 不可用时接口仍返回通过规则的食谱，并带 `down` 标记。
    - “只用冰箱食材”不足 3 道时，严格结果和放宽结果分成两个列表。
    - 被拒食谱带有拒绝原因。营养数字来自后端，不来自模型 JSON。
- [x] **4.4 推荐页与食谱详情页**。
- [x] **4.5 M3 营养报告**：meal_plans 接口、日 / 周统计接口、LLM 解读接口（数值由后端计算）、报告页图表。日期使用 `Asia/Shanghai`。
- [x] **4.6 M5 购物清单**：从计划生成清单、按克扣减库存、勾选已购买、一键入库。过敏原不进清单。
- [x] **4.7 知识图谱可视化页**。点击食材时向 PostgreSQL 取 GI。

### 阶段 5：问答与加分项（第 12 ~ 13 周）

- [x] **5.1 M6 问答**：路由分 4 类（第 6.6 节），`fetch` 流式输出，会话持久化，safety 规则在调用 LLM 前拦截。
  - 验收：
    - "糖尿病能吃西瓜吗"的回答带有指南引用和免责声明。
    - "我胸口疼怎么办"、肾病、妊娠、用药剂量被拦截，返回就医提示。
  - 注：指南引用需导入指南 PDF 建 Chroma 索引后生效（当前索引为空，待补）。
- [x] **5.2 对话录入健康信息**：按第 6.1 节实现确认 / 纠正流程，前端显示确认卡片。
  - 验收：说"我对虾过敏"后出现预览；确认后档案中出现"虾"；说"不对，是对螃蟹过敏"后草稿被修正。未确认前档案不变。
- [ ] **5.3（可选）拍照识别食材 / 小票入库**：识别结果先预览，确认后才入库。
- [ ] **5.4（可选）语音提问**：faster-whisper，模型目录 `D:/models/whisper`，large-v3，CUDA float16。

### 阶段 6：测试、答辩，以及可选的部署（第 14 ~ 16 周）

- [ ] **6.1（可选）Redis**：缓存食谱营养计算结果。不做也不影响答辩。
- [ ] **6.2（可选）RabbitMQ**：不做。临期检查保持 APScheduler。
- [ ] **6.3（可选）Docker Compose**：backend、frontend（Nginx 托管静态文件 + 反向代理 `/api`）、postgres、neo4j。不把 Redis 和 RabbitMQ 列为必选项。Ollama 不放进容器。
- [x] **6.4 测试补齐**：
  - 后端 pytest 覆盖率 ≥ 60%，规则引擎和营养计算 ≥ 90%。
  - 前端 Vitest 覆盖登录守卫、推荐卡片和免责声明。
  - 导出一套 Postman 集合到 `docs/postman/`。
- [x] **6.5 质量评估**：准备 20 个测试用户画像，统计规则违反率（目标为 0）、库存利用情况和平均响应时间。另准备约 20 个带期望页码的指南问题，统计检索前 5 条的命中率。结果放在 `docs/defense/`。
  - 注：20 画像评估已完成（`docs/defense/evaluation.md`）；检索前 5 命中率依赖指南 PDF，待补。
- [x] **6.6 答辩材料**：架构图、演示脚本（按"建档 → 冰箱 → 推荐 → 解释 → 报告 → 购物清单 → 问答 → 图谱"的顺序）、常见问题回答。说明为什么是单工作流而不是多 Agent，以及关键词拦截的局限。

---

## 10. 接口清单（前缀 `/api/v1`）

| 模块 | 方法与路径 |
|---|---|
| 健康检查 | `GET /health` |
| 认证 | `POST /auth/register`、`POST /auth/login`、`GET /auth/me` |
| 档案 | `GET /profile`、`PUT /profile`、`POST /profile/pending/{id}/confirm`、`POST /profile/pending/{id}/cancel`、`POST /profile/pending/{id}/correct` |
| 食材 | `GET /foods?q=`、`GET /foods/{id}` |
| 食谱 | `GET /recipes?q=&meal_type=`、`GET /recipes/{id}`（含营养和图谱关系） |
| 冰箱 | `GET /inventory`、`POST /inventory`、`PUT /inventory/{id}`、`DELETE /inventory/{id}`、`GET /inventory/expiring` |
| 推荐 | `POST /recommend`（body：meal_type、only_inventory、exclude_ids）。响应分严格结果、放宽结果和被拒原因，并带 `graph` / `rag` 状态 |
| 计划 | `GET /meal-plans?date=`、`POST /meal-plans`、`DELETE /meal-plans/{id}` |
| 报告 | `GET /report/daily?date=`、`GET /report/weekly?end=`、`POST /report/explain` |
| 购物清单 | `POST /shopping/generate`、`GET /shopping/{id}`、`PATCH /shopping/items/{id}`、`POST /shopping/{id}/to-inventory` |
| 问答 | `POST /chat`、`POST /chat/stream`（`fetch` 读流，事件类型：`token`、`sources`、`profile_pending`、`done`）、`GET /chat/sessions`、`GET /chat/sessions/{id}` |
| 图谱 | `GET /graph/neighbors?name=&depth=` |
| 管理 | `POST /admin/guidelines`（上传）、`POST /admin/reindex`、`POST /admin/rebuild-graph`、`GET /admin/stats`、`GET /admin/audit` |

统一响应：成功时直接返回数据；失败时返回 `{"detail": "...", "code": "..."}`，每个响应都带 `X-Request-ID` 头。

---

## 11. 工程规范

- **Python**：
  - 带类型注解，用 `ruff` 检查格式。
  - 依赖版本锁在 `requirements.txt`。
  - 分层固定为 `api → services → repositories`，路由函数里不写业务逻辑。
  - 查询用户数据时带当前用户 id。
  - 业务日期使用 `APP_TIMEZONE`（`Asia/Shanghai`）。
- **编排**：推荐和问答都是第 4 节的单工作流。不新增 Agent 角色，不让模型决定要不要跳过规则。
- **Prompt**：统一放在 `agent/prompts.py`。模型只根据给定食谱和检索片段回答；片段里没有的内容就说不知道；不输出营养数字。
- **前端**：
  - 使用 `<script setup lang="ts">`。
  - 接口请求只写在 `src/api/` 中。普通请求用 axios，流式问答用 `fetch`。
- **提交信息**：`<类型>(<模块>): <说明>`，例如 `feat(rules): 实现糖尿病 GI 过滤规则`。类型取 feat、fix、test、docs、refactor、chore 之一。
- **测试**：
  - 外部依赖（LLM、Neo4j、Chroma）在单元测试中一律 mock。
  - 需要真实 PostgreSQL 的测试加上 `@pytest.mark.integration`，默认不运行。
  - 不用 SQLite 代替 PostgreSQL 的 JSONB。

---

## 12. 风险与应对

| 风险 | 应对 |
|---|---|
| 数据收集比预期慢 | 先用种子数据跑通全流程（任务 2.3），正式数据由小组成员并行补充 |
| 成分表或食谱许可证不清 | 只提交人工摘录和许可证允许的数据；指南 PDF 不进 Git |
| 16GB 内存吃紧 | 数据库放在虚拟机上；解释用云端模型；本机 Ollama 平时只跑 bge-m3。不加载 4B/8B 嵌入模型 |
| 云端 LLM 不可用或欠费 | 推荐改用模板。问答再试本机 7B，失败则提示暂时无法回答 |
| 模型编造营养数值或食材 | 数字由后端写入响应；模型只返回食谱 id 和引用 id；`post_validate` 核对这两类 id |
| 混合餐 GL 被当成精确指标 | 响应带 `gl_is_approximate`；主食用 GI 分级，阈值未核对时界面显示“待核对” |
| 虚拟机或 Neo4j 不通 | 健康检查标出 down 的组件；推荐降级为规则 + 库存，图谱分记 0 |
| 医疗边界 | 免责声明；safety 规则拦截用药、诊断、急症、肾病、妊娠和未成年；血糖记录不参与推荐 |
| 多 Agent 绕过规则 | 不引入多 Agent。分类器只能调用已经写好的服务 |

---

## 13. 开发日志（执行 AI 每完成一个任务追加一行）

| 日期 | 任务编号 | 完成内容 | 备注 / 遗留问题 |
|---|---|---|---|
| 2026-10-29 | 1.1 | 建立目录、`.gitignore`、`README.md`、`AGENTS.md`，并初始化 Git | `.env` 与 `data/raw/*.pdf` 已忽略。后端和前端还没有可运行代码 |
| 2026-10-29 | 1.2 | 后端虚拟环境、锁版本依赖、`GET /api/v1/health` 和 `/docs` | pytest 2 项通过。虚拟环境不入库 |
| 2026-10-29 | 1.3 | 配置、日志、审计、JWT、请求号、依赖健康检查和指南切块骨架 | 未配置的 PostgreSQL、Neo4j、LLM 显示 down，接口仍返回 200。pytest 12 项通过 |
| 2026-10-29 | 1.4 | LLM 工厂：推荐只走云端，问答失败后再试 Ollama | pytest 15 项通过。尚未接入真实 API Key |
| 2026-10-29 | 1.5 | 虚拟机 `192.168.88.138` 上的 PostgreSQL 16 与 Neo4j 5 已启动 | 本机健康检查 postgresql、neo4j 均为 up。密码只在 `.env`。大模型仍为 down |
| 2026-10-29 | 1.6 | Vue 3 布局、免责声明和首页健康检查 | 数据库、图谱、大模型显示 down；指南索引 up。Vitest 1 项通过 |
| 2026-10-29 | 2.1 | 全部 PostgreSQL 模型与初始迁移 `44e3579f00ee` | `alembic upgrade head` 已在虚拟机执行。pytest 19 通过，集成测试 1 通过。营养数字只在 PostgreSQL |
| 2026-10-29 | 2.2 | 注册、登录、当前用户和管理员校验 | 密码用 pwdlib。无 token 返回 401，普通用户访问管理接口返回 403。pytest 25 通过 |
| 2026-10-29 | 2.3 | 30 种食材、20 道食谱、克单位换算和演示用户 | 营养素与 GI 留空，烹调油克数未填，均标待核对。演示账号 demo 可登录。pytest 26 通过 |
| 2026-10-30 | 2.4 | 导入 1677 条成分和 251 条 GI | 同名才挂 GI。Tr 与横线留空。指南 PDF 未切块。食谱仍是 20 道演示菜。未对照纸质书 |
| 2026-10-30 | 2.5 | 登录页、注册页和路由守卫 | 未登录访问会跳到登录页。刷新后仍保持登录。Vitest 4 通过 |
| 2026-10-30 | 2.6 | 冻结食谱营养、规则变量、排序权重和 GI 分级 | 见 `docs/contracts.md`。GI 分界 55/70 标待核对。空营养不用 0 填充 |
| 2026-10-30 | 3.1 | 健康档案表单、BMI 和热量估算 | 未满 18 岁不能保存。血糖和糖化血红蛋白只记录。热量系数待核对。pytest 41 通过 |
| 2026-10-30 | 3.2 | 冰箱入库、单位换算和临期提醒 | 没有换算的单位直接拒绝。到期前 2 天标黄，已过期标红。每天 8 点检查。pytest 45 通过 |
| 2026-10-30 | 3.3 | 过敏原排除、忌口减分、高 GI 主食排除和安全拦截 | 表达式用 simpleeval。空 GI 不命中。添加糖规则因没有该列不会命中。GI 阈值 70 仍待核对。pytest 59 通过 |
| 2026-10-30 | 3.4 | 按克数汇总食谱营养、主食 GI 分级和粗估 GL | 食谱已写明用油则不重复加。烹调油表克数仍空，空克数不补油。GL 固定标近似。pytest 73 通过 |
| 2026-10-30 | 4.1 | 把食材、食谱和有页码的疾病关系写入 Neo4j | 节点不写 GI 和营养数字。添加糖没有克数，上限留空。默认 pytest 78 通过，图谱集成测试 1 通过 |
| 2026-10-30 | 4.2 | 用 bge-m3 为糖尿病指南建立检索索引 | 135 个片段，结果带 chunk_id 和 PDF 页码。PDF 与索引不进 Git。问主食定量能检索到指南正文。默认 pytest 80 通过 |
| 2026-10-30 | 4.3 | 固定七步推荐：规则过滤、图谱打分、检索和模板解释 | 营养数字由后端写入。云端失败不调用本机对话模型。图谱或检索失败仍返回食谱。默认 pytest 97 通过 |
| 2026-10-30 | 4.4 | 推荐页、食谱详情和加入今日计划 | 严格结果与需购买分开展示。GI 阈值待核对，GL 标粗估。同一天同一餐同一道菜不重复加入。pytest 107 通过，Vitest 14 通过 |
| 2026-10-30 | 4.5 | 按计划合计日热量和周均热量，并生成说明 | 缺营养素的日期不按 0 计入。供能比用 4/4/9 估算并标待核对，不写目标区间。膳食纤维达标天数不统计。云端失败用模板，不调用本机对话模型。pytest 116 通过，Vitest 19 通过 |
| 2026-10-30 | 4.6 | 按计划食材减去未过期库存生成购物清单 | 过敏原不进清单。能整除的换算单位会显示出来，否则用克。勾选后可按克入库。pytest 124 通过，Vitest 22 通过 |
| 2026-10-30 | 4.7 | 知识图谱页展示一度和二度关系 | 节点不写 GI 和营养数字。点击有成分表编号的食材才从 PostgreSQL 读取。图谱不可用时页面仍打开。pytest 129 通过，Vitest 24 通过 |
| 2026-11-19 | 5.1 | M6 问答：路由 4 类、流式输出、会话持久化、safety 调用 LLM 前拦截 | 端到端验证通过。补了药名和剂量短语拦截（修复"二甲双胍一次吃多少"漏拦）。指南引用待 PDF 建索引 |
| 2026-11-19 | 5.2 | 对话录入健康信息：确认 / 取消 / 纠正流程 + 前端预览卡片 | 确认写入、取消丢弃、纠正改草稿，未确认不写档案。test_chat 16 通过 |
| 2026-11-19 | 6.4 | 测试补齐：后端覆盖率 ≥80%、规则 94%、营养 100%，前端 Vitest 覆盖登录守卫/推荐卡片/免责声明，Postman 集合 39 请求 | 后端全量通过（149 项）。见 docs/postman/ |
| 2026-11-19 | 6.5 | 质量评估：20 画像规则违反率 0%、库存利用约 38.8%、平均响应时间约 134ms（模板降级路径） | 妊娠/肾病/未成年正确拦截。检索前 5 命中率待 PDF。见 docs/defense/evaluation.md |
| 2026-11-19 | 6.6 | 答辩材料：架构图、演示脚本、常见问题回答 | 说明单工作流理由与关键词拦截局限。见 docs/defense/ |
