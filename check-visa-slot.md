# 法国签证 Slot 检查流程

## 前置条件

1. 已安装 agent-browser：
```bash
npm install -g agent-browser --force
agent-browser install
```

2. 使用 CDP 模式连接 Chrome（使用临时 profile 避免冲突）

---

## 完整流程

### Step 1: 启动 Chrome 并开启 CDP 调试端口

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug 2>&1 &
sleep 3
```

### Step 2: 连接 Chrome 并打开签证预约页面

```bash
agent-browser --headed --cdp 9222 open "https://consulat.gouv.fr/ambassade-de-france-en-irlande/rendez-vous?name=Visas"
```

### Step 3: 等待页面加载并获取快照

```bash
sleep 2 && agent-browser snapshot -i
```

找到 `button "Accéder aux services"` 的 ref（通常是 @e3）

### Step 4: 点击 "Accéder aux services"

```bash
agent-browser click @e3 && sleep 1.5 && agent-browser snapshot -i
```

找到 `button "Confirmer"` 的 ref（通常是 @e12）

### Step 5: 点击 "Confirmer"

```bash
agent-browser click @e12 && sleep 1 && agent-browser snapshot -i
```

找到 `checkbox "J'ai bien lu..."` 和 `button "Prendre rendez-vous"` 的 ref

### Step 6: 勾选复选框（通过 JS 绕过遮挡）

```bash
agent-browser eval 'var cb = document.querySelector("input[type=checkbox]"); if(cb) { cb.checked = true; cb.dispatchEvent(new Event("change", {bubbles: true})); }'
```

### Step 7: 点击 "Prendre rendez-vous"

```bash
agent-browser click @e6 && sleep 3 && agent-browser snapshot
```
（ref 可能是 @e8，根据实际 snapshot 调整）

### Step 8: 分析日历页面

日历页面会显示月份和日期按钮。关键信息：

**有可用 slot 的特征：**
- 日期按钮没有 `[disabled]` 标记
- 点击日期后显示具体时间段（如 "09:00", "10:00"）

**无可用 slot 的特征：**
- 所有日期都标记为 `[disabled]`
- 或显示 "Aucune réservation disponible pour ce jour"（当天无可用预约）
- 或显示 "aucun", "pas de créneaux", "complet"

### Step 9: 截图保存

```bash
agent-browser screenshot /Users/zhenjiao-ucd/Downloads/france/calendar-result.png
```

### Step 10: 关闭 agent-browser 和 Chrome

```bash
# 关闭 agent-browser 连接
agent-browser close

# 关闭 Chrome 进程
pkill -f "chrome-debug"
```

---

## 注意事项

1. **ref 编号可能变化**：每次 snapshot 后 ref 编号会重新生成，需要根据实际输出调整
2. **页面可能有弹窗**：如果点击被阻挡，尝试 `agent-browser press Escape` 关闭弹窗
3. **检查频率**：建议每隔几小时检查一次，避免过于频繁被限制
4. **时区**：页面显示 "Europe/Dublin (UTC+0)"，爱尔兰时间

---

## 结果判断

运行完成后，检查：
1. 截图文件：`/Users/zhenjiao-ucd/Downloads/france/calendar-*.png`
2. Snapshot 文件：`/Users/zhenjiao-ucd/Downloads/france/snapshot-*.txt`

在 snapshot 中搜索：
- `button "... 2026"` 没有 `[disabled]` → 可能有 slot
- `Aucune réservation disponible` → 无 slot
- 时间格式 `HH:MM` 有 `[ref=...]` → 有可用时间槽
