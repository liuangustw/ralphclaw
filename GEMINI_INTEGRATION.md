# Ralph-Claw × Gemini Free Tier Integration

## 配置

你有 3 個 Gemini Free Tier API keys，對應三個角色：

```bash
# .env 中
GEMINI_API_KEYS_FREE_TIER_1 → Architect（任務拆解）
GEMINI_API_KEYS_FREE_TIER_2 → Builder（代碼生成）
GEMINI_API_KEYS_FREE_TIER_3 → Replanner（失敗重新規劃）
```

## 運行完整循環

```bash
cd /opt/ralphclaw
export $(cat .env | xargs)

# 初始化任務（第一次）
python3 scripts/update_state.py init

# 運行完整循環（自動 Architect → Builder → Verifier → Replanner）
bash scripts/run_full_loop.sh
```

## 三層 LLM 架構

### 1️⃣ Architect（Gemini Free Tier 1）
- 讀規格、TASKS.json、失敗摘要
- 選擇最適合的原子任務
- 若任務失敗過多，自動重新切分
- **輸出**: CURRENT_TASK.json

### 2️⃣ Builder（Gemini Free Tier 2）
- 讀最小 context（只看相關代碼）
- 寫代碼、生成補丁
- 遵守 allowed_files 範圍限制
- **輸出**: unified diff 補丁

### 3️⃣ Verifier（自動化）
- 執行測試、檢查 lint
- 驗證補丁範圍
- **輸出**: FAILURE_SUMMARY.json（PASS/FAIL/ESCALATE）

### 4️⃣ Replanner（Gemini Free Tier 3，條件性）
- 只在 Builder 失敗時觸發
- 分析失敗原因
- 將任務重新切成 1-3 個小任務
- **輸出**: REPLAN_PROPOSAL.json

## 成本分析

| 情況 | Architect | Builder | Replanner | 總計 |
|------|-----------|---------|-----------|------|
| 任務通過（第一次） | 1 | 1 | 0 | **2 次** |
| 任務失敗 + 重試 | 1 | 2 | 1 | **4 次** |
| 3 個連續任務都通過 | 3 | 3 | 0 | **6 次** |

**Free Tier 配額**: 每個 API key 有 15 RPM（requests per minute）和 1.5M tokens/day 限制

## 運行單個角色（調試）

```bash
# Architect
bash scripts/run_architect.sh

# Builder
bash scripts/run_builder.sh

# Verifier
bash scripts/run_verifier.sh

# Replanner
bash scripts/run_replanner.sh
```

## 檔案結構

```
state/
├── CURRENT_TASK.json       # Architect 選擇的任務
├── FAILURE_SUMMARY.json    # Verifier 的測試結果
├── REPLAN_PROPOSAL.json    # Replanner 的重新規劃
└── TASKS.json              # 所有任務清單

artifacts/
├── architect_raw_output.txt # Gemini Architect 原始回應
├── builder_raw_output.txt   # Gemini Builder 原始回應
├── last_patch.diff          # Builder 生成的補丁
└── test.out / lint.out      # Verifier 檢查結果
```

## 故障排查

### 「Error: GEMINI_API_KEYS_FREE_TIER_X not set」
確保 .env 中有對應的 key：
```bash
grep "GEMINI_API_KEYS" .env
```

### 「Could not parse architect response as JSON」
- Gemini 沒有返回有效的 JSON
- 可能是 API 配額用完（Free Tier 有限制）
- 檢查錯誤日誌：`cat artifacts/architect_raw_output.txt`

### 「Patch could not be applied cleanly」
- Builder 生成的補丁有問題
- 檢查 `artifacts/last_patch.diff` 格式
- 重新運行 Replanner 來重新切分任務

## 成本優化

1. **最小化 Architect 呼叫**：手動維護 TASKS.json，不用 Architect
   → 每個循環省 1 次調用

2. **Replanner 只在必要時觸發**：自動，無法禁用

3. **批量任務**：一次處理多個任務，充分利用 Free Tier 配額

## 與 Candice（Claude）的協作

當前設置：Gemini 三個角色，但你可以隨時介入：

```bash
# 檢查 Architect 選了什麼
jq . state/CURRENT_TASK.json

# 檢查 Builder 生成的補丁
cat artifacts/last_patch.diff

# 檢查 Verifier 的失敗原因
jq . state/FAILURE_SUMMARY.json

# 手動編輯任務（如果不同意 Architect）
nano state/CURRENT_TASK.json

# 手動編輯補丁（如果 Builder 有問題）
nano artifacts/last_patch.diff
```

## 下一步

1. 創建測試項目（sample app）
2. 寫 TASKS.json 清單
3. 運行 `bash scripts/run_full_loop.sh`
4. 觀察三個 Gemini API 的表現
5. 根據結果調整 prompts/
