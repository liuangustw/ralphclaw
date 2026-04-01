# Amazon Product Monitor - VPS 部署指南

## 🚀 現況狀態

**服務已部署並運行**

- **服務地址**: http://46.225.160.37:8080
- **狀態**: ✅ 正常運行
- **API 文檔**: 本文件

---

## 📡 API 端點

### 1. 首頁 / 狀態檢查
```
GET http://46.225.160.37:8080/
```
**回應**: 服務概況和可用端點列表

**範例**:
```bash
curl http://46.225.160.37:8080/
```

### 2. 獲取熱門商品
```
GET http://46.225.160.37:8080/api/trending?limit=20
```
**參數**:
- `limit` (可選): 結果數量，預設 20，最多 100

**回應**:
```json
{
  "status": "success",
  "count": 5,
  "products": [
    {
      "asin": "B0XXXXX",
      "title": "Product Name",
      "price": "$29.99",
      "rating": 4.5,
      "reviews": 150,
      "trending_score": 0.85,
      "trending_reason": "High review velocity..."
    }
  ],
  "timestamp": "2026-04-01T14:00:00.000000"
}
```

**範例**:
```bash
curl "http://46.225.160.37:8080/api/trending?limit=10"
```

### 3. 監控商家頁面
```
POST http://46.225.160.37:8080/api/monitor
Content-Type: application/json

{
  "url": "https://amazon.com/s?i=merchant-XXXXX"
}
```

**也支援 GET 參數**:
```
GET http://46.225.160.37:8080/api/monitor?url=https://amazon.com/s?i=merchant-XXXXX
```

**回應**:
```json
{
  "status": "success",
  "scraped": 42,
  "trending_count": 8,
  "trending": [...],
  "timestamp": "2026-04-01T14:00:00.000000"
}
```

**範例**:
```bash
curl -X POST http://46.225.160.37:8080/api/monitor \
  -H "Content-Type: application/json" \
  -d '{"url": "https://amazon.com/s?i=merchant-ABC123"}'
```

### 4. 查看商品價格歷史
```
GET http://46.225.160.37:8080/api/history?asin=B0XXXXX
```

**參數**:
- `asin` (必須): 商品 ASIN

**回應**:
```json
{
  "status": "success",
  "asin": "B0XXXXX",
  "title": "Product Name",
  "history_count": 5,
  "history": [
    {
      "price": "$29.99",
      "rating": 4.5,
      "reviews": 150,
      "snapshot_date": "2026-04-01T12:00:00"
    }
  ],
  "timestamp": "2026-04-01T14:00:00.000000"
}
```

**範例**:
```bash
curl "http://46.225.160.37:8080/api/history?asin=B0ABC12345"
```

### 5. 導出數據
```
GET http://46.225.160.37:8080/api/export?format=json&limit=50
```

**參數**:
- `format` (必須): `json` 或 `csv`
- `limit` (可選): 結果數量，預設 50，最多 100

**回應格式**:
- JSON: JSON 物件陣列
- CSV: CSV 格式（ASIN, Title, Trending Score, Reason）

**範例**:
```bash
# JSON 格式
curl "http://46.225.160.37:8080/api/export?format=json&limit=20"

# CSV 格式
curl "http://46.225.160.37:8080/api/export?format=csv&limit=20"
```

### 6. 服務狀態
```
GET http://46.225.160.37:8080/api/status
```

**回應**:
```json
{
  "status": "healthy",
  "service": "Amazon Product Monitor API",
  "version": "1.0.0",
  "database": {
    "path": "/opt/ralphclaw/data/products.db",
    "connected": true
  },
  "latest_trending": {...},
  "api_endpoints": [...],
  "timestamp": "2026-04-01T14:00:00.000000"
}
```

---

## 📊 使用範例

### 示例 1: 檢查服務是否運行
```bash
curl http://46.225.160.37:8080/api/status | jq .status
```

### 示例 2: 監控一個商家頁面並獲取趨勢商品
```bash
curl -X POST http://46.225.160.37:8080/api/monitor \
  -H "Content-Type: application/json" \
  -d '{"url": "https://amazon.com/s?i=merchant-A1234"}' \
  | jq '.trending[] | {title, trending_score}'
```

### 示例 3: 獲取最新的 30 個趨勢商品
```bash
curl "http://46.225.160.37:8080/api/trending?limit=30" | jq '.products[]'
```

### 示例 4: 導出 CSV 數據用於分析
```bash
curl "http://46.225.160.37:8080/api/export?format=csv&limit=100" > trending_products.csv
```

### 示例 5: 查看特定商品的價格歷史
```bash
curl "http://46.225.160.37:8080/api/history?asin=B0XXXXX" | jq '.history[]'
```

---

## 🔧 技術規格

| 項目 | 說明 |
|------|------|
| **主機** | ubuntu-4gb-nbg1-1 |
| **IP** | 46.225.160.37 |
| **埠** | 8080 |
| **框架** | Flask 3.1.3 |
| **數據庫** | SQLite3 |
| **Python** | 3.12 |
| **狀態** | ✅ 運行中 |

---

## 🐍 本地開發

如果要在本地運行服務:

```bash
cd /opt/ralphclaw
pip install -r requirements.txt
python3 -m flask --app app.web run --host 0.0.0.0 --port 8080
```

然後訪問: http://localhost:8080

---

## 📋 API 回應代碼

| 代碼 | 說明 |
|------|------|
| 200 | 成功 |
| 400 | 請求參數錯誤 |
| 404 | 資源未找到 |
| 500 | 伺服器錯誤 |

---

## ⚠️ 注意事項

1. **速率限制**: Web 爬蟲每分鐘最多 5 個請求（可配置）
2. **生產環境**: 當前使用 Flask 開發伺服器，應使用 Gunicorn/uWSGI 在生產環境
3. **數據庫**: SQLite 數據保存在 `/opt/ralphclaw/data/products.db`
4. **日誌**: Flask 日誌記錄到標準輸出

---

## 🚀 部署架構

```
VPS (46.225.160.37)
    ↓
Python Flask App (port 8080)
    ↓
├─ Web Scraper Module
├─ Product Analyzer
├─ SQLite Database
└─ API Endpoints
```

---

## 📞 故障排除

### 服務無響應
```bash
# 檢查進程
ps aux | grep flask

# 查看日誌
tail -f /tmp/flask.log

# 測試連接
curl http://46.225.160.37:8080/api/status
```

### 數據庫錯誤
```bash
# 檢查數據庫
ls -la /opt/ralphclaw/data/

# 驗證數據庫完整性
sqlite3 /opt/ralphclaw/data/products.db "SELECT COUNT(*) FROM products;"
```

---

**部署日期**: 2026-04-01
**最後更新**: 2026-04-01
