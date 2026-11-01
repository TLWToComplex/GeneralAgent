// d:\gitee\aisix_v2\src\skill\supermap-village-query\index.js
// 完整替换内容如下（在原文件基础上新增功能）

const fs = require('fs');
const path = require('path');
const axios = require('axios');

// ============================================================
// 常量配置
// ============================================================
const SUPERMAP_BASE_URL = 'http://172.16.235.50:18090/iserver/services/data-ShiLiangShuJu/rest/data';

const SUPERMAP_MAP_URL = 'http://172.16.235.50:18090/iserver/services/map-ugcv5-wj_gis_chinaworld_img/rest/maps/world_image';
const SUPERMAP_CHINA_MAP_URL = 'http://172.16.235.50:18090/iserver/services/map-ugcv5-wj_gis_china_img/rest/maps/china_image';
const SUPERMAP_BOUNDARY_MAP_URL = 'http://172.16.235.50:18090/iserver/services/map-wj_gis_ZhongGuo_XingZhengJingJie/rest/maps/wj_gis_中国_行政境界';

const _RAW_DATA_SOURCE = '矢量数据4490';
const DATA_SOURCE = _RAW_DATA_SOURCE.replace(/\s+/g, '');
const DATASET_NAME = '村庄';
const DEFAULT_CENTER = [34.62, 104.29];
const DEFAULT_ZOOM = 5;
const DEFAULT_BOUNDS = { southwest: [15.68, 73.5], northeast: [53.56, 135.09] };

const VILLAGE_FIELDS = ['SMID', 'QXMC', 'BZMC', 'PTLX', 'SMAREA', 'SMPERIMETER'];

// ============================================================
// 工具函数
// ============================================================

function buildDatasetName(dataSource, dataset) {
  return `${dataSource.replace(/\s+/g, '')}:${dataset}`;
}

function extractFeatures(data) {
  if (!data) return null;
  const candidates = [data?.features, data?.result?.features];
  for (const candidate of candidates) {
    if (!candidate) continue;
    if (Array.isArray(candidate)) return candidate;
    if (candidate.type === 'FeatureCollection' && Array.isArray(candidate.features)) return candidate.features;
    if (candidate.features && Array.isArray(candidate.features)) return candidate.features;
  }
  if (data.type === 'FeatureCollection' && Array.isArray(data.features)) return data.features;
  return null;
}

function parseFeatureId(featureId) {
  const parts = (featureId || '').split('-');
  return { smid: parts[parts.length - 1] || featureId };
}

function buildLayersConfig() {
  return [
    { type: 'tile', url: SUPERMAP_MAP_URL, name: '世界地图底图', attribution: 'SuperMap' },
    { type: 'tile', url: SUPERMAP_CHINA_MAP_URL, name: '中国地图叠加', attribution: 'SuperMap' },
    { type: 'tile', url: SUPERMAP_BOUNDARY_MAP_URL, name: '中国行政境界', attribution: 'SuperMap' }
  ];
}

function buildMapMarkdown(config) {
  return `\n\`\`\`map\n${JSON.stringify(config, null, 2)}\n\`\`\`\n`;
}

function buildQueryUrl() {
  return `${SUPERMAP_BASE_URL}/featureResults.json`;
}

async function executeQuery(requestBody, urlParams = {}) {
  const defaultParams = { fromIndex: 0, toIndex: 100, returnContent: true };
  const params = { ...defaultParams, ...urlParams };
  return axios.post(buildQueryUrl(), requestBody, {
    params,
    headers: { 'Content-Type': 'application/json' },
    timeout: 15000
  });
}

// ============================================================
// 核心查询函数
// ============================================================

/**
 * SQL 查询 - 按属性条件查询村庄
 */
async function queryVillage(params) {
  const { villageName, cityName, type, returnGeometry = true, maxFeatures, fields } = params;
  const filters = [];
  if (villageName) filters.push(`BZMC LIKE '%${villageName}%'`);
  if (cityName) filters.push(`QXMC LIKE '%${cityName}%'`);
  if (type) filters.push(`PTLX LIKE '%${type}%'`);
  const attributeFilter = filters.length > 0 ? filters.join(' AND ') : 'SMID >= 0';

  const requestBody = {
    getFeatureMode: 'SQL',
    datasetNames: [buildDatasetName(DATA_SOURCE, DATASET_NAME)],
    queryParameter: {
      attributeFilter,
      fields: fields || (returnGeometry ? ['*'] : VILLAGE_FIELDS)
    },
    hasGeometry: returnGeometry
  };
  if (maxFeatures != null) requestBody.maxFeatures = maxFeatures;

  try {
    console.log(`🔍 SQL 查询村庄: ${attributeFilter}`);
    const response = await executeQuery(requestBody);
    const features = extractFeatures(response.data);
    if (!features || features.length === 0) {
      return { success: false, count: 0, features: [] };
    }
    console.log(`✅ 查询成功，共 ${features.length} 条`);
    return { success: true, count: features.length, features };
  } catch (error) {
    console.error('❌ SQL 查询失败:', error.message);
    return { success: false, count: 0, features: [], error: error.message };
  }
}

/**
 * ID 查询 - 按要素 ID 批量查询
 */
async function queryByIds(params) {
  const { ids, returnGeometry = true } = params;
  if (!ids || !Array.isArray(ids) || ids.length === 0) {
    return { success: false, error: '缺少 ids 参数' };
  }
  const requestBody = {
    getFeatureMode: 'ID',
    datasetNames: [buildDatasetName(DATA_SOURCE, DATASET_NAME)],
    ids,
    hasGeometry: returnGeometry
  };
  try {
    console.log(`🔍 ID 查询: ${ids.length} 个ID`);
    const response = await executeQuery(requestBody);
    const features = extractFeatures(response.data);
    return { success: true, count: features?.length || 0, features: features || [] };
  } catch (error) {
    console.error('❌ ID 查询失败:', error.message);
    return { success: false, count: 0, features: [], error: error.message };
  }
}

/**
 * 范围查询 - 按矩形坐标范围查询
 */
async function queryByBounds(params) {
  const { bounds, attributeFilter, returnGeometry = true, fields } = params;
  if (!bounds) return { success: false, error: '缺少 bounds 参数' };

  const mode = attributeFilter ? 'BOUNDS_ATTRIBUTEFILTER' : 'BOUNDS';
  const requestBody = {
    getFeatureMode: mode,
    datasetNames: [buildDatasetName(DATA_SOURCE, DATASET_NAME)],
    bounds: {
      leftBottom: { x: bounds.leftBottom?.x ?? bounds.left, y: bounds.leftBottom?.y ?? bounds.bottom },
      rightTop: { x: bounds.rightTop?.x ?? bounds.right, y: bounds.rightTop?.y ?? bounds.top }
    },
    hasGeometry: returnGeometry
  };
  if (attributeFilter) requestBody.attributeFilter = attributeFilter;
  if (fields) requestBody.fields = fields;

  try {
    console.log(`🔍 范围查询: ${JSON.stringify(bounds)}`);
    const response = await executeQuery(requestBody);
    const features = extractFeatures(response.data);
    return { success: true, count: features?.length || 0, features: features || [] };
  } catch (error) {
    console.error('❌ 范围查询失败:', error.message);
    return { success: false, count: 0, features: [], error: error.message };
  }
}

/**
 * 缓冲区查询 - 按点坐标 + 缓冲区半径查询
 */
async function queryByBuffer(params) {
  const { point, bufferDistance, bufferDistanceUnit, attributeFilter, returnGeometry = true, fields } = params;
  if (!point || bufferDistance == null) {
    return { success: false, error: '缺少 point 或 bufferDistance 参数' };
  }

  const mode = attributeFilter ? 'BUFFER_ATTRIBUTEFILTER' : 'BUFFER';
  const requestBody = {
    getFeatureMode: mode,
    datasetNames: [buildDatasetName(DATA_SOURCE, DATASET_NAME)],
    geometry: {
      type: 'POINT',
      points: [{ x: point.x ?? point.lng, y: point.y ?? point.lat }]
    },
    bufferDistance,
    hasGeometry: returnGeometry
  };
  if (bufferDistanceUnit) requestBody.bufferDistanceUnit = bufferDistanceUnit;
  if (attributeFilter) requestBody.attributeFilter = attributeFilter;
  if (fields) requestBody.fields = fields;

  try {
    console.log(`🔍 缓冲区查询: 中心(${point.x ?? point.lng}, ${point.y ?? point.lat}), 半径${bufferDistance}`);
    const response = await executeQuery(requestBody);
    const features = extractFeatures(response.data);
    return { success: true, count: features?.length || 0, features: features || [] };
  } catch (error) {
    console.error('❌ 缓冲区查询失败:', error.message);
    return { success: false, count: 0, features: [], error: error.message };
  }
}

/**
 * 空间查询 - 按空间关系查询（相交/包含/在内/分离）
 */
async function queryBySpatial(params) {
  const { geometry, spatialQueryMode, attributeFilter, returnGeometry = true, fields } = params;
  if (!geometry || !spatialQueryMode) {
    return { success: false, error: '缺少 geometry 或 spatialQueryMode 参数' };
  }

  const mode = attributeFilter ? 'SPATIAL_ATTRIBUTEFILTER' : 'SPATIAL';
  const requestBody = {
    getFeatureMode: mode,
    datasetNames: [buildDatasetName(DATA_SOURCE, DATASET_NAME)],
    geometry,
    spatialQueryMode,
    hasGeometry: returnGeometry
  };
  if (attributeFilter) requestBody.attributeFilter = attributeFilter;
  if (fields) requestBody.fields = fields;

  try {
    console.log(`🔍 空间查询: ${spatialQueryMode}`);
    const response = await executeQuery(requestBody);
    const features = extractFeatures(response.data);
    return { success: true, count: features?.length || 0, features: features || [] };
  } catch (error) {
    console.error('❌ 空间查询失败:', error.message);
    return { success: false, count: 0, features: [], error: error.message };
  }
}

/**
 * 仅计数查询 - 只返回数量，不返回数据
 */
async function queryCount(params) {
  const { villageName, cityName, type } = params;
  const filters = [];
  if (villageName) filters.push(`BZMC LIKE '%${villageName}%'`);
  if (cityName) filters.push(`QXMC LIKE '%${cityName}%'`);
  if (type) filters.push(`PTLX LIKE '%${type}%'`);
  const attributeFilter = filters.length > 0 ? filters.join(' AND ') : 'SMID >= 0';

  const requestBody = {
    getFeatureMode: 'SQL',
    datasetNames: [buildDatasetName(DATA_SOURCE, DATASET_NAME)],
    queryParameter: { attributeFilter, fields: ['SMID'] },
    hasGeometry: false
  };
  try {
    const response = await axios.post(buildQueryUrl(), requestBody, {
      params: { returnContent: true, returnCountOnly: true },
      headers: { 'Content-Type': 'application/json' },
      timeout: 10000
    });
    const totalCount = response.data?.totalCount ?? response.data?.count ?? 0;
    return { success: true, count: totalCount };
  } catch (error) {
    console.error('❌ 计数查询失败:', error.message);
    return { success: false, count: 0, error: error.message };
  }
}

/**
 * 按要素 ID 查询详情
 */
async function getFeatureById(params) {
  const { featureId, hasGeometry = true } = params;
  if (!featureId) return { success: false, error: '缺少 featureId' };

  const { smid } = parseFeatureId(featureId);
  const url = `${SUPERMAP_BASE_URL}/datasources/${encodeURIComponent(DATA_SOURCE)}/datasets/${DATASET_NAME}/features/${smid}`;

  try {
    const response = await axios.get(url, {
      params: { hasGeometry, returnContent: true },
      headers: { 'Accept': 'application/json' },
      timeout: 10000
    });
    const feature = response.data;
    if (!feature) return { success: false, error: '要素不存在' };

    const props = feature.properties || {};
    const resultProps = {};
    VILLAGE_FIELDS.forEach(field => {
      if (props[field] !== undefined) resultProps[field] = props[field];
    });
    return { success: true, feature: { ...feature, properties: resultProps }, properties: resultProps };
  } catch (error) {
    console.error('❌ 查询要素详情失败:', error.message);
    return { success: false, error: error.message };
  }
}

// ============================================================
// 综合查询 + 地图配置
// ============================================================

/**
 * SQL 查询 + 自动上图
 */
async function queryAndMap(params) {
  const { villageName, cityName, type } = params;
  const effectiveName = (villageName || '阿氏村').trim();

  console.log(`\n🗺️  SuperMap 村庄查询与地图可视化`);
  console.log(`   =${'='.repeat(40)}`);

  const queryResult = await queryVillage({ villageName: effectiveName, cityName, type, returnGeometry: true });

  if (!queryResult.success || queryResult.features.length === 0) {
    return {
      success: false,
      markdown: `❌ 未找到包含 "${effectiveName}" 的村庄数据。`,
      features: [], count: 0, message: '未找到匹配数据'
    };
  }

  let center = DEFAULT_CENTER;
  let zoom = DEFAULT_ZOOM;
  const firstFeature = queryResult.features[0];
  if (firstFeature?.geometry?.center) {
    center = [firstFeature.geometry.center.y, firstFeature.geometry.center.x];
    zoom = 14;
  }

  const mapConfig = {
    type: 'map',
    status: 'complete',
    isComplete: true,
    title: `村庄查询 - ${effectiveName}`,
    center, zoom,
    layers: buildLayersConfig(),
    queryParams: { villageName: effectiveName, cityName: cityName || '', type: type || '' },
    summary: { count: queryResult.features.length, hasResult: true }
  };

  const markdown = buildMapMarkdown(mapConfig);
  console.log(`✅ 查询完成，共 ${queryResult.features.length} 条`);
  console.log(`📍 中心点: [${center[0]}, ${center[1]}]`);

  return { success: true, markdown, count: queryResult.features.length, villageName: effectiveName, queryParams: { villageName: effectiveName, cityName, type } };
}

/**
 * 范围查询 + 自动上图
 */
async function queryAndMapByBounds(params) {
  const { bounds, attributeFilter, title } = params;
  const desc = title || `范围查询`;

  console.log(`\n🗺️  范围查询与地图可视化: ${desc}`);

  const queryResult = await queryByBounds({ bounds, attributeFilter, returnGeometry: true });

  if (!queryResult.success || !queryResult.features?.length) {
    return { success: false, markdown: `❌ 指定范围内未找到村庄数据。`, count: 0 };
  }

  const centerLat = (bounds.leftBottom?.y + bounds.rightTop?.y) / 2;
  const centerLng = (bounds.leftBottom?.x + bounds.rightTop?.x) / 2;

  const mapConfig = {
    type: 'map',
    status: 'complete',
    isComplete: true,
    title: desc,
    center: [centerLat, centerLng],
    zoom: 12,
    layers: buildLayersConfig(),
    queryParams: {
      villageName: queryResult.features[0]?.properties?.BZMC || '',
      cityName: '',
      type: ''
    },
    summary: { count: queryResult.count, hasResult: true }
  };

  const markdown = buildMapMarkdown(mapConfig);
  return { success: true, markdown, count: queryResult.count, features: queryResult.features };
}

/**
 * 缓冲区查询 + 自动上图
 */
async function queryAndMapByBuffer(params) {
  const { point, bufferDistance, bufferDistanceUnit, attributeFilter, title } = params;
  const desc = title || `缓冲区查询`;

  console.log(`\n🗺️  缓冲区查询与地图可视化: ${desc}`);

  const queryResult = await queryByBuffer({ point, bufferDistance, bufferDistanceUnit, attributeFilter, returnGeometry: true });

  if (!queryResult.success || !queryResult.features?.length) {
    return { success: false, markdown: `❌ 指定缓冲区范围内未找到村庄数据。`, count: 0 };
  }

  const mapConfig = {
    type: 'map',
    status: 'complete',
    isComplete: true,
    title: desc,
    center: [point.y ?? point.lat, point.x ?? point.lng],
    zoom: 13,
    layers: buildLayersConfig(),
    queryParams: {
      villageName: queryResult.features[0]?.properties?.BZMC || '',
      cityName: '',
      type: ''
    },
    summary: { count: queryResult.count, hasResult: true }
  };

  const markdown = buildMapMarkdown(mapConfig);
  return { success: true, markdown, count: queryResult.count, features: queryResult.features };
}

// ============================================================
// 导出模块
// ============================================================
module.exports = {
  default: queryAndMap,
  SUPERMAP_BASE_URL, SUPERMAP_MAP_URL, SUPERMAP_CHINA_MAP_URL, SUPERMAP_BOUNDARY_MAP_URL,
  DATA_SOURCE, DATASET_NAME, VILLAGE_FIELDS,
  DEFAULT_CENTER, DEFAULT_ZOOM, DEFAULT_BOUNDS,

  queryVillage,
  queryByIds,
  queryByBounds,
  queryByBuffer,
  queryBySpatial,
  queryCount,
  getFeatureById,
  queryAndMap,
  queryAndMapByBounds,
  queryAndMapByBuffer,

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
    const result = await queryAndMap({ villageName });
    console.log(result.markdown || JSON.stringify(result, null, 2));
  })().catch(console.error);
}