---
name: eicd-json-to-visualization
description: EICD JSON to Visualization 转换技能是一款专业的电气原理图可视化工具，能够将JSON格式的EICD数据转换为电气原理图。该技能通过读取记忆目录保持上下文连贯性，支持用户交互式选择模板，使用固定坐标布局生成标准航空电气原理图，并生成详细的操作文档。适用于航空航天、汽车、工业自动化等领域的电气系统可视化设计，可大幅提升电气原理图绘制效率。
---

***

name: eicd-json-to-visualization
description: EICD JSON to Visualization 转换技能是一款专业的电气原理图可视化工具，能够将JSON格式的EICD数据转换为电气原理图。该技能通过读取记忆目录保持上下文连贯性，支持用户交互式选择模板，使用固定坐标布局生成标准航空电气原理图，并生成详细的操作文档。适用于航空航天、汽车、工业自动化等领域的电气系统可视化设计，可大幅提升电气原理图绘制效率。


# EICD JSON to Visualization 转换技能

## Description

EICD JSON数据转电气原理图自动化工具，支持将JSON格式的电气接口控制文档转换为标准航空电气原理图，使用固定坐标布局，并生成操作文档记录转换详情。

## 应用场景

- 当用户需要将EICD JSON数据转换为电气原理图时
- 当用户希望选择不同的模板（默认模板或自定义模板）时
- 当用户希望在多次转换之间保持上下文连贯性时
- 当用户需要记录可视化操作详情时

## EICD 可视化强制规范

> **CRITICAL: 所有 EICD JSON to SVG 可视化必须严格遵守以下布局规范，违反将导致生成的SVG被用户拒绝**

### 1. GND符号布局（核心规范）

- **位置**: GND符号必须在RPDU设备正下方（x=130），禁止放在画布中间
- **数量**: 每个RPDU下方需要2个GND符号
  - RPDU1下方: GND-601（电源地）、GND-600（屏蔽地）
  - RPDU2下方: GND-602（电源地）、GND-603（屏蔽地）
- **垂直间距**: GND符号之间保持60像素间距

### 2. 设备位置规范

- **RPDU设备**（电源侧）: 画布左侧 x=60
- **座椅设备**（负载侧）: 画布右侧 x=550 或 x=650
- **GND符号**: x=130（RPDU正下方）

### 3. 连接器位置规范

- **RPDU设备**: 连接器J3/J4位于设备框**右侧外部**（x=200），引脚位于**外侧**（x=220）
- **座椅设备**: 连接器J1位于设备框**左侧外部**（x=530或630），引脚位于**外侧**（x=625）

### 4. 连接线规范

- **正交折线**: 使用水平-垂直-水平的三段式连线
- **GND连接**: 必须从RPDU侧（x=130）引出，不能从画布中间引出
- **信号标签**: 放置在连线上方，靠近中间位置

### 5. 引脚位置规范

- **座椅设备引脚必须在连接器外部**：引脚x坐标 < 连接器x坐标
- **RPDU设备引脚必须在连接器外部**：引脚x坐标 > 连接器x坐标

### 6. 违规后果

- 违反上述规范生成的SVG将被用户拒绝
- 必须按照本规范生成符合航空电气标准的原理图

### 7. 强制检查清单（在生成SVG前必须逐项确认）

| # | 检查项 | 正确值 | 错误示例 |
|---|--------|--------|----------|
| 1 | GND符号X坐标 | `x=130` | `x=300`, `x=500` |
| 2 | GND符号位置 | RPDU正下方 | 画布中间 |
| 3 | RPDU设备X坐标 | `x=60` | `x=80` |
| 4 | 座椅设备X坐标 | `x=550` 或 `x=650` | 其他值 |
| 5 | 座椅设备连接器X坐标 | `x=530` 或 `x=630` (在设备左侧) | `x=570` |
| 6 | 座椅设备引脚X坐标 | `x=625` (连接器外侧) | `x=650` (连接器内侧) |
| 7 | RPDU连接器X坐标 | `x=200` (设备右侧) | 其他值 |
| 8 | RPDU引脚X坐标 | `x=220` (连接器外侧) | `x=200` |
| 9 | GND垂直间距 | ≥60像素 | <60像素 |

### 8. 拒绝生成规则

**如果以下任一情况发生，必须拒绝生成并提示用户修正**：

| 情况 | 原因 | 处理方式 |
|------|------|----------|
| GND符号在画布中间 | 违反强制规范 | 移动到RPDU正下方 x=130 |
| 引脚在连接器内侧 | 违反引脚必须在外部的规范 | 修正引脚坐标到连接器外侧 |
| GND间距<60像素 | 会导致地线重叠 | 增加间距到60像素 |
| 设备位置与规范不符 | 影响整体布局 | 按规范调整坐标 |

---

## 工作方式：协作式交互模式

采用分阶段协作模式，每个阶段完成后等待用户确认再进入下一阶段。

### 阶段一：文件确认与准备

**目标**：确认JSON文件路径并准备可视化环境

**⚠️ 强制要求：必须先学习 EICD 可视化强制规范**

**执行步骤**：
1. ⭐ **首先**读取并熟悉 `## EICD 可视化强制规范` 章节的所有规范
2. ⭐ 读取 `d:\trae\商飞\memory\json-to-visualization\pin_position_fix.md`，确认引脚位置修正记录
3. ⭐ 读取 `d:\trae\商飞\memory\GUARDRAILS.md`，了解工作边界
4. ⭐ 读取最近的操作文档（`d:\trae\商飞\memory\json-to-visualization\*.md`），了解用户偏好和之前的模板选择

**规范引用**：
- 所有布局规范已整合到 `## EICD 可视化强制规范` 章节
- 生成SVG前必须按照**强制检查清单**逐项确认

### 阶段二：模板选择

**目标**：让用户选择要使用的模板

**执行步骤**：

1. 读取 `templates` 目录中的所有可用模板
2. 构建选择菜单，包含：
   - **默认选项**：
     - ⚡ 电气原理图（推荐） - 使用系统默认模板
   - **自定义模板**：
     - 从 `templates` 目录读取所有用户保存的模板
3. **等待用户选择后再进入下一阶段**（关键：未经确认不得继续）
4. **分析用户选择**：
   - 如果选择"电气原理图（推荐）"，使用系统默认模板
   - 如果选择自定义模板，使用对应的模板配置
5. **在生成图表前确认用户选择**，确保符合用户需求

**对话框实现**：
技能使用 `AskUserQuestion` 工具创建交互式对话框：

```json
{
  "questions": [{
    "question": "请选择要使用的模板：",
    "header": "模板选择",
    "options": [
      {
        "label": "⚡ 电气原理图（推荐）",
        "description": "使用系统默认的电气原理图模板，白色设备框、连接器J3/J4/J1、引脚编号、接地符号、正交连线"
      },
      {
        "label": "1. 默认电气原理图模板 [系统]",
        "description": "标准航空电气原理图风格，白色设备框、连接器J3/J4/J1、引脚编号、接地符号、正交连线"
      },
      {
        "label": "2. 用户自定义模板 - 测试 [用户]",
        "description": "用户编辑后的自定义模板，包含完整的连接路径配置"
      },
      {
        "label": "3. 用户编辑的SVG转换模板 [用户]",
        "description": "从SVG转换并编辑的电气原理图模板"
      }
    ],
    "multiSelect": false
  }]
}
```

**响应处理**：

- 当用户选择后，技能会根据选择确定使用的模板
- 如果选择"电气原理图（推荐）"，使用系统默认模板
- 如果选择自定义模板，使用对应的模板配置生成图表
- 技能会根据用户的选择继续执行图表生成操作

### 阶段三：图表生成与布局计算

**目标**：根据用户选择的模板生成电气原理图

**⚠️ 强制检查清单**：生成SVG前必须按照 `## EICD 可视化强制规范` 章节中的**强制检查清单**逐项确认

**执行步骤**：

1. ⭐ **逐项检查**布局规范，确认每个坐标值正确（详见顶部强制检查清单）
2. 读取JSON数据并解析EICD结构
3. 根据用户选择创建对应的SVG图结构
   - **电气原理图（推荐）**：使用参考图风格，白色设备框、连接器J3/J4/J1、引脚编号、接地符号、正交连线（详见附录风格案例）
   - 自定义模板：应用用户保存的模板配置
4. 使用固定坐标布局算法
5. 生成SVG格式的电气原理图
6. 确保所有节点、边、标签都正确渲染

### 阶段四：文档生成与完成

**目标**：生成操作文档并完成可视化过程

**执行步骤**：

1. 创建MD格式的操作文档
2. 包含转换详情、时间戳和文件信息
3. 包含用户交互记录（用户选择的模板或图表类型）
4. 将文档保存到 `d:\trae\商飞\memory\json-to-visualization` 目录
5. 向用户展示转换结果和生成的文件路径

## 输入

- json\_file: EICD JSON文件路径
- template\_id: (可选) 模板ID，如果未提供则进入交互选择
- output\_dir: (可选) 保存SVG输出的目录

## 模板系统

### 模板概述

技能支持模板系统，用户可以：

1. **使用默认模板** - 系统预设的标准电气原理图模板
2. **创建自定义模板** - 通过模板编辑器创建并保存自定义布局
3. **选择已有模板** - 在生成图表时选择之前保存的模板

### 模板存储位置

```
d:\trae\.trae\skills\eicd-json-to-visualization\templates\
├── default_schematic.json    # 默认模板（系统预设）
├── user_custom_1.json        # 用户自定义模板
└── user_custom_2.json        # 用户自定义模板
```

### 模板数据结构

```json
{
  "templateName": "模板名称",
  "templateId": "唯一标识",
  "description": "模板描述",
  "version": "1.0",
  "createdAt": "创建时间",
  "canvas": {
    "width": 900,
    "height": 650,
    "backgroundColor": "#ffffff",
    "gridSize": 20,
    "showGrid": true
  },
  "layout": {
    "type": "fixed",
    "direction": "horizontal"
  },
  "styles": {
    "device": { "fill": "white", "stroke": "black", ... },
    "connector": { "fill": "white", "stroke": "black", ... },
    "pin": { "radius": 3, ... },
    "connection": { "stroke": "black", "style": "orthogonal" }
  },
  "positions": {
    "RPDU1": { "x": 60, "y": 80 },
    "2501U2201": { "x": 650, "y": 80 }
  },
  "connections": [...]
}
```

### 模板管理器 API

```javascript
const TemplateManager = require('./src/template-manager');
const manager = new TemplateManager();

// 获取所有模板
const templates = manager.getAllTemplates();

// 获取指定模板
const template = manager.getTemplate('default_schematic');

// 保存模板
manager.saveTemplate(templateObject);

// 应用模板生成SVG
const svg = manager.applyTemplate('template_id', eicdData);

// 复制模板
const newTemplate = manager.copyTemplate('source_id', '新模板名称');

// 删除模板
manager.deleteTemplate('template_id');
```

## 输出

- SVG文件: 生成的电气原理图，采用SVG格式
- 操作文档: 包含转换详情的MD文件

## 模板说明

### 1. 电气原理图（推荐）

- **图标**: ⚡
- **描述**: 标准航空电气原理图风格，与参考图 `elkjs_layout_custom.html` 完全一致
- **布局**: 固定坐标布局，RPDU在左，座椅设备在右，**GND在RPDU正下方**
- **风格特征**:
  - 白色设备框，黑色边框 (stroke-width="1.5")
  - 连接器标注 (J3, J4, J1)
  - 引脚编号 (10, 20, A, B, C, D, E, F)
  - 接地符号 (GND-601, GND-600, GND-602, GND-603)
  - 正交折线连接
  - 信号标签 (1LN ESS D N, CG ESS Z N)
- **适用场景**: 航空电气工程标准图纸，符合行业规范

### 2. 自定义模板

用户可以通过模板编辑器创建和保存自定义模板，模板存储在 `templates` 目录中。每个模板包含：
- 画布配置（尺寸、背景色、网格）
- 布局配置（固定坐标布局）
- 样式配置（设备、连接器、引脚、连接线样式）
- 设备位置配置
- 连接路径配置

## 电气原理图（推荐）生成代码

当用户选择"电气原理图（推荐）"时，使用以下代码生成与参考图风格一致的SVG：

```javascript
const fs = require('fs');

// 读取JSON文件
const jsonPath = 'EICD数据表-ATA25设备装饰-01-驾驶员座椅 (1).json';
const jsonData = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));

// 生成SVG - 完全匹配参考图风格
const svgWidth = 900;
const svgHeight = 600;

let svg = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${svgWidth}" height="${svgHeight}" viewBox="0 0 ${svgWidth} ${svgHeight}">
  <defs>
    <!-- 接地符号 -->
    <g id="ground-symbol">
      <line x1="0" y1="0" x2="0" y2="15" stroke="black" stroke-width="1"/>
      <line x1="-10" y1="15" x2="10" y2="15" stroke="black" stroke-width="1"/>
      <line x1="-6" y1="20" x2="6" y2="20" stroke="black" stroke-width="1"/>
      <line x1="-3" y1="25" x2="3" y2="25" stroke="black" stroke-width="1"/>
    </g>
  </defs>
  
  <!-- 背景 -->
  <rect width="100%" height="100%" fill="white"/>
  
  <!-- 标题 -->
  <text x="20" y="30" font-family="Arial, sans-serif" font-size="20" font-weight="bold" fill="#333">Layout Result</text>
  
  <!-- 主边框 -->
  <rect x="10" y="45" width="880" height="540" fill="#fafafa" stroke="#ccc" stroke-width="1"/>
`;

// 绘制设备框和连接器 - 参考图风格
// RPDU1 (2404U4101)
svg += `
  <!-- RPDU1 设备框 -->
  <rect x="60" y="80" width="140" height="120" fill="white" stroke="black" stroke-width="1.5"/>
  <text x="130" y="110" font-family="Arial" font-size="11" text-anchor="middle" fill="black">RPDU1_SSPC_J3_08</text>
  
  <!-- RPDU1 连接器 J3 (右侧) -->
  <rect x="200" y="130" width="20" height="40" fill="white" stroke="black" stroke-width="1"/>
  <text x="210" y="155" font-family="Arial" font-size="9" text-anchor="middle" fill="black">J3</text>
  
  <!-- RPDU1 引脚 10 -->
  <circle cx="200" cy="145" r="3" fill="white" stroke="black" stroke-width="1"/>
  <text x="195" y="142" font-family="Arial" font-size="8" text-anchor="end" fill="black">10</text>
  
  <!-- RPDU1 标签 -->
  <text x="130" y="215" font-family="Arial" font-size="11" text-anchor="middle" fill="black" font-weight="bold">RPDU1</text>
`;

// RPDU2 (2404U4103)
svg += `
  <!-- RPDU2 设备框 -->
  <rect x="60" y="380" width="140" height="120" fill="white" stroke="black" stroke-width="1.5"/>
  <text x="130" y="410" font-family="Arial" font-size="11" text-anchor="middle" fill="black">RPDU2_SSPC_J4_10</text>
  
  <!-- RPDU2 连接器 J4 (右侧) -->
  <rect x="200" y="430" width="20" height="40" fill="white" stroke="black" stroke-width="1"/>
  <text x="210" y="455" font-family="Arial" font-size="9" text-anchor="middle" fill="black">J4</text>
  
  <!-- RPDU2 引脚 20 -->
  <circle cx="200" cy="445" r="3" fill="white" stroke="black" stroke-width="1"/>
  <text x="195" y="442" font-family="Arial" font-size="8" text-anchor="end" fill="black">20</text>
  
  <!-- RPDU2 标签 -->
  <text x="130" y="515" font-family="Arial" font-size="11" text-anchor="middle" fill="black" font-weight="bold">RPDU2</text>
`;

// GND 接地符号
svg += `
  <!-- GND-601 -->
  <use href="#ground-symbol" x="130" y="240"/>
  <text x="130" y="275" font-family="Arial" font-size="10" text-anchor="middle" fill="black">GND-601</text>
  
  <!-- GND-600 -->
  <use href="#ground-symbol" x="130" y="290"/>
  <text x="130" y="325" font-family="Arial" font-size="10" text-anchor="middle" fill="black">GND-600</text>
  
  <!-- GND-602 -->
  <use href="#ground-symbol" x="130" y="540"/>
  <text x="130" y="575" font-family="Arial" font-size="10" text-anchor="middle" fill="black">GND-602</text>
  
  <!-- GND-603 -->
  <use href="#ground-symbol" x="130" y="590"/>
  <text x="130" y="625" font-family="Arial" font-size="10" text-anchor="middle" fill="black">GND-603</text>
`;

// 2501U2201 设备框
svg += `
  <!-- 2501U2201 设备框 -->
  <rect x="650" y="80" width="140" height="140" fill="white" stroke="black" stroke-width="1.5"/>
  
  <!-- 2501U2201 连接器 J1 (左侧) -->
  <rect x="630" y="110" width="20" height="80" fill="white" stroke="black" stroke-width="1"/>
  <text x="640" y="155" font-family="Arial" font-size="9" text-anchor="middle" fill="black">J1</text>
  
  <!-- 2501U2201 引脚 A, B, C -->
  <!-- ⚠️ 重要：引脚必须在连接器外部（连接器x=630，所以引脚x=625在左侧外部） -->
  <circle cx="625" cy="125" r="3" fill="white" stroke="black" stroke-width="1"/>
  <text x="620" y="128" font-family="Arial" font-size="8" fill="black">A</text>
  <text x="595" y="121" font-family="Arial" font-size="10" fill="black">DC PWR IN</text>
  
  <circle cx="625" cy="150" r="3" fill="white" stroke="black" stroke-width="1"/>
  <text x="620" y="153" font-family="Arial" font-size="8" fill="black">B</text>
  <text x="595" y="146" font-family="Arial" font-size="10" fill="black">DC GND</text>
  
  <circle cx="625" cy="175" r="3" fill="white" stroke="black" stroke-width="1"/>
  <text x="620" y="178" font-family="Arial" font-size="8" fill="black">C</text>
  <text x="595" y="171" font-family="Arial" font-size="10" fill="black">GROUNDING</text>
  
  <!-- 2501U2201 标签 -->
  <text x="720" y="235" font-family="Arial" font-size="11" text-anchor="middle" fill="black" font-weight="bold">2501U2201</text>
`;

// 2501U2203 设备框
svg += `
  <!-- 2501U2203 设备框 -->
  <rect x="650" y="350" width="140" height="140" fill="white" stroke="black" stroke-width="1.5"/>
  
  <!-- 2501U2203 连接器 J1 (左侧) -->
  <rect x="630" y="380" width="20" height="80" fill="white" stroke="black" stroke-width="1"/>
  <text x="640" y="425" font-family="Arial" font-size="9" text-anchor="middle" fill="black">J1</text>
  
  <!-- 2501U2203 引脚 D, E, F -->
  <!-- ⚠️ 重要：引脚必须在连接器外部（连接器x=630，所以引脚x=625在左侧外部） -->
  <circle cx="625" cy="405" r="3" fill="white" stroke="black" stroke-width="1"/>
  <text x="620" y="408" font-family="Arial" font-size="8" fill="black">D</text>
  <text x="595" y="401" font-family="Arial" font-size="10" fill="black">DC PWR IN</text>
  
  <circle cx="625" cy="430" r="3" fill="white" stroke="black" stroke-width="1"/>
  <text x="620" y="433" font-family="Arial" font-size="8" fill="black">E</text>
  <text x="595" y="426" font-family="Arial" font-size="10" fill="black">DC GND</text>
  
  <circle cx="625" cy="455" r="3" fill="white" stroke="black" stroke-width="1"/>
  <text x="620" y="458" font-family="Arial" font-size="8" fill="black">F</text>
  <text x="595" y="451" font-family="Arial" font-size="10" fill="black">GROUNDING</text>
  
  <!-- 2501U2203 标签 -->
  <text x="720" y="505" font-family="Arial" font-size="11" text-anchor="middle" fill="black" font-weight="bold">2501U2203</text>
`;

// 绘制连接线 - 正交风格，带标签
// ⚠️ 重要：连接线终点必须是引脚位置（x=625），不是连接器位置
jsonData.interfaces.forEach((intf, idx) => {
  if (intf.sigSrcDev === '2404U4101' && intf.sigDestDev === '2501U2201') {
    if (intf.sigDestPinNum === 'A') {
      svg += `
  <!-- RPDU1 J3-10 -> 2501U2201 J1-A -->
  <!-- 连接线从RPDU引脚(220,145)到座椅引脚(625,125) -->
  <polyline points="220,145 280,145 280,125 625,125" fill="none" stroke="black" stroke-width="1"/>
  <text x="380" y="120" font-family="Arial" font-size="9" fill="black">${intf.powSupplyCode} ${intf.emcCode} ${intf.sigDir}</text>
`;
    } else if (intf.sigDestPinNum === 'B') {
      svg += `
  <!-- GND -> 2501U2201 J1-B -->
  <polyline points="130,265 300,265 300,150 625,150" fill="none" stroke="black" stroke-width="1"/>
  <text x="380" y="145" font-family="Arial" font-size="9" fill="black">${intf.groundCode}</text>
`;
    } else if (intf.sigDestPinNum === 'C') {
      svg += `
  <!-- GND -> 2501U2201 J1-C -->
  <polyline points="130,315 320,315 320,175 625,175" fill="none" stroke="black" stroke-width="1"/>
  <text x="380" y="170" font-family="Arial" font-size="9" fill="black">${intf.groundCode}</text>
`;
    }
  }

  if (intf.sigSrcDev === '2404U4103' && intf.sigDestDev === '2501U2203') {
    if (intf.sigDestPinNum === 'A') {
      svg += `
  <!-- RPDU2 J4-20 -> 2501U2203 J1-A -->
  <polyline points="220,445 280,445 280,405 625,405" fill="none" stroke="black" stroke-width="1"/>
  <text x="380" y="400" font-family="Arial" font-size="9" fill="black">${intf.powSupplyCode} ${intf.emcCode} ${intf.sigDir}</text>
`;
    } else if (intf.sigDestPinNum === 'B') {
      svg += `
  <!-- GND -> 2501U2203 J1-B -->
  <polyline points="130,565 300,565 300,430 625,430" fill="none" stroke="black" stroke-width="1"/>
  <text x="380" y="425" font-family="Arial" font-size="9" fill="black">${intf.groundCode}</text>
`;
    } else if (intf.sigDestPinNum === 'C') {
      svg += `
  <!-- GND -> 2501U2203 J1-C -->
  <polyline points="130,615 320,615 320,455 625,455" fill="none" stroke="black" stroke-width="1"/>
  <text x="380" y="450" font-family="Arial" font-size="9" fill="black">${intf.groundCode}</text>
`;
    }
  }
});

svg += `</svg>`;

// 保存SVG文件
const svgFileName = jsonPath.replace('.json', '_schematic_v2.svg');
fs.writeFileSync(svgFileName, svg, 'utf8');

console.log('电气原理图（推荐）已保存:', svgFileName);
```

## 自定义模板配置

自定义模板支持以下配置参数：

```json
{
  "canvas": {
    "width": 900,           // 画布宽度（像素）
    "height": 650,          // 画布高度（像素）
    "backgroundColor": "#ffffff",
    "gridSize": 20,
    "showGrid": true
  },
  "layout": {
    "type": "fixed",        // 固定坐标布局
    "direction": "horizontal"
  },
  "styles": {
    "device": {             // 设备样式
      "fill": "white",
      "stroke": "black",
      "strokeWidth": 1.5
    },
    "connector": {          // 连接器样式
      "fill": "white",
      "stroke": "black",
      "strokeWidth": 1
    },
    "connection": {         // 连接线样式
      "stroke": "black",
      "strokeWidth": 1,
      "style": "orthogonal" // 正交连线
    }
  },
  "positions": {          // 设备位置
    "RPDU1": { "x": 60, "y": 80 },
    "2501U2201": { "x": 650, "y": 80 }
  },
  "connections": [...]    // 连接路径
}
```

## 错误处理

- 文件未找到: 返回包含文件路径的错误信息
- 无效的JSON格式: 返回关于文件格式的错误信息
- 数据解析错误: 返回每个解析问题的详细错误信息
- 布局计算错误: 返回ELKJS布局计算失败的详细信息
- SVG生成错误: 返回SVG生成失败的详细信息

## 示例

### 示例1: 基本转换（带用户交互）

输入:

```
{"json_file": "d:\trae\商飞\EICD数据表-ATA25设备装饰-01-驾驶员座椅 (1).json"}
```

输出（等待用户选择）:

```
{
  "status": "need_selection",
  "message": "请选择要使用的模板：",
  "type": "template_selection",
  "options": [
    {"label": "⚡ 电气原理图（推荐）", "description": "使用系统默认的电气原理图模板..."},
    {"label": "1. 默认电气原理图模板 [系统]", "description": "标准航空电气原理图风格..."},
    {"label": "2. 用户自定义模板 - 测试 [用户]", "description": "用户编辑后的自定义模板..."}
  ]
}
```

用户选择后输入:

```
{
  "json_file": "d:\trae\商飞\EICD数据表-ATA25设备装饰-01-驾驶员座椅 (1).json",
  "template_id": "default_schematic"
}
```

最终输出:

```
{
  "status": "success",
  "json_file": "d:\trae\商飞\EICD数据表-ATA25设备装饰-01-驾驶员座椅 (1).json",
  "svg_file": "d:\trae\商飞\EICD数据表-ATA25设备装饰-01-驾驶员座椅 (1)_schematic.svg",
  "template_id": "default_schematic",
  "template_name": "默认电气原理图模板",
  "operation_doc": "d:\trae\商飞\memory\json-to-visualization\visualization_operation_20260317_120001.md"
}
```

### 示例2: 直接指定模板（跳过交互）

输入:

```
{
  "json_file": "d:\trae\商飞\EICD数据表-ATA25设备装饰-01-驾驶员座椅 (1).json",
  "template_id": "default_schematic"
}
```

输出:

```
{
  "status": "success",
  "json_file": "d:\trae\商飞\EICD数据表-ATA25设备装饰-01-驾驶员座椅 (1).json",
  "svg_file": "d:\trae\商飞\EICD数据表-ATA25设备装饰-01-驾驶员座椅 (1)_schematic.svg",
  "template_id": "default_schematic",
  "template_name": "默认电气原理图模板",
  "operation_doc": "d:\trae\商飞\memory\json-to-visualization\visualization_operation_20260317_120001.md"
}
```

## 依赖

- Node.js 环境
- ELKJS布局引擎 (elkjs)
- 文件系统操作
- JSON解析

## 执行模式

### 铁律

- 始终在处理前读取记忆目录以保持上下文
- 始终在转换后生成操作文档
- 始终在解析前验证JSON文件格式
- 永远不要修改原始JSON文件
- 始终执行完整的用户交互流程，未经用户确认不得跳过

### 交互式流程

技能默认执行完整的交互式流程：

1. 阶段一：文件确认与准备
2. 阶段二：用户交互与模板选择（必选，未经确认不得继续）
3. 阶段三：图表生成与布局计算
4. 阶段四：文档生成与完成

**用户交互流程**：

- 询问用户需要使用的模板
- 提供选项：电气原理图（推荐）、以及templates目录中的自定义模板
- 等待用户选择后再进入下一阶段

**对话框实现**：
技能使用 `AskUserQuestion` 工具创建交互式对话框：

```json
{
  "questions": [{
    "question": "请选择要使用的模板：",
    "header": "模板选择",
    "options": [
      {"label": "⚡ 电气原理图（推荐）", "description": "使用系统默认的电气原理图模板，白色设备框、连接器J3/J4/J1、引脚编号、接地符号、正交连线"},
      {"label": "1. 默认电气原理图模板 [系统]", "description": "标准航空电气原理图风格"},
      {"label": "2. 用户自定义模板 [用户]", "description": "用户自定义的模板配置"}
    ],
    "multiSelect": false
  }]
}
```

**响应处理**：

- 当用户选择模板后，技能会记录用户的选择
- 如果用户选择"电气原理图（推荐）"，使用系统默认模板生成SVG
- 如果用户选择自定义模板，使用对应的模板配置生成SVG
- 技能会根据用户的选择使用对应的模板生成器

### 红旗

- 尝试处理非JSON文件
- JSON数据中缺少必要的EICD字段（equipment, components, interfaces）
- 布局计算失败或超时
- SVG生成失败
- 无法生成操作文档

**拒绝生成规则详见 `## EICD 可视化强制规范` 章节**

### 门控函数

- 记忆目录读取成功
- JSON文件验证通过且可访问
- 数据解析无严重错误
- 用户已选择图表类型
- 布局计算成功
- SVG生成并保存成功
- 操作文档创建并保存

## 流程图

```
开始
  ↓
读取记忆目录
  ↓
验证JSON文件
  ↓
[判断] 有效?
  ├─ 否 → 返回错误
  └─ 是 → 显示模板选择
↓
[判断] 用户已选择?
  ├─ 否 → 等待用户选择
  └─ 是 → 解析JSON数据
↓
[判断] 模板类型?
  ├─ 默认模板 → 使用系统默认模板生成
  └─ 自定义模板 → 使用对应模板配置生成
↓
生成SVG
  ↓
生成操作文档
  ↓
保存文件
  ↓
返回成功
```

## 附录：风格案例参考 (elkjs\_layout\_custom.html)

本技能支持参考 `d:\trae\商飞\elkjs_layout_custom.html` 中的电气原理图风格进行可视化生成。该风格案例展示了以下关键特征：

### 风格特征

#### 1. 设备组件样式

- **设备框**: 使用 `<rect>` 元素绘制矩形，白色填充，黑色边框 (stroke-width="1.5")
- **连接器**: 设备边缘的小矩形突出 (J3, J4 在右侧，J1 在左侧)
- **引脚**: 使用 `<circle>` 绘制，半径 3，白色填充，黑色边框
- **引脚编号**: 使用小号字体 (8px) 标注在引脚旁边 (10, 20, A, B, C, D, E, F)

#### 2. 接地符号

- **样式**: 标准三线递减接地符号
- **标签**: GND-601, GND-600, GND-602, GND-603

#### 3. 连接线样式

- **线型**: 使用 `<polyline>` 元素绘制正交折线
- **颜色**: 黑色 (stroke="black")
- **线宽**: 1px
- **路由**: 直角转弯，水平垂直走向

#### 4. 信号标签

- **内容**: 1LN ESS D N, CG ESS Z N
- **字体**: Arial 9px
- **位置**: 连线上方

#### 5. 完整SVG结构

```svg
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="900" height="600" viewBox="0 0 900 600">
  <defs>
    <g id="ground-symbol">
      <line x1="0" y1="0" x2="0" y2="15" stroke="black" stroke-width="1"/>
      <line x1="-10" y1="15" x2="10" y2="15" stroke="black" stroke-width="1"/>
      <line x1="-6" y1="20" x2="6" y2="20" stroke="black" stroke-width="1"/>
      <line x1="-3" y1="25" x2="3" y2="25" stroke="black" stroke-width="1"/>
    </g>
  </defs>
  
  <rect width="100%" height="100%" fill="white"/>
  <text x="20" y="30" font-family="Arial, sans-serif" font-size="20" font-weight="bold" fill="#333">Layout Result</text>
  <rect x="10" y="45" width="880" height="540" fill="#fafafa" stroke="#ccc" stroke-width="1"/>
  
  <!-- 设备框、连接器、引脚、接地符号、连接线 -->
  
</svg>
```

### 使用建议

当用户要求生成与参考图风格一致的电气原理图时：

1. 选择"⚡ 电气原理图（推荐）"选项
2. 使用固定的坐标布局（非ELKJS动态布局）
3. 严格按照参考图的样式绘制设备框、连接器、引脚
4. 绘制正交连接线并添加信号标签
5. 生成符合航空电气标准的 SVG 输出

### 布局规范参考

> **注意**: 详细的布局规范已整合到本文档顶部的 `## EICD 可视化强制规范` 章节。以下为参考补充。

#### GND符号坐标参考
- GND-601: (130, 240) - RPDU1正下方
- GND-600: (130, 300) - GND-601下方60像素
- GND-602: (130, 540) - RPDU2正下方
- GND-603: (130, 600) - GND-602下方60像素

#### 设备垂直分布参考
- 上方区域：RPDU1 (y=80)、2501U2201 (y=80)
- 下方区域：RPDU2 (y=380)、2501U2203 (y=380)

**完整规范请参阅 `## EICD 可视化强制规范` 章节**