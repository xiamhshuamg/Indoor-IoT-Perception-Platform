# 基于物联网的室内感知平台 (Indoor IoT Perception Platform)

## 项目简介

本项目是一个面向课程实践的物联网室内环境监测平台，旨在模拟真实室内环境数据的采集、处理、可视化与联动控制。系统通过模拟数据引擎生成温度、湿度、CO₂、PM2.5、光照等指标的连续变化数据，并叠加昼夜效应、特殊事件扰动，使数据更贴近真实场景。平台实现了实时监测、阈值告警、事件化管理、执行器控制、自动化规则触发及数据持久化，形成“感知→传输→处理→展示→控制→反馈”的完整闭环，适用于物联网课程教学与实验演示。

## 技术栈

- **前端**：Vue 3 + Vue Router + Pinia + Tailwind CSS + ECharts
- **后端**：Python 3.9+ + FastAPI + WebSocket + MySQL驱动 + asyncio
- **数据库**：MySQL 8.0
- **通信协议**：RESTful API + WebSocket
- **开发工具**：PyCharm / WebStorm, Postman, Git

## 功能特性

- **实时监测**：多房间、多传感器数据实时刷新，支持趋势曲线可视化。
- **告警事件化**：基于阈值规则生成告警事件，支持单条/批量确认，事件可追溯。
- **执行器控制**：模拟灯光、新风、净化、目标温度等控制，控制效果可在后续数据中观察。
- **自动化规则**：支持阈值条件、时间条件、复合条件规则配置，自动触发动作并记录日志。
- **配置管理**：传感器阈值、房间映射等关键参数可动态配置，无需修改代码。
- **数据持久化**：传感器读数、告警事件、系统配置均存入MySQL，支持历史查询与审计。
- **实时推送**：WebSocket主动推送最新数据和告警，前端即时更新。
- **接口文档**：自动生成Swagger UI（/docs），便于联调与测试。

## 快速开始

### 环境要求

- Node.js 18+ 和 npm
- Python 3.9+
- MySQL 8.0
- Git

### 安装步骤

1. **克隆仓库**
   ```bash
   git clone https://github.com/your-repo/indoor-iot-platform.git
   cd indoor-iot-platform
   ```

2. **后端配置**
   - 进入后端目录：`cd backend`
   - 创建虚拟环境并安装依赖：
     ```bash
     python -m venv venv
     source venv/bin/activate  # Windows: venv\Scripts\activate
     pip install -r requirements.txt
     ```
   - 复制环境变量模板并修改数据库连接信息：
     ```bash
     cp .env.example .env
     # 编辑 .env 文件，填入正确的 MySQL 地址、端口、用户名、密码和数据库名
     ```
   - 初始化数据库（需先创建对应数据库）：
     ```bash
     # 手动执行SQL脚本或等待系统自动建表（系统启动时会自动创建表结构）
     ```

3. **前端配置**
   - 进入前端目录：`cd ../frontend`
   - 安装依赖：
     ```bash
     npm install
     ```
   - 修改API地址（如需）：编辑 `src/lib/config.js` 或 `.env` 文件，确保 `VITE_API_BASE_URL` 指向正确的后端地址。

### 运行

1. **启动后端**
   ```bash
   cd backend
   source venv/bin/activate  # Windows: venv\Scripts\activate
   uvicorn main:app --host 127.0.0.1 --port 8003 --reload
   ```
   出现 `Application startup complete` 表示启动成功，可访问 `http://127.0.0.1:8003/docs` 查看接口文档。

2. **启动前端**
   ```bash
   cd frontend
   npm run dev
   ```
   默认运行在 `http://localhost:5173`，打开浏览器即可访问系统。

## 项目结构

```
indoor-iot-platform/
├── backend/                # 后端代码
│   ├── main.py             # 服务入口，FastAPI应用
│   ├── data.py             # 数据模型、模拟引擎、业务逻辑
│   ├── requirements.txt    # Python依赖
│   ├── .env.example        # 环境变量模板
│   └── ...
├── frontend/               # 前端代码
│   ├── public/             # 静态资源
│   ├── src/
│   │   ├── components/     # 可复用组件
│   │   ├── pages/          # 页面级组件
│   │   ├── lib/            # API封装、WebSocket管理、状态管理
│   │   ├── router/         # 路由配置
│   │   ├── styles/         # 全局样式
│   │   ├── App.vue
│   │   └── main.js
│   ├── package.json
│   └── ...
└── README.md
```

## 使用说明

1. **总览页**：查看全局传感器统计、核心指标仪表盘和房间对比图。
2. **房间详情**：点击某个房间进入，查看该房间所有传感器实时值、趋势曲线，并可对执行器进行控制。
3. **告警中心**：查看所有未确认/已确认告警，支持确认操作。
4. **自动化**：查看、新增、编辑、删除自动化规则，可手动测试规则或查看触发记录。
5. **设置**：配置传感器阈值、房间映射等参数。

## 测试

- **外部行为测试**：参考文档第6.4.1节，可手动执行控制、确认等操作验证功能。
- **内部逻辑测试**：后端提供自动化测试用例，运行 `pytest` 可快速回归核心链路。

## 贡献指南

欢迎提交Issue或Pull Request。请确保代码风格符合项目规范，并补充必要的测试用例。

## 许可证

本项目仅供教学与学习使用，未经许可不得用于商业用途。

---

**项目状态**：课程设计完成，功能闭环可演示，后续可扩展真实硬件接入与安全权限控制。


<img width="194" height="374" alt="image" src="https://github.com/user-attachments/assets/6c42beea-1559-420b-a10f-78665ef448e6" />
<img width="693" height="357" alt="image" src="https://github.com/user-attachments/assets/f541ca1e-26f3-4794-a008-d4eae9923ff6" />
<img width="627" height="355" alt="image" src="https://github.com/user-attachments/assets/321159ba-6a26-4ba6-ab17-70296269aa1d" />
<img width="655" height="316" alt="image" src="https://github.com/user-attachments/assets/c5ee436d-47ff-469b-b951-1027b515167e" />
<img width="656" height="347" alt="image" src="https://github.com/user-attachments/assets/1df01f68-5e9c-4256-bfa1-f67035e02979" />
<img width="692" height="358" alt="image" src="https://github.com/user-attachments/assets/a729ef1c-60da-4ecd-9bf3-d7edff56f3ca" />
<img width="631" height="331" alt="image" src="https://github.com/user-attachments/assets/05132fe2-1e35-437e-aed4-3fc3d98821cc" />





