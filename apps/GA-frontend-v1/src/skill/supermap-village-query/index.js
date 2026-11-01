const fs = require('fs');
const path = require('path');
const axios = require('axios');

// ============================================================
// 常量配置
// ============================================================
const SUPERMAP_BASE_URL = 'http://172.16.235.50:18090/iserver/services/data-ShiLiangShuJu/rest/data';

// 地图服务 URL（三层叠加）
const SUPERMAP_MAP_URL = 'http://172.16.235.50:18090/iserver/services/map-ugcv5-wj_gis_chinaworld_img/rest/maps/world_image';           // 底图：世界地图
const SUPERMAP_CHINA_MAP_URL = 'http://172.16.235.50:18090/iserver/services/map-ugcv5-wj_gis_china_img/rest/maps/china_image';          // 叠加：中国地图
const SUPERMAP_BOUNDARY_MAP_URL = 'http://172.16.235.50:18090/iserver/services/map-wj_gis_ZhongGuo_XingZhengJingJie/rest/maps/wj_gis_中国_行政境界';  // 叠加：中国行政境界

const _RAW_DATA_SOURCE = '矢量数据4490';
const DATA_SOURCE = _RAW_DATA_SOURCE.replace(/\s+/g, '');
const DATASET_NAME = '村庄';
const DEFAULT_CENTER = [34.62, 104.29];  // 中国地图中心点
const DEFAULT_ZOOM = 5;
const DEFAULT_BOUNDS = { southwest: [15.68, 73.5], northeast: [53.56, 135.09] };

// ============================================================
// 字段配置
// ============================================================
const VILLAGE_FIELDS = ['SMID', 'QXMC', 'BZMC', 'PTLX', 'SMAREA', 'SMPERIMETER'];

// ============================================================
// 1. 村庄数据查询
// ============================================================

function buildDatasetName(dataSource, dataset) {
  return `${dataSource.replace(/\s+/g, '')}:${dataset}`;
}

async function queryVillage(params) {
  const { villageName, cityName, type, returnGeometry = true } = params;
  const url = `${SUPERMAP_BASE_URL}/featureResults.json`;

  let filters = [];
  if (villageName) filters.push(`BZMC LIKE '%${villageName}%'`);
  if (cityName) filters.push(`QXMC LIKE '%${cityName}%'`);
  if (type) filters.push(`PTLX LIKE '%${type}%'`);

  const attributeFilter = filters.length > 0 ? filters.join(' AND ') : 'SMID >= 0';

  const requestBody = {
    getFeatureMode: 'SQL',
    datasetNames: [buildDatasetName(DATA_SOURCE, DATASET_NAME)],
    queryParameter: {
      attributeFilter,
      fields: returnGeometry ? ['*'] : VILLAGE_FIELDS
    },
    hasGeometry: returnGeometry
  };

  try {
    console.log(`🔍 正在查询村庄数据...`);
    console.log(`   数据源: ${DATA_SOURCE}:${DATASET_NAME}`);
    console.log(`   过滤条件: ${attributeFilter}`);

    const response = await axios.post(url, requestBody, {
      params: { fromIndex: 0, toIndex: 100, returnContent: true },
      headers: { 'Content-Type': 'application/json' },
      timeout: 15000
    });

    let features = extractFeatures(response.data);

    if (!features || features.length === 0) {
      console.log(`❌ 未找到匹配的村庄数据`);
      return { success: false, count: 0, features: [] };
    }

    console.log(`✅ 查询成功，共找到 ${features.length} 条结果`);
    features.forEach((f, i) => {
      const props = f.properties || {};
      console.log(`   ${i + 1}. ${props.BZMC || '未知'} (${props.QXMC || '未知区县'})`);
    });

    return { success: true, count: features.length, features };
  } catch (error) {
    console.error('❌ 查询失败:', error.message);
    if (error.response) {
      console.error('   状态码:', error.response.status);
    }
    return { success: false, count: 0, features: [], error: error.message };
  }
}

function extractFeatures(data) {
  if (!data) return null;

  const candidates = [
    data?.features,
    data?.result?.features,
  ];

  for (const candidate of candidates) {
    if (!candidate) continue;
    if (Array.isArray(candidate)) return candidate;
    if (candidate.type === 'FeatureCollection' && Array.isArray(candidate.features)) {
      return candidate.features;
    }
    if (candidate.features && Array.isArray(candidate.features)) {
      return candidate.features;
    }
  }

  if (data.type === 'FeatureCollection' && Array.isArray(data.features)) {
    return data.features;
  }

  return null;
}

// ============================================================
// 2. 按要素 ID 查询详情
// ============================================================

function parseFeatureId(featureId) {
  const parts = (featureId || '').split('-');
  return { smid: parts[parts.length - 1] || featureId };
}

async function getFeatureById(params) {
  const { featureId, hasGeometry = true } = params;

  if (!featureId) {
    return { success: false, error: '缺少 featureId' };
  }

  const { smid } = parseFeatureId(featureId);

  const url = `${SUPERMAP_BASE_URL}/datasources/${encodeURIComponent(DATA_SOURCE)}/datasets/${DATASET_NAME}/features/${smid}`;

  try {
    const response = await axios.get(url, {
      params: { hasGeometry, returnContent: true },
      headers: { 'Accept': 'application/json' },
      timeout: 10000
    });

    const feature = response.data;
    if (!feature) {
      return { success: false, error: '要素不存在' };
    }

    const props = feature.properties || {};
    const resultProps = {};
    VILLAGE_FIELDS.forEach(field => {
      if (props[field] !== undefined) {
        resultProps[field] = props[field];
      }
    });

    return {
      success: true,
      feature: { ...feature, properties: resultProps },
      properties: resultProps
    };
  } catch (error) {
    console.error('❌ 查询要素详情失败:', error.message);
    return { success: false, error: error.message };
  }
}

// ============================================================
// 3. 综合查询 - 只查数据 + 触发 Canvas
// ============================================================


 // index.js - queryAndMap 函数

async function queryAndMap(params) {
  const { villageName, cityName, type } = params;
  const effectiveName = (villageName || '阿氏村').trim();

  console.log(`\n🗺️  SuperMap 村庄查询与地图可视化`);
  console.log(`   =${'='.repeat(40)}`);

  // ✅ 先查询一次，验证数据是否存在，并获取中心点
  const queryResult = await queryVillage({
    villageName: effectiveName,
    cityName,
    type,
    returnGeometry: true
  });

  if (!queryResult.success || queryResult.features.length === 0) {
    console.log(`\n❌ 未找到匹配的村庄数据`);
    return {
      success: false,
      markdown: `❌ 未找到包含 "${effectiveName}" 的村庄数据。`,
      features: [],
      count: 0,
      message: '未找到匹配数据'
    };
  }

  // ✅ 提取中心点作为地图初始位置
  let center = DEFAULT_CENTER;
  let zoom = DEFAULT_ZOOM;
  const firstFeature = queryResult.features[0];
  if (firstFeature?.geometry?.center) {
    center = [firstFeature.geometry.center.y, firstFeature.geometry.center.x];
    zoom = 14;
  }

  // ✅ 构建 map 配置 - 只传递查询参数，不传递 features 数据（特别是 points 数组）
  const mapConfig = {
    type: 'map',
    status: 'complete',
    isComplete: true,
    title: `村庄查询 - ${effectiveName}`,
    center: center,
    zoom: zoom,
    layers: [
      {
        type: 'tile',
        url: SUPERMAP_MAP_URL,
        name: '世界地图底图',
        attribution: 'SuperMap'
      },
      {
        type: 'tile',
        url: SUPERMAP_CHINA_MAP_URL,
        name: '中国地图叠加',
        attribution: 'SuperMap'
      },
      {
        type: 'tile',
        url: SUPERMAP_BOUNDARY_MAP_URL,
        name: '中国行政境界',
        attribution: 'SuperMap'
      }
    ],
    // ✅ 只传递查询参数，不传递任何 features/points 数据
    queryParams: {
      villageName: effectiveName,
      cityName: cityName || '',
      type: type || ''
    },
    // ✅ 只传递统计摘要，不传递完整数据
    summary: {
      count: queryResult.features.length,
      hasResult: true
    }
  };

  // ✅ 生成 ```map 代码块，触发 Canvas 渲染（此时 JSON 非常小，不会被截断）
  const markdown = `\n\`\`\`map\n${JSON.stringify(mapConfig, null, 2)}\n\`\`\`\n`;

  console.log(`\n✅ 查询完成，共找到 ${queryResult.features.length} 条记录`);
  console.log(`📍 已生成地图配置（轻量级，不含几何数据），将触发 Canvas 渲染`);
  console.log(`📍 中心点: [${center[0]}, ${center[1]}]`);
  console.log(`📝 Canvas 将根据查询参数 "${effectiveName}" 重新加载完整数据`);

  return {
    success: true,
    markdown,
    count: queryResult.features.length,
    villageName: effectiveName,
    queryParams: { villageName: effectiveName, cityName, type }
  };
}
// ============================================================
// 导出模块
// ============================================================
module.exports = {
  default: queryAndMap,
  SUPERMAP_BASE_URL,
  SUPERMAP_MAP_URL,
  SUPERMAP_CHINA_MAP_URL,
  SUPERMAP_BOUNDARY_MAP_URL,
  DATA_SOURCE,
  DATASET_NAME,
  VILLAGE_FIELDS,
  DEFAULT_CENTER,
  DEFAULT_ZOOM,
  DEFAULT_BOUNDS,

  queryVillage,
  getFeatureById,
  queryAndMap,

  buildDatasetName,
  extractFeatures
};

// ============================================================
// CLI 入口
// ============================================================
if (require.main === module) {
  (async () => {
    const args = process.argv.slice(2);
    const villageName = args[0] || '阿氏村';

    console.log(`\n🗺️  SuperMap 村庄查询工具`);
    console.log(`   =${'='.repeat(40)}`);
    console.log(`   查询村庄: ${villageName}\n`);

    const result = await queryVillage({ villageName });

    if (result.success) {
      console.log(`\n📊 查询到 ${result.count} 条记录`);
    } else {
      console.log('\n❌ 查询失败');
    }
  })().catch(console.error);
}