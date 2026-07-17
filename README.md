# AI 字幕分析与素材匹配平台

## 项目简介

用户上传口播视频、音频或粘贴字幕文本后，系统自动完成字幕整理、语义分段、关键词提取，并从素材库中推荐与字幕内容匹配的图片/视频素材，支持人工调整并持久化保存。

## 提交信息

| 项目 | 内容 |
| :--- | :--- |
| 候选人姓名 | 刘敦宇 |
| 选择题目 | 题目二：AI 字幕分析与素材匹配平台 |
| 公网演示地址 | https://liudunyu666.github.io/ai-subtitle-matching-platform/ |
| 测试账号 | 无需登录 |
| 源代码仓库 | https://github.com/liudunyu666/ai-subtitle-matching-platform |
| 主要技术方案 | FastAPI + React + SQLite + Jaccard 关键词匹配 |
| AI 辅助开发范围 | 代码生成、调试、部署配置、Bug 修复；核心方案设计和问题排查由候选人独立完成 |

## 技术栈

| 模块 | 技术 |
| :--- | :--- |
| 前端 | React 18 + Ant Design 6 + Vite |
| 后端 | FastAPI + SQLAlchemy |
| 数据库 | SQLite |
| 异步任务 | ThreadPoolExecutor |
| 语音识别 | OpenAI Whisper API / 阿里云 DashScope Paraformer |
| 语义分段 | 规则分词 / LLM（可降级） |
| 素材匹配 | Jaccard 关键词相似度 |
| 关键词提取 | jieba TF-IDF |
| 部署 | 前端 GitHub Pages / 后端 Render |

## 匹配策略说明

采用 **Jaccard 相似度** 对字幕片段关键词与素材标签进行匹配。策略选择理由：

- **可解释性强**：匹配理由可以直接显示交集关键词，用户能理解为什么推荐该素材
- **无需外部服务**：不依赖向量数据库或 Embedding API
- **实现简单**：适合 Demo 阶段的快速验证

**降级方案**：外部 AI 服务不可用时，后端自动切换到基于 jieba 分词 + TF-IDF 的关键词提取和标点分句规则分段。

## 公网地址

- **前端**：https://liudunyu666.github.io/ai-subtitle-matching-platform/
- **后端**：https://ai-subtitle-backend-90pz.onrender.com

## 项目结构

```
├── backend/
│   ├── app.py                  # FastAPI 应用入口与路由
│   ├── config.py               # 配置
│   ├── gunicorn.conf.py        # Gunicorn 生产部署配置
│   ├── requirements.txt        # Python 依赖
│   ├── models/db.py            # 数据库模型（Task, Material）
│   ├── services/
│   │   ├── asr_service.py      # 语音识别服务（OpenAI / DashScope）
│   │   ├── llm_service.py      # LLM 分段服务
│   │   ├── matching_service.py # 素材匹配服务
│   │   ├── segmentation_service.py # 规则分段与关键词
│   │   └── tag_service.py      # 素材标签自动生成
│   └── uploads/                # 上传文件存储
├── frontend/
│   ├── src/
│   │   ├── api/index.js        # API 接口封装
│   │   ├── pages/
│   │   │   ├── TaskList.jsx    # 任务列表页
│   │   │   ├── Upload.jsx      # 新建任务页
│   │   │   ├── TaskDetail.jsx  # 任务详情页（分段、匹配、选择素材）
│   │   │   └── Materials.jsx   # 素材库页
│   │   └── App.jsx             # 应用入口与路由
│   ├── dist/                   # 构建产物（GitHub Pages 部署）
│   └── package.json
├── README.md
├── render.yaml
└── recruitment-practical-assignment.md
```

## 启动方法

### 后端

```bash
cd backend
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 5000 --reload
```

后端默认运行在 `http://localhost:5000`

生产环境（Render）使用 Gunicorn + Uvicorn Worker：

```bash
cd backend
gunicorn app:app -c gunicorn.conf.py
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

前端默认运行在 `http://localhost:3000`，API 请求自动代理到后端。

## 部署方式

### 后端（Render）

1. 在 Render 中创建 Web Service
2. 构建命令：`cd backend && pip install -r requirements.txt`
3. 启动命令：`gunicorn app:app -c gunicorn.conf.py`
4. 设置环境变量：
   - `DASHSCOPE_API_KEY`（阿里云百炼，用于语音识别）
   - `OPENAI_API_KEY`（可选，用于 LLM 分段备选）
   - `PUBLIC_BASE_URL`（后端公网地址，如 `https://your-app.onrender.com`）
   - `SECRET_KEY`（应用密钥）

### 前端（GitHub Pages）

```bash
cd frontend
npm run build
```

将 `frontend/dist` 部署到 GitHub Pages，SPA 路由通过 `404.html` fallback 处理。

## API 接口

| 方法 | 路径 | 说明 |
| :--- | :--- | :--- |
| POST | /api/tasks | 创建任务（支持文件上传和文本） |
| GET | /api/tasks | 任务列表 |
| GET | /api/tasks/:id | 任务详情 |
| POST | /api/tasks/:id/retry | 重试失败任务 |
| PUT | /api/tasks/:id/segments | 更新分段 |
| POST | /api/tasks/:id/segments/:seg_id/select | 选择素材 |
| GET | /api/materials | 素材列表（支持 ?keyword= 搜索） |
| POST | /api/materials | 上传素材 |
| DELETE | /api/materials/:id | 删除素材 |
| GET | /api/materials/suggest-tags | 自动生成标签 |
| POST | /api/parse-subtitle | 纯文本解析（同步，绕过 ASR） |

所有接口返回统一格式：`{ "code": 0, "data": {}, "msg": "" }`

## 测试步骤

1. 访问前端首页，查看任务列表（初始为空）
2. 点击「新建任务」进入上传页
3. 选择「粘贴字幕文本」模式，填入示例文本或自定义文本
4. 点击「创建任务」，等待处理完成
5. 在任务详情页查看分段结果和候选素材
6. 点击候选素材为每个分段选择最终素材
7. 编辑分段文本或调整顺序
8. 点击「保存修改」持久化
9. 刷新页面确认结果保留
10. 进入「素材库」查看预置素材，支持搜索和上传新素材

## 异常处理

| 场景 | 处理方式 |
| :--- | :--- |
| 语音识别失败（文件上传） | 提示 ASR 错误，允许粘贴字幕文本作为备选 |
| LLM 不可用 | 自动切换规则分词 + TF-IDF |
| API 返回异常 | 全局错误提示，不影响其他操作 |
| 任务超时 | 120 秒后标记失败 |
| 重复上传 | 文件 MD5 去重 |
| 后台标签页 | 自动暂停轮询，切回时立即恢复 |
| 删除素材 | 二次确认弹窗，防止误删 |

## 环境变量

| 变量 | 说明 |
| :--- | :--- |
| OPENAI_API_KEY | OpenAI API 密钥 |
| DASHSCOPE_API_KEY | 阿里云百炼 API 密钥 |
| PUBLIC_BASE_URL | 后端公网地址（DashScope ASR 需要，如 https://your-app.onrender.com） |
| DATABASE_URL | 数据库连接（默认 sqlite:///smp.db） |
| SECRET_KEY | 应用密钥 |

## 已完成功能

- [x] 上传视频/音频/粘贴字幕文本
- [x] 语音识别转字幕（OpenAI Whisper / 阿里云 DashScope Paraformer）
- [x] 异步任务处理 + 进度展示
- [x] 任务失败查看原因 + 重试
- [x] 字幕语义分段 + 关键词提取
- [x] 人工编辑文本 + 拖拽排序
- [x] 素材库（12 个预置素材，支持搜索/上传/删除）
- [x] 智能素材匹配（每片段 ≥3 候选 + 匹配理由）
- [x] 人工替换素材 + 持久化保存
- [x] 自动为素材生成标签
- [x] AI 服务失败自动降级
- [x] 重复任务检测（MD5 去重）
- [x] 任务超时处理
- [x] 素材搜索结果显示匹配度与匹配理由
- [x] 删除素材二次确认，防止误删
- [x] 页面不可见时暂停轮询，减少无用请求
- [x] 任务全部完成后自动停止轮询

## 已知问题与优化方向

| 问题 | 影响 | 计划 |
| :--- | :--- | :--- |
| 匹配仅基于关键词 Jaccard | 语义理解不足 | 升级为向量相似度（Sentence-BERT） |
| 无视频时间轴预览 | 无法结合时间线 | 集成 video.js |
| 无用户登录 | 多用户隔离缺失 | 增加 JWT 认证 |
| 素材仅本地存储 | 扩展性差 | 接入云存储 OSS |
| 仅支持关键词搜索 | 语义搜索缺失 | 集成 Embedding 全文搜索 |
| DashScope ASR 需公网文件 URL | 国内服务器无法访问 Render | 提供粘贴文字备选方案 |
| 无单元测试 | 回归验证依赖人工 | 增加 pytest + 前端测试 |
