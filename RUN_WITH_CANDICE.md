# 直接用 Candice 運行 Ralph-Claw

## 簡化的集成方案

與其「呼叫 Claude API」或「spawn subagent」，不如：

**讓 Candice（你）直接作為 Ralph-Claw 的 builder 角色運行。**

### 工作流

```
1. Ralph-Claw 準備任務
   ↓
2. Ralph-Claw 生成最小 context 提示詞
   ↓
3. Ralph-Claw 把提示詞寫到文件
   ↓
4. Ralph-Claw 告訴 Candice：「該你了」
   ↓
5. Candice 讀提示詞、執行 builder 角色
   ↓
6. Candice 寫出補丁
   ↓
7. Ralph-Claw 自動驗證
```

### 實作方式

#### 步驟 1：Ralph-Claw 準備提示詞（已有）
```bash
# 在 /tmp/ralphclaw-task/<timestamp>/prompt.md
```

#### 步驟 2：Candice 作為 Builder
```bash
cd /opt/ralphclaw
cat /tmp/ralphclaw-task/*/prompt.md | head -100
# 讀完後，在下方寫 builder 的回應
```

#### 步驟 3：回應格式
```
ANALYZE: [簡單分析]

IMPLEMENT:
[unified diff 格式的補丁]

SUMMARY: [做了什麼]
```

#### 步驟 4：Ralph-Claw 繼續
```bash
# 自動檢測補丁
grep "^ANALYZE:" /tmp/candice_builder_response.txt
grep "^IMPLEMENT:" /tmp/candice_builder_response.txt | sed 's/^IMPLEMENT://' > artifacts/last_patch.diff

# 驗證
bash scripts/run_verifier.sh
```

## 為什麼這樣最簡單

1. **無 API 調用** — 不需要外部 Claude API
2. **完全可控** — 你直接看到每一步
3. **交互式** — 你可以看到 Ralph-Claw 的提示，手動調整
4. **成本最低** — 只用你現有的 OpenClaw 環境

## 改造計畫

修改 `scripts/run_builder.sh`：
- ✅ 生成最小 context（已有）
- ✅ 寫提示詞到文件（已有）
- 🔄 暫停，等待 Candice 輸入
- ✅ 讀取 Candice 的補丁
- ✅ 驗證並應用

## 實際做法

### 方案 A：完全手動（最直接）
```bash
cd /opt/ralphclaw

# 1. Ralph-Claw 準備任務
bash scripts/run_builder.sh &
# 這會在 /tmp/ralphclaw-task/ 生成提示詞，然後等待

# 2. 在另一個終端，Candice 讀提示詞
cat /tmp/ralphclaw-task/*/prompt.md

# 3. Candice 寫補丁到文件
# （使用 Claude Code 或手動寫代碼）
cat > /tmp/candice_response.txt << 'PATCH'
ANALYZE: 需要實現 slugify_title 函數

IMPLEMENT:
--- a/app/utils/text.py
+++ b/app/utils/text.py
@@ -1,2 +1,5 @@
...patch content...

SUMMARY: 實現了 slugify_title 函數
PATCH

# 4. Ralph-Claw 繼續
bash scripts/run_builder.sh --input /tmp/candice_response.txt
```

### 方案 B：部分自動化
修改 `run_builder.sh`，在等待時提示：
```bash
echo "等待 Candice 完成..."
echo "請編輯: /tmp/ralphclaw-task/$(date +%s)/response.txt"
echo "完成後按 Enter"
read _
```

### 方案 C：完全集成（需要更多工程）
設置 cron job + file watching，自動檢測 Candice 的輸出

## 我的建議

**先用方案 A（完全手動）測試**，看看流程是否真的解決了「Claude 編程散漫」的問題。

如果有效，再考慮自動化。
