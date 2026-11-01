---
name: supermap-village-query
description: "SuperMap 村庄数据查询与地图可视化综合服务，支持数据查询、条件筛选、地图上图和属性展示"
version: 2.0.0
metadata:
  openclaw:
    requires:
      bins:
        - node
    install:
      - kind: node
        package: axios
        bins: []
---

# SuperMap 村庄查询与地图可视化 Skill

基于 SuperMap iServer 服务，提供村庄地理信息查询与地图可视化一体化能力。支持**数据查询的同时数据上图**，查询结果直接在地图上高亮展示。

## 功能特性

- 🔍 **村庄数据查询** — 通过 SuperMap REST API 查询村庄属性信息（SMID、QXMC、BZMC、PTLX、SMAREA 等）
- 🗺️ **自动触发 Canvas** — 查询结果自动生成 ` ```map ` 代码块，触发 Canvas 面板渲染地图
- 🏙️ **多条件筛选** — 支持按村庄名称（BZMC）、区县（QXMC）、类型（PTLX）模糊查询
- 📍 **交互式地图** — Canvas 中支持村庄查询、路径分析、绘制工具、测量工具等完整功能
- 📋 **属性展示** — 弹窗和侧边面板同步展示村庄属性

## 触发条件

用户表达了以下意图之一：
- 查询某个村庄的位置和信息（如"查一下阿氏村"、"蓝田县有哪些村庄"）
- 在地图上显示村庄（如"在地图上找阿氏村"、"显示阿氏村位置"）
- 查询村庄数据并可视化（如"把阿氏村的数据查出来显示在地图上"）

## 使用说明

**重要：调用此 skill 时，必须使用 `queryAndMap` 函数**，返回的 `markdown` 字段包含 `\`\`\`map` 代码块，系统会自动解析并打开 Canvas 面板。

```javascript
const result = await queryAndMap({ villageName: '村庄名' });
// result.markdown 包含完整的地图配置
```

## 架构说明
