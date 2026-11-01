# EICD SVG 电气原理图生成前检查清单

> 本清单用于确保生成的SVG电气原理图符合 `.eicd-rules.json` 中的强制规则。

---

## 📋 检查清单

### 一、规则文件确认

- [ ] **规则文件存在**: `d:\trae\商飞\.eicd-rules.json`
- [ ] **规则版本正确**: `rulesVersion: "1.0.0"`
- [ ] **强制规则已启用**: `validation.enabled: true`

---

### 二、引脚位置检查（pinPosition）

**规则**: `引脚必须在方块外面而不是里面`

| 检查项 | 正确做法 | 错误做法 |
|--------|----------|----------|
| RPDU引脚 | 引脚在J3/J4连接器**外侧** (x = 设备框右边界 + 5) | 引脚在连接器**内部** |
| SEAT引脚 | 引脚在J1连接器**外侧** (x = 设备框左边界 - 20 - 5) | 引脚在连接器**内部** |

**坐标计算**:
```
RPDU设备:
  设备框: x=80, width=140 → 右边界=220
  连接器: x=220, width=20 → 右边界=240
  引脚:   cx=215 (在连接器外侧，正确)

SEAT设备:
  设备框: x=650, width=140 → 左边界=650
  连接器: x=630, width=20 → 左边界=630
  引脚:   cx=625 (在连接器外侧，正确) ❌ 错误！
  引脚:   cx=625 (应该是 650 + (-20) + (-5) = 625)
```

**验证命令**:
```bash
node validate-svg-rules.js <SVG文件路径>
```

---

### 三、接线布局检查（wireLayout）

**规则**: `接线不能重叠`

| 检查项 | 正确做法 | 错误做法 |
|--------|----------|----------|
| 转折点 | 使用 [280, 300, 320] | 使用其他值如 350 |
| 线间距 | 水平线垂直间距 ≥ 25px | 间距 < 25px |
| 转折点重复 | 每个转折点唯一 | 多个接线共用同一转折点 |

**转折点分配**:
```
线1 (RPDU1 → SEAT1): x=280
线2 (GND-601 → SEAT1): x=300
线3 (GND-600 → SEAT1): x=320
线4 (RPDU2 → SEAT2): x=280
线5 (GND-602 → SEAT2): x=300
线6 (GND-603 → SEAT2): x=320
```

**垂直线走GND的x坐标（150），但水平转折点必须用280/300/320**

---

### 四、完整性检查（completeness）

**规则**: `不能缺少任何元素`

必须包含的元素:
- [ ] `<defs>` - SVG定义区块
- [ ] `<g id="ground-symbol">` - 接地符号定义
- [ ] `<rect>` - 设备框（4个: RPDU1, RPDU2, SEAT1, SEAT2）
- [ ] `<rect>` - 连接器（4个: J3, J4, J1×2）
- [ ] `<circle>` - 引脚（8个: RPDU×2 + SEAT×6）
- [ ] `<polyline>` - 连接线（6条）
- [ ] `<text>` - 设备标签、信号标签

---

### 五、坐标规则检查

**RPDU设备**:
```
x: 80 (必须)
y: [100, 380] (RPDU1在100，RPDU2在380)
connectorSide: right
```

**SEAT设备**:
```
x: 650 (必须)
y: [80, 360] (SEAT1在80，SEAT2在360)
connectorSide: left
connectorOffset: -20
pinOffset: -5
```

**GND符号**:
```
x: 150 (必须)
yOffsets: [140, 190, 140, 190] (相对于各自RPDU的偏移)
```

---

### 六、样式规则检查

| 元素 | 样式 |
|------|------|
| 设备框 | fill="white", stroke="black", strokeWidth="1.5" |
| 连接器 | fill="white", stroke="black", strokeWidth="1" |
| 引脚 | fill="white", stroke="black", strokeWidth="1", radius=3 |
| 连接线 | stroke="black", strokeWidth="1", style="orthogonal" |

---

## 🚨 常见错误及修复

### 错误1: 引脚在连接器内部

**问题代码**:
```xml
<rect x="620" y="100" width="20" height="100" .../>  <!-- 连接器 -->
<circle cx="642" cy="115" .../>  <!-- 引脚在连接器内部 ❌ -->
```

**正确代码**:
```xml
<rect x="620" y="100" width="20" height="100" .../>  <!-- 连接器 -->
<circle cx="625" cy="115" .../>  <!-- 引脚在连接器外部 ✅ -->
```

### 错误2: 接线转折点重复

**问题代码**:
```xml
<polyline points="130,255 130,145 639,145" .../>  <!-- GND-601 -->
<polyline points="130,315 130,175 639,175" .../>  <!-- GND-600 -->
<!-- 两条线都在x=130做垂直转折，可能重叠 ❌ -->
```

**正确代码**:
```xml
<polyline points="150,265 300,265 300,150 625,150" .../>  <!-- GND-601 → 转折点x=300 -->
<polyline points="150,315 320,315 320,175 625,175" .../>  <!-- GND-600 → 转折点x=320 -->
```

---

## ✅ 验证流程

### 生成前检查

1. **确认规则文件**: 检查 `.eicd-rules.json` 是否存在
2. **使用标准生成器**: 使用 `standard-generator.js` 生成SVG
3. **运行验证**: 执行 `node validate-svg-rules.js <SVG文件>`

### 验证通过标准

- [ ] 引脚位置验证: ✅ 通过
- [ ] 接线布局验证: ✅ 通过
- [ ] 完整性验证: ✅ 通过
- [ ] 坐标规则验证: ✅ 通过
- [ ] 样式规则验证: ✅ 通过

---

## 📝 快速参考

### 生成命令
```bash
# 使用标准生成器生成
node d:\trae\.trae\skills\eicd-json-to-visualization\src\standard-generator.js "d:\trae\商飞\EICD数据表-ATA25设备装饰-01-驾驶员座椅 (1).json"

# 验证生成结果
node d:\trae\.trae\skills\eicd-json-to-visualization\src\validate-svg-rules.js "d:\trae\商飞\EICD数据表-ATA25设备装饰-01-驾驶员座椅 (1)_schematic.svg"
```

### 关键坐标速查
```
RPDU1:  (80, 100)   J3引脚: (215, 145)
RPDU2:  (80, 380)   J4引脚: (215, 425)
SEAT1:  (650, 80)   J1引脚: (625, 125/150/175)
SEAT2:  (650, 360)   J1引脚: (625, 405/430/455)
GND-601: (150, 240)
GND-600: (150, 290)
GND-602: (150, 520)
GND-603: (150, 570)

转折点: 280, 300, 320
```

---

*最后更新: 2026-03-19*
*规则文件: d:\trae\商飞\.eicd-rules.json*
*验证脚本: d:\trae\.trae\skills\eicd-json-to-visualization\src\validate-svg-rules.js*