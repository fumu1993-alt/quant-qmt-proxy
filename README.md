# xtquant-proxy

> 🚧 **开发状态**: v0.1.0 迭代中 | 当前版本覆盖 REST/gRPC/WebSocket 多协议，支持多策略并行管理

<div align="center">

**基于 FastAPI + gRPC + WebSocket 的 xtquant 量化交易代理服务**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![gRPC](https://img.shields.io/badge/gRPC-1.60+-orange.svg)](https://grpc.io/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

提供 **RESTful API**、**gRPC** 与 **WebSocket** 多协议接口，封装国金 QMT xtquant SDK 的数据和交易功能

**✨ v0.1.0 新增：多策略并行管理** — 策略调度器、虚拟账户隔离、订单策略标识

[快速开始](#-快速开始) • [多策略管理](#-多策略管理) • [API 文档](#-api接口说明) • [技术架构](#-技术架构)

</div>

---

## ✨ 核心特性

### 🎯 多协议支持
- 🌐 **REST API**: 基于 FastAPI，提供 HTTP/HTTPS 接口，自动生成 Swagger 文档
- ⚡ **gRPC**: 高性能 RPC 框架，支持流式调用和双向通信
- 🔔 **WebSocket**: 提供行情订阅实时推送，内置心跳与限流控制
- 🔄 **统一服务**: 多种协议共享相同的业务逻辑层，一次部署同时服务

### 📊 多策略并行管理（v0.1.0 新增）
- 🎮 **策略调度器**: 完整的生命周期管理 — 注册 / 启动 / 暂停 / 停止
- 💰 **虚拟账户隔离**: 每个策略独立管理资金和持仓，互不干扰
- 🏷️ **订单策略标识**: 所有订单携带 `strategy_id`，支持按策略查询和追踪
- 📈 **策略盈亏报告**: 实时计算每个策略的已实现/未实现盈亏、胜率
- 🛡️ **风控保护**: 超限直接拒绝下单，资金不足不允许买入

### 🛡️ 安全可靠
- 🔐 **API Key 认证**: 多环境 API Key 管理
- 🚦 **交易拦截**: dev 模式自动拦截真实交易，保护账户安全
- 📝 **完整日志**: 基于 Loguru 的结构化日志，支持日志轮转和压缩
- 🔒 **异常保护**: 全局异常处理，xtdata 连接超时保护

### 📊 功能完整
- 📈 **市场数据**: K线、分时、tick、财务数据、板块数据、行情订阅
- 💼 **交易功能**: 下单、撤单、持仓查询、订单管理
- ❤️ **健康检查**: REST 和 gRPC 双协议健康检查
- 🎯 **三种模式**: mock/dev/prod 灵活切换

---

## 📁 项目结构

```
quant-qmt-proxy/
├── app/
│   ├── main.py                 # FastAPI 应用入口
│   ├── grpc_server.py          # gRPC 服务器入口
│   ├── grpc_client.py          # gRPC 客户端封装
│   ├── config.py               # 配置管理（单例）
│   ├── dependencies.py         # 依赖注入（单例服务）
│   ├── models/                 # Pydantic 数据模型
│   │   ├── data_models.py      # 数据相关模型
│   │   ├── trading_models.py   # 交易相关模型（含 strategy_id）
│   │   └── strategy_models.py  # 策略管理模型 ✨ NEW
│   ├── routers/                # REST API 路由
│   │   ├── data.py             # 数据服务 API
│   │   ├── trading.py          # 交易服务 API
│   │   ├── health.py           # 健康检查 API
│   │   ├── websocket.py        # WebSocket 行情推送
│   │   └── strategy.py         # 策略管理 API ✨ NEW
│   ├── grpc_services/          # gRPC 服务实现
│   │   ├── data_grpc_service.py
│   │   ├── trading_grpc_service.py
│   │   └── health_grpc_service.py
│   ├── services/               # 业务服务层（REST 和 gRPC 共享）
│   │   ├── data_service.py     # 数据服务（xtdata 封装）
│   │   ├── trading_service.py  # 交易服务（xttrader 封装）
│   │   ├── subscription_manager.py  # 行情订阅管理器
│   │   ├── strategy_manager.py      # 策略调度器 ✨ NEW
│   │   └── virtual_account_manager.py  # 虚拟账户管理器 ✨ NEW
│   └── utils/                  # 工具函数
│       ├── exceptions.py       # 自定义异常
│       ├── helpers.py          # 辅助函数
│       └── logger.py           # 日志配置
├── proto/                      # Protocol Buffers 定义
├── generated/                  # protobuf 生成的 Python 代码
├── tests/                      # 测试套件
├── xtquant/                    # xtquant SDK（国金 QMT）请自行下载
├── scripts/                    # 工具脚本
├── config.yml                  # 统一配置文件
├── requirements.txt            # Python 依赖
├── run.py                      # 启动脚本
└── README.md
```

---

## 🚀 快速开始

### 1. 前置要求

- **Python 3.10+**
- **国金 QMT 客户端**（dev/prod 模式需要）
- **Windows 系统**（QMT 仅支持 Windows）

### 2. 安装依赖

```bash
# 创建虚拟环境（推荐）
python -m venv .venv
.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置 QMT 路径

编辑 `config.yml`，修改 QMT 安装路径：

```yaml
xtquant:
  qmt_userdata_path: "C:/quant/国金QMT交易端模拟/userdata_mini"
```

### 4. 启动服务

```powershell
# mock 模式 - 不连接 QMT，使用模拟数据（无需 QMT）
$env:APP_MODE="mock"; python run.py

# dev 模式 - 连接 QMT，获取真实数据，禁止交易（推荐开发使用）
$env:APP_MODE="dev"; python run.py

# prod 模式 - 连接 QMT，获取真实数据，允许交易（生产环境）
$env:APP_MODE="prod"; python run.py
```

### 5. 访问服务

| 服务 | 地址 | 说明 |
|------|------|------|
| **REST API** | http://localhost:8000 | RESTful API 主入口 |
| **gRPC** | localhost:50051 | gRPC 服务端口 |
| **Swagger UI** | http://localhost:8000/docs | 交互式 API 文档 |
| **ReDoc** | http://localhost:8000/redoc | API 文档（阅读友好） |
| **健康检查** | http://localhost:8000/health/ | 服务健康状态 |
| **WebSocket 测试页** | http://localhost:8000/ws/test | 行情推送调试页面 |

---

## 📊 多策略管理

### 架构设计

```
                    ┌─────────────────────────────┐
                    │    Strategy Manager (调度器)   │
                    │  策略注册/启动/停止/生命周期     │
                    └──────────┬──────────────────┘
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                  │
    ┌───────▼──────┐  ┌───────▼──────┐  ┌───────▼──────┐
    │  策略A 虚拟账户 │  │  策略B 虚拟账户 │  │  策略C 虚拟账户 │
    │  分配: 30万    │  │  分配: 40万    │  │  分配: 30万    │
    │  独立持仓/订单  │  │  独立持仓/订单  │  │  独立持仓/订单  │
    └───────┬──────┘  └───────┬──────┘  └───────┬──────┘
            │                  │                  │
            └──────────────────┼──────────────────┘
                               │
                    ┌──────────▼──────────────────┐
                    │  TradingService (交易服务)     │
                    │  注入 strategy_id 到订单       │
                    └──────────┬──────────────────┘
                               │
                          QMT xtquant
```

### 核心规则

| 规则 | 说明 |
|------|------|
| **同股多策略** | 同一只股票可被多个策略同时持有，各自独立管理 |
| **固定金额分配** | 每个策略分配固定的资金金额，互不借用 |
| **超限拒绝** | 资金不足/持仓超限时直接拒绝下单 |

### 使用流程

#### 第 1 步：注册策略

```bash
POST /api/v1/strategy/register
```
```json
{
    "strategy_name": "均线突破策略",
    "strategy_type": "TREND_FOLLOWING",
    "allocated_capital": 300000,
    "max_positions": 5,
    "max_single_position_ratio": 0.3,
    "description": "基于20日均线突破的趋势跟踪策略"
}
```

#### 第 2 步：启动策略

```bash
POST /api/v1/strategy/{strategy_id}/start
```

#### 第 3 步：带策略标识下单

```bash
POST /api/v1/trading/order/{session_id}
```
```json
{
    "stock_code": "000001.SZ",
    "side": "BUY",
    "volume": 1000,
    "price": 13.50,
    "strategy_id": "strategy_a1b2c3d4",
    "strategy_name": "均线突破策略"
}
```

#### 第 4 步：查看策略状态

```bash
# 策略详情
GET /api/v1/strategy/{strategy_id}/status

# 策略虚拟持仓
GET /api/v1/strategy/{strategy_id}/positions

# 策略盈亏报告
GET /api/v1/strategy/{strategy_id}/pnl
```

#### 其他操作

```bash
# 暂停策略（保留持仓，停止新交易）
POST /api/v1/strategy/{strategy_id}/pause

# 停止策略（force_liquidate=true 时提示需平仓的股票）
POST /api/v1/strategy/{strategy_id}/stop
{"force_liquidate": true}

# 列出所有策略
GET /api/v1/strategy/list
```

### 策略生命周期

```
REGISTERED → RUNNING → PAUSED → STOPPED
  (已注册)    (运行中)   (已暂停)   (已停止)
     │           │         │
     └─ start ──┘         │
                 └─ stop ─┘
                          └─ 自动注销虚拟账户
```

### 风控检查

下单时系统自动进行以下检查（任一不通过即拒绝）：

1. ✅ 策略状态必须为 `RUNNING`
2. ✅ 持仓数量不超过 `max_positions`（已持有的股票加仓不计数）
3. ✅ 单股仓位不超过 `allocated_capital × max_single_position_ratio`
4. ✅ 可用资金 ≥ 订单金额

---

## 🎯 运行模式说明

| 模式 | 连接 xtquant | 真实交易 | 使用场景 |
|------|------------|---------|---------|
| **mock** | ❌ 否 | ❌ 禁止 | 开发测试，无需 QMT 客户端 |
| **dev** | ✅ 是 | ❌ 禁止 | 开发调试，获取真实数据但不下单 |
| **prod** | ✅ 是 | ✅ 允许 | 生产环境，真实交易 |

---

## 📡 API 接口说明

### 策略管理 API (`/api/v1/strategy/`) ✨ NEW

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/strategy/register` | 注册策略 |
| POST | `/api/v1/strategy/{id}/start` | 启动策略 |
| POST | `/api/v1/strategy/{id}/pause` | 暂停策略 |
| POST | `/api/v1/strategy/{id}/stop` | 停止策略 |
| GET | `/api/v1/strategy/list` | 列出所有策略 |
| GET | `/api/v1/strategy/{id}/status` | 策略详情 |
| GET | `/api/v1/strategy/{id}/pnl` | 盈亏报告 |
| GET | `/api/v1/strategy/{id}/positions` | 策略虚拟持仓 |
| GET | `/api/v1/strategy/{id}/orders` | 策略订单统计 |

### 数据服务 (`/api/v1/data/`)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/data/market` | 获取市场行情数据 |
| POST | `/api/v1/data/financial` | 获取财务数据 |
| GET | `/api/v1/data/sectors` | 获取板块列表 |
| POST | `/api/v1/data/sector` | 获取板块成分股 |
| POST | `/api/v1/data/index-weight` | 获取指数权重 |
| GET | `/api/v1/data/trading-calendar/{year}` | 获取交易日历 |
| GET | `/api/v1/data/instrument/{stock_code}` | 获取合约信息 |
| GET | `/api/v1/data/etf/{etf_code}` | 获取 ETF 基础信息 |
| POST | `/api/v1/data/subscription` | 创建行情订阅 |
| GET | `/api/v1/data/subscription/{id}` | 查询订阅详情 |
| GET | `/api/v1/data/subscriptions` | 获取订阅列表 |
| DELETE | `/api/v1/data/subscription/{id}` | 取消订阅 |

### 交易服务 (`/api/v1/trading/`)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/trading/connect` | 连接交易账户 |
| POST | `/api/v1/trading/disconnect/{session_id}` | 断开账户 |
| GET | `/api/v1/trading/account/{session_id}` | 获取账户信息 |
| GET | `/api/v1/trading/positions/{session_id}` | 获取持仓信息 |
| POST | `/api/v1/trading/order/{session_id}` | 提交订单（支持 strategy_id）|
| POST | `/api/v1/trading/cancel/{session_id}` | 撤销订单 |
| GET | `/api/v1/trading/orders/{session_id}` | 获取订单列表 |
| GET | `/api/v1/trading/trades/{session_id}` | 获取成交记录 |
| GET | `/api/v1/trading/asset/{session_id}` | 获取资产信息 |
| GET | `/api/v1/trading/risk/{session_id}` | 获取风险指标 |
| GET | `/api/v1/trading/strategies/{session_id}` | 获取策略列表 |
| GET | `/api/v1/trading/status/{session_id}` | 查询连接状态 |

### gRPC 接口

#### 数据服务 (DataService)
- `GetMarketData()` / `GetFinancialData()` / `GetSectorList()` / `GetStockListInSector()`
- `GetIndexWeight()` / `GetTradingCalendar()` / `GetInstrumentDetail()`
- `SubscribeQuote()` / `SubscribeWholeQuote()` / `UnsubscribeQuote()`
- `GetSubscriptionInfo()` / `ListSubscriptions()`

#### 交易服务 (TradingService)
- `Connect()` / `Disconnect()` / `GetAccountInfo()` / `GetPositions()`
- `SubmitOrder()` / `CancelOrder()` / `GetOrders()` / `GetTrades()`
- `GetAsset()` / `GetRiskInfo()` / `GetStrategies()`

#### 健康检查服务 (HealthService)
- `Check()` / `Watch()`

### WebSocket 接口
- `GET /ws/quote/{subscription_id}` — 行情订阅推送
- `GET /ws/test` — 内置测试页面

---

## 🔧 技术架构

### 核心技术栈
- **FastAPI**: 现代高性能 Web 框架
- **gRPC**: 高性能 RPC 框架
- **Protocol Buffers**: 数据序列化协议
- **Pydantic**: 数据验证和序列化
- **uvicorn**: ASGI 服务器
- **Loguru**: 结构化日志库
- **xtquant**: 国金 QMT Python SDK

### 设计模式
- ✅ **依赖注入**: 使用 FastAPI 的 Depends 系统
- ✅ **单例模式**: 服务实例全局唯一，避免重复初始化
- ✅ **策略模式**: 不同模式下的不同行为
- ✅ **拦截器模式**: 交易请求拦截保护
- ✅ **适配器模式**: REST 和 gRPC 共享业务逻辑
- ✅ **虚拟账户模式**: 多策略资金/持仓隔离 ✨ NEW

---

## ⚠️ 注意事项

### 安全警告
- ⚠️ **生产环境必须修改默认 API Key**
- ⚠️ **prod 模式会真实下单，请谨慎使用**
- ⚠️ **不要将包含真实账号密码的配置文件提交到 Git**

### 已知限制
- **xtquant 仅支持 Windows 系统**
- 需要 QMT 客户端正在运行（dev/prod 模式）
- 虚拟账户的资金管理为应用层逻辑，不绑定真实账户资金
- 多策略对同一股票的卖出需确保各自可用数量足够

---

## 🐛 故障排查

### 服务启动失败
1. 检查 Python 版本 >= 3.10
2. 确认所有依赖已安装: `pip install -r requirements.txt`
3. 检查端口 8000 和 50051 是否被占用

### 策略下单被拒绝
1. 确认策略状态为 `RUNNING`（通过 `/api/v1/strategy/list` 查看）
2. 检查策略可用资金（通过 `/api/v1/strategy/{id}/status` 查看）
3. 检查是否超过 `max_positions` 或 `max_single_position_ratio`
4. 查看 `logs/app.log` 中的拒绝原因

### gRPC 连接失败
1. 确认 gRPC 服务已启动
2. 检查端口 50051 是否被占用
3. 确认防火墙设置

---

## 🤝 贡献指南

```bash
git clone https://github.com/fumu1993-alt/quant-qmt-proxy.git
cd quant-qmt-proxy
pip install -r requirements.txt
python scripts/generate_proto.py
pytest tests/ -v
```

### 提交规范
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建/工具相关

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

<div align="center">

**如果觉得项目有帮助，请给个 ⭐ Star 支持一下！**

</div>