# AI 字幕分析与素材匹配平台

## 项目简介

用户上传口播视频、音频或粘贴字幕文本后，系统自动完成字幕整理、语义分段、关键词提取，并从素材库中推荐与字幕内容匹配的图片/视频素材，支持人工调整并持久化保存。

## 技术栈

| 模块 | 技术 |
| :--- | :--- |
| 前端 | React 18 + Ant Design 6 + Vite |
| 后端 | Flask + SQLAlchemy |
| 数据库 | SQLite |
| 异步任务 | ThreadPoolExecutor |
| 语音识别 | OpenAI Whisper API（可降级） |
| 语义分段 | 规则分词 / LLM（可降级） |
| 素材匹配 | Jaccard 关键词相似度 |
| 关键词提取 | jieba TF-IDF |

## 匹配策略说明

采用 **Jaccard 相似度** 对字幕片段关键词与素材标签进行匹配。策略选择理由：

- **可解释性强**：匹配理由可以直接显示交集关键词，用户能理解为什么推荐该素材
- **无需外部服务**：不依赖向量数据库或 Embedding API
- **实现简单**：适合 Demo 阶段的快速验证

**降级方案**：外部 AI 服务不可用时，后端自动切换到基于 jieba 分词 + TF-IDF 的关键词提取和标点分句规则分段。

## 项目结构

```
├── backend/
│   ├── app.py                  # Flask 应用入口与路由
│   ├── config.py               # 配置
│   ├── requirements.txt        # Python 依赖
│   ├── models/db.py            # 数据库模型（Task, Material）
│   ├── services/
│   │   ├── asr_service.py      # 语音识别服务
│   │   ├── llm_service.py      # LLM 分段服务
│   │   ├── matching_service.py # 素材匹配服务
│   │   └── segmentation_service.py # 规则分段与关键词
│   └── uploads/                # 上传文件存储
├── frontend/
│   ├── src/
│   │   ├── api/index.js        # API 接口封装
│   │   ├── pages/
│   │   │   ├── TaskList.jsx    # 任务列表页
│   │   │   ├── Upload.jsx      # 新建任务页
│   │   │   ├── TaskDetail.jsx  # 任务详情页
│   │   │   └── Materials.jsx   # 素材库页
│   │   └── App.jsx             # 应用入口与路由
│   └── package.json
└── README.md
```

## 启动方法

### 后端

```bash
cd backend
pip install -r requirements.txt
python app.py
```

后端默认运行在 `http://localhost:5000`

### 前端

```bash
cd frontend
npm install
npm run dev
```

前端默认运行在 `http://localhost:3000`，API 请求自动代理到后端。

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

## API 接口

| 方法 | 路径 | 说明 |
| :--- | :--- | :--- |
| POST | /api/tasks | 创建任务（支持文件上传和文本） |
| GET | /api/tasks | 任务列表 |
| GET | /api/tasks/:id | 任务详情 |
| PUT | /api/tasks/:id/segments | 更新分段 |
| POST | /api/tasks/:id/segments/:seg_id/select | 选择素材 |
| GET | /api/materials | 素材列表（支持 ?keyword= 搜索） |
| POST | /api/materials | 上传素材 |
| DELETE | /api/materials/:id | 删除素材 |
| POST | /api/parse-subtitle | 纯文本解析（同步，绕过 ASR） |

所有接口返回统一格式：`{ "code": 0, "data": {}, "msg": "" }`

## 异常处理

| 场景 | 处理方式 |
| :--- | :--- |
| 语音识别失败 | 前端提示并允许粘贴字幕文本 |
| LLM 不可用 | 自动切换规则分词 + TF-IDF |
| 网络异常 | Axios 自动重试 |
| 任务超时 | 120 秒后标记失败 |
| 重复上传 | 文件 MD5 去重 |

## 环境变量

| 变量 | 说明 |
| :--- | :--- |
| OPENAI_API_KEY | OpenAI API 密钥（可选，用于 ASR 和 LLM 分段） |
| DATABASE_URL | 数据库连接（默认 sqlite:///smp.db） |
| SECRET_KEY | Flask 密钥 |

## 已知问题与优化方向

| 问题 | 影响 | 计划 |
| :--- | :--- | :--- |
| 匹配仅基于关键词 Jaccard | 语义理解不足 | 升级为向量相似度（Sentence-BERT） |
| 无视频时间轴预览 | 无法结合时间线 | 集成 video.js |
| 无用户登录 | 多用户隔离缺失 | 增加 JWT 认证 |
| 素材仅本地存储 | 扩展性差 | 接入云存储 OSS |
| 仅支持关键词搜索 | 语义搜索缺失 | 集成 Embedding 全文搜索 |
