const axios = require('axios');

// ============================================================
// 常量配置
// ============================================================

// SuperMap iServer 秦岭数据服务（统一数据源 qinling，数据集：camera / uav / member / satellite）
const QINLING_DATA_BASE_URL = 'http://172.16.235.50:18090/iserver/services/data-qinling/rest/data';
const QINLING_DATASOURCE = 'qinling';
const QINLING_FEATURE_URL = `${QINLING_DATA_BASE_URL}/featureResults.json?returnContent=true`;
const QINLING_DATASETS_URL = `${QINLING_DATA_BASE_URL}/datasources/${QINLING_DATASOURCE}/datasets`;

// 摄像头数据查询地址（data-camera 已并入秦岭数据服务，保留常量名以兼容既有调用方）
const CAMERA_DATA_URL = QINLING_FEATURE_URL;

// 地理编码服务地址（矢量数据主库）
const GEOCODING_URL = 'http://172.16.235.50:18090/iserver/services/addressmatch-ShiLiangShuJu/restjsr/v1/address/geocoding.json';

// 地理编码回退服务（中国地名地址库，主库无结果时使用）
const GEOCODING_FALLBACK_URL = 'http://172.16.235.50:18090/iserver/services/addressmatch-wj_gis_ZhongGuo_DiMingDiZhiKu/restjsr/v1/address/geocoding.json';
const GEOCODING_FALLBACK_MIN_SCORE = 60;  // 回退库模糊匹配宽松，过滤低分候选（百分比）

// 地图服务 URL（多层叠加）
const SUPERMAP_MAP_URL = 'http://172.16.235.50:18090/iserver/services/map-ugcv5-wj_gis_chinaworld_img/rest/maps/world_image';           // 底图：世界地图
const SUPERMAP_CHINA_MAP_URL = 'http://172.16.235.50:18090/iserver/services/map-ugcv5-wj_gis_china_img/rest/maps/china_image';          // 叠加：中国地图
const SUPERMAP_BOUNDARY_MAP_URL = 'http://172.16.235.50:18090/iserver/services/map-wj_gis_ZhongGuo_XingZhengJingJie/rest/maps/wj_gis_%E4%B8%AD%E5%9B%BD_%E8%A1%8C%E6%94%BF%E5%A2%83%E7%95%8C';  // 叠加：中国行政境界
const SUPERMAP_SHANXI_MAP_URL = 'http://172.16.235.50:18090/iserver/services/map-ugcv5-wj_gis_YingXiang_ShanXi3/rest/maps/wj_gis_%E5%BD%B1%E5%83%8F_%E9%99%95%E8%A5%BF';  // 叠加：陕西地图

const DATASET_NAME = `${QINLING_DATASOURCE}:camera`;
const DEFAULT_CENTER = [33.972476, 108.689005];
const DEFAULT_ZOOM = 13;

// 通用配置
const METERS_PER_DEGREE = 111319.49;  // 米/度，用于缓冲区半径换算
const REQUEST_TIMEOUT = 15000;         // 请求超时（毫秒）
const MAX_FEATURES = 1000;             // 单次查询最大要素数
const VIDEO_STREAM_API = 'http://10.17.49.196:36003/jeecg-boot/camera/newCameraInfo/getCameraUrl';  // 视频流播放接口

// 秦岭数据服务数据集（无人机、网格员、摄像头、历史火情）
const QINLING_DATASOURCES = {
  uav:       { label: '无人机',   datasetName: `${QINLING_DATASOURCE}:uav` },
  member:    { label: '网格员',   datasetName: `${QINLING_DATASOURCE}:member` },
  camera:    { label: '摄像头',   datasetName: `${QINLING_DATASOURCE}:camera` },
  satellite: { label: '历史火情', datasetName: `${QINLING_DATASOURCE}:satellite` },
};

// ============================================================
// 通用工具函数
// ============================================================

/**
 * Haversine 公式计算两点间球面距离
 * @param {number} lng1 - 起点经度
 * @param {number} lat1 - 起点纬度
 * @param {number} lng2 - 终点经度
 * @param {number} lat2 - 终点纬度
 * @returns {number} 距离（米，四舍五入取整）
 */
function haversineDistance(lng1, lat1, lng2, lat2) {
  const R = 6371000; // 地球半径（米）
  const toRad = (deg) => deg * Math.PI / 180;
  const dLat = toRad(lat2 - lat1);
  const dLng = toRad(lng2 - lng1);
  const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
            Math.sin(dLng / 2) * Math.sin(dLng / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return Math.round(R * c);
}

/**
 * 从 iServer 响应中提取要素数组（兼容多种响应格式）
 * @param {Object} data - iServer 接口响应
 * @returns {Array|null} 要素数组，无匹配时返回 null
 */
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

/**
 * 为要素标注到查询点的距离（_distance，单位米）并按距离升序排序
 * @param {Array} features - 要素数组（原地修改）
 * @param {number} lng - 查询点经度
 * @param {number} lat - 查询点纬度
 */
function annotateFeaturesDistance(features, lng, lat) {
  features.forEach(f => {
    const geo = f.geometry;
    if (!geo) return;
    // 兼容不同几何格式：POINT 直接坐标 / points / partPoints / point / 带中心点 / GeoJSON coordinates
    const pt = geo.points?.[0]
      ?? (Array.isArray(geo.partPoints?.[0]) ? geo.partPoints[0][0] : null)
      ?? geo.point;
    const fx = geo.x ?? pt?.x ?? geo.center?.x ?? (geo.coordinates ? geo.coordinates[0] : null);
    const fy = geo.y ?? pt?.y ?? geo.center?.y ?? (geo.coordinates ? geo.coordinates[1] : null);
    if (fx != null && fy != null) {
      f._distance = haversineDistance(lng, lat, fx, fy);
    }
  });
  features.sort((a, b) => (a._distance ?? Infinity) - (b._distance ?? Infinity));
}

/**
 * 计算要素集的距离统计（最近/最远/平均）
 * @param {Array} features - 已标注 _distance 的要素数组
 * @returns {Object} { minDistance, maxDistance, avgDistance }，无有效距离时返回 {}
 */
function computeDistanceStats(features) {
  const distances = features.map(f => f._distance).filter(d => d != null);
  if (distances.length === 0) return {};
  return {
    minDistance: Math.min(...distances),
    maxDistance: Math.max(...distances),
    avgDistance: Math.round(distances.reduce((a, b) => a + b, 0) / distances.length)
  };
}

/**
 * 格式化距离（米 → 易读文本）
 * @param {number} meters - 距离（米）
 * @returns {string} 如 '320m' / '1.2km'
 */
function formatDistance(meters) {
  if (meters == null) return '-';
  return meters < 1000 ? `${meters}m` : `${(meters / 1000).toFixed(1)}km`;
}

// 各类型实体名称字段优先级（兼容 SuperMap 字段命名差异）
const ENTITY_NAME_FIELDS = {
  camera: ['name', 'CAMERANAME', 'DEVICENAME', 'ADDRESS'],
  uav: ['DEVICENAME', 'NAME', 'UAVNAME', 'DEVICECODE'],
  member: ['REAL_NAME', 'USERNAME', 'NAME', 'POSITION'],
  satellite: ['NAME', 'FIRE_NAME', 'ADDRESS', 'POSITION', 'LOCATION']
};

/**
 * 从要素中提取实体名称
 * 兼容 SuperMap（fieldNames/fieldValues）与 GeoJSON（properties）两种结构
 * @param {Object} feature - 要素对象
 * @param {string} [type='camera'] - 实体类型
 * @returns {string} 实体名称，无法提取时返回空字符串
 */
function extractFeatureName(feature, type = 'camera') {
  let info = null;
  if (Array.isArray(feature?.fieldNames) && Array.isArray(feature?.fieldValues)) {
    info = {};
    feature.fieldNames.forEach((key, i) => { info[key] = feature.fieldValues[i]; });
  } else if (feature?.properties && typeof feature.properties === 'object') {
    info = feature.properties;
  }
  if (!info) return '';

  const fields = ENTITY_NAME_FIELDS[type] || ENTITY_NAME_FIELDS.camera;
  for (const field of fields) {
    const value = info[field];
    if (value != null && String(value).trim()) return String(value).trim();
  }

  // 大小写不敏感兜底
  const lowerMap = {};
  Object.keys(info).forEach(k => { lowerMap[k.toLowerCase()] = info[k]; });
  for (const field of fields) {
    const value = lowerMap[field.toLowerCase()];
    if (value != null && String(value).trim()) return String(value).trim();
  }
  return '';
}

/**
 * 构建地图图层配置（世界底图 + 中国地图 + 行政境界 + 陕西地图）
 * @returns {Array} 图层配置数组
 */
function buildMapLayers() {
  return [
    { type: 'tile', url: SUPERMAP_MAP_URL,          name: '世界地图底图', attribution: 'SuperMap' },
    { type: 'tile', url: SUPERMAP_CHINA_MAP_URL,    name: '中国地图叠加', attribution: 'SuperMap' },
    { type: 'tile', url: SUPERMAP_BOUNDARY_MAP_URL, name: '中国行政境界', attribution: 'SuperMap' },
    { type: 'tile', url: SUPERMAP_SHANXI_MAP_URL,   name: '陕西地图叠加', attribution: 'SuperMap' }
  ];
}

/**
 * 构建地图配置公共骨架（类型/状态/标题/中心点/缩放级别/图层）
 * 调用方在此基础上展开叠加各自专属字段（如 entityType、fireResponse、queryParams 等）
 * @param {Object} options - 骨架参数
 * @param {string} options.title - 地图标题
 * @param {number} options.lng - 中心点经度
 * @param {number} options.lat - 中心点纬度
 * @returns {Object} 基础地图配置
 */
function buildBaseMapConfig({ title, lng, lat }) {
  return {
    type: 'map',
    status: 'complete',
    isComplete: true,
    title,
    center: [lat, lng],
    zoom: DEFAULT_ZOOM,
    layers: buildMapLayers()
  };
}

/**
 * 将地图配置对象包装为 ```map 代码块（触发 Canvas 面板渲染）
 * @param {Object} mapConfig - 地图配置
 * @returns {string} markdown 文本
 */
function wrapMapMarkdown(mapConfig) {
  // 使用字符串拼接避免模板字面量中 \` 转义产生尾随反斜杠
  return '\n```map\n' + JSON.stringify(mapConfig, null, 2) + '\n```\n';
}

// ============================================================
// 地理编码：地址 → 经纬度
// ============================================================

/**
 * 调用指定地址匹配服务进行地理编码，返回标准化候选列表
 * @param {string} url - 地址匹配服务地址
 * @param {string} address - 地址名称
 * @param {number} [minScore=0] - 最低匹配分数（百分比），低于该值的候选被过滤
 * @returns {Promise<Array>} 候选列表 [{ score, address, lng, lat }]（按 score 降序）
 */
async function geocodeFromService(url, address, minScore = 0) {
  const response = await axios.get(url, {
    params: {
      address: address,
      fromIndex: 0,
      toIndex: 10,
      maxReturn: -1
    },
    timeout: REQUEST_TIMEOUT
  });

  let results = response.data;

  // 处理不同的响应格式
  if (results && !Array.isArray(results)) {
    if (Array.isArray(results.result)) results = results.result;
    else if (Array.isArray(results.geoCodingResultList)) results = results.geoCodingResultList;
    else results = [];
  }

  if (!results || results.length === 0) return [];

  // 标准化候选列表，按 score 降序排列
  return results
    .map(item => ({
      score: item.score || 0,
      address: item.address || '',
      lng: item.location?.x || 0,
      lat: item.location?.y || 0
    }))
    .filter(c => c.lng !== 0 && c.lat !== 0 && c.score >= minScore)
    .sort((a, b) => b.score - a.score);
}

/**
 * 地址地理编码：优先矢量数据主库，无结果时回退中国地名地址库
 * @param {string} address - 地址名称
 * @returns {Promise<Object>} { success, candidates: [{ score, address, lng, lat }], error? }
 */
async function geocodeAddress(address) {
  console.log(`🌍 正在对地址进行地理编码: "${address}"`);

  const services = [
    { url: GEOCODING_URL, label: '矢量数据主库', minScore: 0 },
    { url: GEOCODING_FALLBACK_URL, label: '中国地名地址库', minScore: GEOCODING_FALLBACK_MIN_SCORE }
  ];
  let lastError = null;

  for (const { url, label, minScore } of services) {
    try {
      const candidates = await geocodeFromService(url, address, minScore);
      if (candidates.length > 0) {
        console.log(`✅ 地理编码完成（${label}），找到 ${candidates.length} 个候选地址`);
        candidates.forEach((c, i) => {
          console.log(`${i + 1}. ${c.address} (匹配度: ${c.score}%, 坐标: ${c.lng}, ${c.lat})`);
        });
        return { success: true, candidates };
      }
      console.log(`⚠️ ${label}未找到匹配结果`);
    } catch (error) {
      lastError = error.message;
      console.error(`❌ ${label}地理编码失败:`, error.message);
    }
  }

  console.log(`❌ 地理编码未找到匹配结果`);
  return lastError
    ? { success: false, candidates: [], error: lastError }
    : { success: false, candidates: [] };
}

/**
 * 判断候选地址是否可自动选中（唯一结果，或最高分明显领先）
 * @param {Array} candidates - 候选地址列表（已按 score 降序）
 * @returns {boolean} true 表示可自动选中第一个候选
 */
function shouldAutoSelect(candidates) {
  if (!candidates || candidates.length === 0) return false;
  if (candidates.length === 1) return true;

  const topScore = candidates[0].score;
  const secondScore = candidates[1].score;

  // 最高分 >= 80 且与第二名分差 >= 15 → 自动选中
  return topScore >= 80 && (topScore - secondScore) >= 15;
}

/**
 * 构建候选地址列表 Markdown（用于多轮对话让用户选择）
 * @param {Array} candidates - 候选地址列表
 * @param {string} address - 用户原始输入地址
 * @returns {string} 候选列表 Markdown 文本
 */
function buildCandidateListMarkdown(candidates, address) {
  let md = `🌍 地址 "${address}" 找到以下匹配地点，请告诉我您要查询哪个位置附近的摄像头：\n\n`;
  candidates.forEach((c, i) => {
    md += `${i + 1}. **${c.address}**（匹配度 ${c.score}%）\n`;
  });
  md += `\n请回复序号选择具体位置，或输入更精确的地址重新查询。`;
  return md;
}

// ============================================================
// 数据查询：缓冲区查询
// ============================================================

/**
 * SuperMap 缓冲区查询（核心实现，供各数据源复用）
 * @param {Object} options - 查询参数
 * @param {string} options.url - featureResults 接口地址
 * @param {string} options.datasetName - 数据集名称，如 'camera:camera'
 * @param {string} options.label - 数据源中文名（用于日志与错误提示）
 * @param {number} options.lng - 中心点经度
 * @param {number} options.lat - 中心点纬度
 * @param {number} options.radius - 查询半径（米）
 * @returns {Promise<Object>} { success, count, features }
 */
async function queryByBuffer({ url, datasetName, label, lng, lat, radius }) {
  // 将米近似转换为度
  const degrees = radius / METERS_PER_DEGREE;

  const requestBody = {
    getFeatureMode: 'BUFFER',
    datasetNames: [datasetName],
    geometry: {
      type: 'POINT',
      points: [{ x: lng, y: lat }]
    },
    bufferDistance: degrees,
    maxFeatures: MAX_FEATURES
  };

  try {
    console.log(`🔍 正在查询${label}数据...`);
    console.log(`   中心点: [${lng}, ${lat}], 半径: ${radius}米, 数据源: ${datasetName}`);

    const response = await axios.post(url, requestBody, {
      headers: { 'Content-Type': 'application/json' },
      timeout: REQUEST_TIMEOUT
    });

    const features = extractFeatures(response.data) || [];

    if (features.length === 0) {
      console.log(`❌ 未找到匹配的${label}数据`);
      return { success: false, count: 0, features: [] };
    }

    // 标注距离并按距离升序排序
    annotateFeaturesDistance(features, lng, lat);

    console.log(`✅ 查询成功，共找到 ${features.length} 个${label}`);
    const stats = computeDistanceStats(features);
    if (stats.minDistance != null) {
      console.log(`   距离范围: ${stats.minDistance}m ~ ${stats.maxDistance}m，平均: ${stats.avgDistance}m`);
    }

    return { success: true, count: features.length, features };
  } catch (error) {
    console.error(`❌ 查询${label}失败:`, error.message);
    return { success: false, count: 0, features: [], error: error.message };
  }
}

/**
 * 摄像头缓冲区查询（秦岭数据服务 qinling:camera 数据集）
 * @param {Object} params - 查询参数
 * @param {number} params.lng - 中心点经度
 * @param {number} params.lat - 中心点纬度
 * @param {number} [params.radius=5000] - 查询半径（米）
 * @returns {Promise<Object>} { success, count, features }
 */
async function queryCamera(params) {
  const { lng, lat, radius = 5000 } = params;
  return queryByBuffer({ url: CAMERA_DATA_URL, datasetName: DATASET_NAME, label: '摄像头', lng, lat, radius });
}

/**
 * 秦岭数据缓冲区查询（无人机 / 网格员 / 摄像头 / 历史火情）
 * @param {Object} params - 查询参数
 * @param {string} params.type - 数据集类型：uav / member / camera / satellite
 * @param {number} params.lng - 中心点经度
 * @param {number} params.lat - 中心点纬度
 * @param {number} [params.radius=3000] - 查询半径（米）
 * @returns {Promise<Object>} { success, count, features, label }
 */
async function queryQinlingData({ type, lng, lat, radius = 3000 }) {
  const ds = QINLING_DATASOURCES[type];
  if (!ds) {
    console.error(`❌ 未知的秦岭数据源类型: ${type}`);
    return { success: false, count: 0, features: [], error: `未知数据源类型: ${type}` };
  }

  const result = await queryByBuffer({
    url: QINLING_FEATURE_URL,
    datasetName: ds.datasetName,
    label: ds.label,
    lng,
    lat,
    radius
  });

  return result.success ? { ...result, label: ds.label } : result;
}

/**
 * 查询附近无人机
 * @param {Object} params - 查询参数（同 queryQinlingData，不含 type）
 * @returns {Promise<Object>} 查询结果
 */
async function queryUAV(params) {
  return queryQinlingData({ type: 'uav', ...params });
}

/**
 * 查询附近网格员
 * @param {Object} params - 查询参数（同 queryQinlingData，不含 type）
 * @returns {Promise<Object>} 查询结果
 */
async function queryMember(params) {
  return queryQinlingData({ type: 'member', ...params });
}

/**
 * 查询附近秦岭摄像头
 * @param {Object} params - 查询参数（同 queryQinlingData，不含 type）
 * @returns {Promise<Object>} 查询结果
 */
async function queryQinlingCamera(params) {
  return queryQinlingData({ type: 'camera', ...params });
}

/**
 * 查询附近历史火情点
 * @param {Object} params - 查询参数（同 queryQinlingData，不含 type）
 * @returns {Promise<Object>} 查询结果
 */
async function querySatellite(params) {
  return queryQinlingData({ type: 'satellite', ...params });
}

// ============================================================
// 查询 + 地图配置构建
// ============================================================

/**
 * 通用查询执行器：执行缓冲区查询并构建地图配置（内部复用）
 * @param {Object} options - 查询参数
 * @param {string} [options.type='camera'] - 查询类型：camera / uav / member / satellite（均为秦岭数据服务下的数据集）
 * @param {number} options.lng - 中心点经度
 * @param {number} options.lat - 中心点纬度
 * @param {number} [options.radius=5000] - 查询半径（米）
 * @param {string} [options.resolvedAddress=''] - 已解析的地址（用于标题展示）
 * @returns {Promise<Object>} { success, markdown, count, queryParams, distance }
 */
async function executeQueryAndBuildMap({ type = 'camera', lng, lat, radius = 5000, resolvedAddress = '' }) {
  const isCamera = type === 'camera';
  const label = QINLING_DATASOURCES[type]?.label || '摄像头';

  const queryResult = isCamera
    ? await queryCamera({ lng, lat, radius })
    : await queryQinlingData({ type, lng, lat, radius });

  if (!queryResult.success || queryResult.features.length === 0) {
    const locationDesc = resolvedAddress || `坐标(${lng}, ${lat})`;
    console.log(`\n❌ 未找到匹配的${label}数据`);
    return {
      success: false,
      markdown: `❌ 在 ${locationDesc} 附近 ${radius}米 内未找到${label}数据。`,
      features: [],
      count: 0,
      message: '未找到匹配数据'
    };
  }

  const distanceStats = computeDistanceStats(queryResult.features);
  const titleLocation = resolvedAddress ? `${resolvedAddress}附近` : '';
  const title = `${label}周边查询 - ${titleLocation}半径 ${radius}m`;
  const queryParams = isCamera ? { lng, lat, radius } : { lng, lat, radius, type };

  // 构建 map 配置 - 只传递查询参数，不传递 features 数据（由前端按 queryParams 自行查询）
  const mapConfig = {
    ...buildBaseMapConfig({ title, lng, lat }),
    ...(isCamera
      ? { isCamera: true, videoStreamApi: VIDEO_STREAM_API }
      : { entityType: type, isCamera: false }),
    queryParams,
    summary: {
      count: queryResult.features.length,
      hasResult: true,
      ...distanceStats
    }
  };

  const markdown = wrapMapMarkdown(mapConfig);

  console.log(`\n✅ 查询完成，共找到 ${queryResult.features.length} 个${label}`);
  console.log(`📍 已生成地图配置（轻量级，不含几何数据），将触发 Canvas 渲染`);
  console.log(`📍 中心点: [${lat}, ${lng}]`);
  if (distanceStats.minDistance != null) {
    console.log(`📏 距离范围: ${distanceStats.minDistance}m ~ ${distanceStats.maxDistance}m，平均: ${distanceStats.avgDistance}m`);
  }

  return {
    success: true,
    markdown,
    count: queryResult.features.length,
    queryParams,
    distance: distanceStats
  };
}

/**
 * 执行摄像头查询并构建地图配置
 * @param {Object} options - 查询参数（同 executeQueryAndBuildMap，不含 type）
 * @returns {Promise<Object>} 查询结果
 */
async function executeCameraQueryAndBuildMap(options) {
  return executeQueryAndBuildMap({ type: 'camera', ...options });
}

/**
 * 执行秦岭数据查询并构建地图配置（无人机 / 网格员 / 历史火情）
 * @param {Object} options - 查询参数（同 executeQueryAndBuildMap，type 为 uav / member / satellite）
 * @returns {Promise<Object>} 查询结果
 */
async function executeQinlingQueryAndBuildMap({ type, lng, lat, radius = 3000, resolvedAddress = '' }) {
  return executeQueryAndBuildMap({ type, lng, lat, radius, resolvedAddress });
}

// ============================================================
// 多类型合并查询（单次调用 → 单个地图配置 → 四类实体同图叠加）
// ============================================================

// 各数据集默认查询半径（米）
const DEFAULT_ENTITY_RADIUS = { camera: 5000, uav: 3000, member: 3000, satellite: 5000 };
// 全部实体类型（type='all' 时使用）
const ALL_ENTITY_TYPES = ['camera', 'uav', 'member', 'satellite'];
// 实体图标（文本报告用）
const ENTITY_EMOJI = { camera: '📹', uav: '🚁', member: '👤', satellite: '🔥' };

/**
 * 多类型合并查询：一次调用并行查询多个数据集，输出**单个**地图配置
 *
 * 适用场景：用户一句话要求多种资源（如“查询北豆角村附近的摄像头、无人机、网格员和历史火情”）。
 * 必须单次调用完成，禁止对每种类型分别调用 queryAndMap：否则会产生多个 map 代码块，
 * 客户端只保留第一个，其余 Canvas 卡片会被丢弃。
 *
 * @param {Object} options - 查询参数
 * @param {string[]} [options.types] - 要查询的数据集类型，默认全部四种
 * @param {number} options.lng - 中心点经度
 * @param {number} options.lat - 中心点纬度
 * @param {number} [options.radius] - 统一查询半径（米）；不传则各类型用自身默认半径
 * @param {string} [options.resolvedAddress=''] - 已解析的地址（用于标题展示）
 * @returns {Promise<Object>} { success, markdown, count, entityGroups, queryParams, summary }
 */
async function executeMultiEntityQueryAndBuildMap({ types = ALL_ENTITY_TYPES, lng, lat, radius, resolvedAddress = '' }) {
  const validTypes = types.filter(t => QINLING_DATASOURCES[t]);
  if (validTypes.length === 0) {
    return { success: false, markdown: `❌ 未知的查询类型: ${types.join(', ')}`, count: 0, message: '未知查询类型' };
  }

  console.log(`\n🗺️  多类型合并查询: ${validTypes.map(t => QINLING_DATASOURCES[t].label).join('、')}`);

  // 并行查询各数据集（各自使用默认半径，除非显式指定统一 radius）
  const results = await Promise.all(validTypes.map(async (type) => {
    const typeRadius = radius || DEFAULT_ENTITY_RADIUS[type] || 5000;
    const result = await queryQinlingData({ type, lng, lat, radius: typeRadius });
    return { type, typeRadius, result };
  }));

  const entityGroups = [];
  const byType = {};
  for (const { type, typeRadius, result } of results) {
    const { label } = QINLING_DATASOURCES[type];
    const count = result.success ? result.count : 0;
    byType[type] = { label, count, radius: typeRadius };
    if (count > 0) {
      entityGroups.push({
        entityType: type,
        label,
        radius: typeRadius,
        count,
        queryParams: { lng, lat, radius: typeRadius, type }
      });
    }
    console.log(`   ${count > 0 ? '✅' : '➖'} ${label}: ${count} 个（${typeRadius}m 内）`);
  }

  const locationDesc = resolvedAddress || `坐标(${lng}, ${lat})`;
  if (entityGroups.length === 0) {
    return {
      success: false,
      markdown: `❌ 在 ${locationDesc} 附近未找到任何数据（${validTypes.map(t => QINLING_DATASOURCES[t].label).join('、')}）。`,
      entityGroups: [], count: 0, summary: byType, message: '未找到匹配数据'
    };
  }

  const titleLocation = resolvedAddress ? `${resolvedAddress}附近` : '';
  const title = `周边资源综合查询 - ${titleLocation}${entityGroups.map(g => g.label).join('、')}`;
  const totalCount = entityGroups.reduce((sum, g) => sum + g.count, 0);
  const maxRadius = Math.max(...entityGroups.map(g => g.radius));

  // 单个 map 配置：multiEntity + entityGroups，由前端在同一张地图上分类叠加渲染
  const mapConfig = {
    ...buildBaseMapConfig({ title, lng, lat }),
    multiEntity: true,
    isCamera: false,
    entityGroups,
    queryParams: { lng, lat, radius: maxRadius },
    summary: { count: totalCount, hasResult: true, byType }
  };

  // 文本报告 + 单个 map 代码块
  const foundLines = entityGroups.map(g => `- ${ENTITY_EMOJI[g.entityType]} **${g.label}**（${g.radius}m 内）：${g.count} 个`);
  const missingLabels = validTypes
    .filter(t => !entityGroups.some(g => g.entityType === t))
    .map(t => QINLING_DATASOURCES[t].label);
  let reportText = `📍 ${locationDesc} 周边资源查询结果：\n\n${foundLines.join('\n')}`;
  if (missingLabels.length > 0) reportText += `\n\n➖ 未找到：${missingLabels.join('、')}`;
  reportText += `\n\n**资源总计**: ${totalCount}`;

  const markdown = reportText + wrapMapMarkdown(mapConfig);

  console.log(`\n✅ 合并查询完成: ${entityGroups.length} 类共 ${totalCount} 个实体，已生成单个地图配置`);

  return {
    success: true,
    markdown,
    count: totalCount,
    entityGroups,
    queryParams: mapConfig.queryParams,
    summary: byType
  };
}

// ============================================================
// 火情应急响应级联查询
// ============================================================

// 火情应急各资源默认查询半径（米）——调度场景需尽可能覆盖全部可用资源
const FIRE_RESOURCE_RADIUS = { camera: 5000, uav: 10000, member: 5000, satellite: 5000 };
const FIRE_UAV_RECOMMEND_COUNT = 3;  // 建议优先调派的无人机数量（按距离最近，仅标记不截断）
const FIRE_GEOCODE_AUTO_SELECT_MIN_SCORE = 70;  // 应急场景地理编码自动选中最低分（百分比），低于此值仍需人工确认

/**
 * 火情应急资源全量查询：并行调取摄像头 / 无人机 / 网格员 / 历史火情
 *
 * 与旧级联逻辑的区别：**不做条件跳过**。旧逻辑在 1km 内有摄像头时会直接跳过无人机查询，
 * 并把无人机截断为最近 3 台，导致指挥人员拿不到完整资源清单。现在四类资源全量返回，
 * 仅对无人机标记“建议优先调派”（最近 N 台），最终调度决策交由用户。
 *
 * @param {Object} options - 查询参数
 * @param {number} options.lng - 火情点经度
 * @param {number} options.lat - 火情点纬度
 * @param {string} [options.fireArea=''] - 火情面积描述（仅用于日志）
 * @param {number|Object} [options.radius] - 查询半径（米）：传数字则四类统一，传对象则按类型覆盖
 * @returns {Promise<Object>} { inventory, radii, cameras, uavs, members, historyFires, recommendedUAVs, ... }
 */
async function queryFireResources({ lng, lat, fireArea = '', radius }) {
  console.log(`\n🔥 火情应急响应 - 可调度资源全量调取`);
  console.log(`   =${'='.repeat(40)}`);
  console.log(`   坐标: [${lng}, ${lat}], 火情面积: ${fireArea || '未知'}`);

  const resolveRadius = (type) => {
    if (typeof radius === 'number') return radius;
    return radius?.[type] || FIRE_RESOURCE_RADIUS[type];
  };

  // 四类资源并行查询（摄像头与其他三类已同属 qinling 数据源）
  const radii = {};
  const results = await Promise.all(ALL_ENTITY_TYPES.map(async (type) => {
    const typeRadius = resolveRadius(type);
    radii[type] = typeRadius;
    const res = await queryQinlingData({ type, lng, lat, radius: typeRadius });
    return { type, typeRadius, res };
  }));

  const inventory = {};
  for (const { type, typeRadius, res } of results) {
    const features = res.success ? res.features : [];
    inventory[type] = {
      label: QINLING_DATASOURCES[type].label,
      radius: typeRadius,
      features,
      count: features.length,
      stats: computeDistanceStats(features)
    };
    const emoji = ENTITY_EMOJI[type];
    const near = inventory[type].stats.minDistance != null
      ? `，最近 ${formatDistance(inventory[type].stats.minDistance)}`
      : '';
    console.log(`   ${emoji} ${inventory[type].label}（${typeRadius / 1000}km）: ${features.length > 0 ? `${features.length} 个${near}` : '无'}`);
  }

  // 标记建议优先调派的无人机（距离最近 N 台），全量数据保留供用户自行选择
  const recommendedUAVs = inventory.uav.features.slice(0, FIRE_UAV_RECOMMEND_COUNT);
  recommendedUAVs.forEach((f, i) => {
    f._recommended = true;
    f._recommendRank = i + 1;
  });

  const cameras = inventory.camera.features;
  const uavs = inventory.uav.features;
  const members = inventory.member.features;
  const historyFires = inventory.satellite.features;

  if (historyFires.length > 0) {
    console.log(`   ⚠️ ${radii.satellite / 1000}km 内存在 ${historyFires.length} 处历史火情，需注意复燃风险`);
  }

  const total = cameras.length + uavs.length + members.length;
  console.log(`\n✅ 资源调取完成：可调度资源共 ${total} 个（📹${cameras.length} 🚁${uavs.length} 👤${members.length}），历史火情 ${historyFires.length} 处`);

  return {
    inventory,
    radii,
    cameras,
    uavs,
    members,
    historyFires,
    recommendedUAVs,
    hasCamera: cameras.length > 0,
    hasUAV: uavs.length > 0,
    hasMember: members.length > 0,
    hasHistoryFire: historyFires.length > 0,
    // 兼容旧字段：全量模式下不再条件跳过无人机
    needsUAV: false,
    uavDispatched: false
  };
}

/**
 * 火情响应结果生成：从级联查询结果构建文本报告 + ```map 代码块
 * @param {Object} options - 生成参数
 * @param {number} options.lng - 火情点经度
 * @param {number} options.lat - 火情点纬度
 * @param {string} [options.fireArea=''] - 火情面积描述，如 '50亩'
 * @param {string} [options.resolvedAddress=''] - 已解析的地址（用于报告展示）
 * @param {Object} options.resources - queryFireResources 返回的级联查询结果
 * @returns {Object} { markdown, count, queryParams, summary }
 */
function buildFireResponse({ lng, lat, fireArea = '', resolvedAddress = '', resources }) {
  const {
    cameras = [], uavs = [], members = [], historyFires = [],
    inventory = {}, radii = {}, recommendedUAVs = [],
    hasCamera, hasMember, hasHistoryFire
  } = resources;

  // 构建标题与汇总
  const titleLocation = resolvedAddress ? `${resolvedAddress}附近` : '';
  const title = `🔥 火情应急响应 - ${titleLocation}${fireArea ? '面积 ' + fireArea : ''}`;

  const summary = {
    hasCamera,
    cameraCount: cameras.length,
    hasUAV: uavs.length > 0,
    uavCount: uavs.length,
    hasMember,
    memberCount: members.length,
    totalResources: cameras.length + uavs.length + members.length,
    // 历史火情为风险研判信息，不计入可调度资源总数
    hasHistoryFire: hasHistoryFire ?? historyFires.length > 0,
    historyFireCount: historyFires.length,
    // 各类资源查询半径（前端据此绘制分类型范围圈）
    radii,
    // 建议优先调派的无人机（距离最近 N 台，最终调度由用户决策）
    recommendedUAVs: recommendedUAVs.map(f => ({
      name: extractFeatureName(f, 'uav'),
      distance: f._distance
    })),
    fireArea
  };

  // 构建 map 配置（fireResponse 标记，前端同时渲染四类实体）
  // 轻量级：不携带全量 features（几何+字段数据量大，流式传输慢且易截断导致 map 代码块解析失败），
  // 仅下发中心点/半径/数量，前端收到后自动向 SuperMap 自查询并渲染
  const mapConfig = {
    ...buildBaseMapConfig({ title, lng, lat }),
    fireResponse: true,
    fireCenter: [lat, lng],
    fireArea,
    radii,
    cameras: { count: cameras.length },
    uavs: { count: uavs.length },
    members: { count: members.length },
    historyFires: { count: historyFires.length },
    summary
  };

  const markdown = wrapMapMarkdown(mapConfig);

  // 构建文本报告（可调度资源清单）
  const radiusKm = (type) => (radii[type] || FIRE_RESOURCE_RADIUS[type]) / 1000;
  let reportText = `## 🔥 火情应急响应报告\n\n`;
  reportText += `**位置**: ${resolvedAddress || `坐标(${lng}, ${lat})`}\n`;
  if (fireArea) reportText += `**火情面积**: ${fireArea}\n`;

  reportText += `\n### 可调度资源清单\n\n`;
  reportText += `| 类型 | 数量 | 查询范围 | 最近距离 |\n| --- | --- | --- | --- |\n`;
  ['camera', 'uav', 'member'].forEach(type => {
    const item = inventory[type] || {};
    const fallback = type === 'camera' ? cameras.length : (type === 'uav' ? uavs.length : members.length);
    const count = item.count ?? fallback;
    reportText += `| ${ENTITY_EMOJI[type]} ${QINLING_DATASOURCES[type].label} | ${count} | ${radiusKm(type)}km | ${formatDistance(item.stats?.minDistance)} |\n`;
  });
  reportText += `\n**可调度资源总计**: ${summary.totalResources}\n`;

  if (uavs.length > 0) {
    reportText += `\n### 建议优先调派（无人机 · 距离最近 ${recommendedUAVs.length} 台）\n\n`;
    recommendedUAVs.forEach((f, i) => {
      reportText += `${i + 1}. **${extractFeatureName(f, 'uav') || `无人机 ${i + 1}`}**（${formatDistance(f._distance)}）\n`;
    });
    reportText += `\n> 地图上已标出全部 ${uavs.length} 台无人机，可点击任意图标查看详情后自行调度。\n`;
  }

  if (members.length > 0) {
    const nearest = members[0];
    reportText += `\n### 现场处置力量\n\n`;
    reportText += `- 👤 最近网格员：**${extractFeatureName(nearest, 'member') || '网格员'}**（${formatDistance(nearest._distance)}），共 ${members.length} 名可派往现场\n`;
  }

  reportText += `\n### 复燃风险提示\n\n`;
  reportText += summary.historyFireCount > 0
    ? `- 🔥 ${radiusKm('satellite')}km 内存在 **${summary.historyFireCount} 处历史火情**，建议重点巡查并防范复燃\n`
    : `- ✅ ${radiusKm('satellite')}km 内无历史火情记录\n`;

  if (summary.totalResources === 0) {
    reportText += `\n> ⚠️ 当前范围内未查询到可调度资源，建议扩大查询半径后重试。\n`;
  }

  console.log(`\n✅ 火情响应完成: 📹${cameras.length} 🚁${uavs.length} 👤${members.length} | 历史火情 ${historyFires.length} 处`);

  const maxRadius = Math.max(...Object.values({ ...FIRE_RESOURCE_RADIUS, ...radii }));
  return {
    markdown: reportText + '\n' + markdown,
    count: summary.totalResources,
    queryParams: { lng, lat, radius: maxRadius, type: 'fire' },
    summary
  };
}

/**
 * 火情应急响应：级联查询 + 生成报告与地图（组合入口）
 * @param {Object} options - 查询参数
 * @param {number} options.lng - 火情点经度
 * @param {number} options.lat - 火情点纬度
 * @param {string} [options.fireArea=''] - 火情面积描述，如 '50亩'
 * @param {string} [options.resolvedAddress=''] - 已解析的地址（用于报告展示）
 * @param {number|Object} [options.radius] - 查询半径（米）：不传则各资源类型用自身默认半径
 * @returns {Promise<Object>} { success, markdown, count, queryParams, summary }
 */
async function queryFireResponse({ lng, lat, fireArea = '', resolvedAddress = '', radius }) {
  const resources = await queryFireResources({ lng, lat, fireArea, radius });
  return {
    success: true,
    ...buildFireResponse({ lng, lat, fireArea, resolvedAddress, resources })
  };
}

// ============================================================
// 综合查询入口（支持地址 + 坐标两种模式，支持 type 分发）
// ============================================================

/**
 * 综合查询入口：地址/坐标 → 地理编码（可选）→ 按类型分发查询 → 生成地图
 *
 * 返回值包含 markdown 字段（```map 代码块或候选列表），系统解析后自动打开 Canvas 面板。
 *
 * @param {Object} params - 查询参数
 * @param {string} [params.address] - 地址名称（与 lng/lat 二选一，同时提供时优先坐标）
 * @param {number} [params.lng] - 经度
 * @param {number} [params.lat] - 纬度
 * @param {number} [params.radius] - 查询半径（米），默认按类型：fire 1000 / uav、member 3000 / camera、satellite 5000
 * @param {string} [params.type='camera'] - 查询类型：camera / uav / member / satellite / all（多类型合并）/ fire
 * @param {string[]} [params.types] - 显式指定多个类型（与 type='all' 等效），如 ['camera','uav']
 * @param {string} [params.fireArea=''] - 火情面积（仅 type='fire' 时有效）
 * @returns {Promise<Object>} 查询结果，多候选地址时返回 needsDisambiguation: true
 */
async function queryAndMap(params) {
  const { address, lng, lat, radius, type = 'camera', fireArea = '' } = params;

  // 多类型合并查询：用户一句话要求多种资源时必须走此分支（只生成一个 map 代码块）
  const multiTypes = Array.isArray(params.types) ? params.types : null;
  const isMulti = type === 'all' || !!multiTypes;

  const dsLabel = type === 'fire'
    ? '火情应急响应'
    : isMulti
      ? `周边资源综合（${(multiTypes || ALL_ENTITY_TYPES).map(t => QINLING_DATASOURCES[t]?.label).filter(Boolean).join('、')}）`
      : (QINLING_DATASOURCES[type]?.label || '摄像头');
  console.log(`\n🗺️  SuperMap ${dsLabel}查询与地图可视化`);
  console.log(`   =${'='.repeat(40)}`);

  // 按类型选择默认半径（米）；多类型合并时不强制统一，由各数据集自身默认半径决定
  // fire / 多类型合并：不强制统一半径，由各资源类型自身默认半径决定
  const defaultRadius = (isMulti || type === 'fire')
    ? null
    : (type === 'uav' || type === 'member') ? 3000 : 5000;
  const effectiveRadius = radius || defaultRadius;
  const radiusLabel = effectiveRadius != null ? `${effectiveRadius}m` : '按类型默认';
  const parsedRadius = effectiveRadius != null ? parseFloat(effectiveRadius) : undefined;

  // 统一查询执行器：根据 type 分发
  const executeQuery = ({ lng, lat, radius, resolvedAddress = '' }) => {
    if (type === 'fire') {
      return queryFireResponse({ lng, lat, fireArea, resolvedAddress, radius });
    }
    if (isMulti) {
      return executeMultiEntityQueryAndBuildMap({
        types: multiTypes || ALL_ENTITY_TYPES,
        lng, lat, radius, resolvedAddress
      });
    }
    return executeQueryAndBuildMap({ type, lng, lat, radius, resolvedAddress });
  };

  // ===== 坐标模式（lng/lat 已提供，优先使用） =====
  if (lng != null && lat != null) {
    console.log(`📍 坐标模式: lng=${lng}, lat=${lat}, radius=${radiusLabel}, type=${type}`);
    return executeQuery({
      lng: parseFloat(lng),
      lat: parseFloat(lat),
      radius: parsedRadius,
      resolvedAddress: address || ''
    });
  }

  // ===== 地址模式 =====
  if (address) {
    console.log(`📍 地址模式: address="${address}", radius=${radiusLabel}, type=${type}`);

    // Step 1: 地理编码
    const geoResult = await geocodeAddress(address);

    if (!geoResult.success || geoResult.candidates.length === 0) {
      return {
        success: false,
        markdown: `❌ 无法识别地址 "${address}"，请检查地址是否正确或提供经纬度坐标。`,
        count: 0,
        message: '地理编码失败'
      };
    }

    // Step 2: 判断是否需要用户选择
    // 火情应急场景：跳过歧义确认，最高分候选达到应急门槛即直接采用（应急响应优先，减少对话轮次）
    const isEmergency = type === 'fire';
    const topCandidate = geoResult.candidates[0];
    const emergencyAutoSelect = isEmergency && topCandidate.score >= FIRE_GEOCODE_AUTO_SELECT_MIN_SCORE;
    if (shouldAutoSelect(geoResult.candidates) || emergencyAutoSelect) {
      const selected = topCandidate;
      if (emergencyAutoSelect && !shouldAutoSelect(geoResult.candidates)) {
        console.log(`🚨 应急模式：跳过地址歧义确认，直接采用最高分候选`);
      }
      console.log(`\n✅ 自动选中: "${selected.address}" (${selected.lng}, ${selected.lat})`);
      return executeQuery({
        lng: selected.lng,
        lat: selected.lat,
        radius: parsedRadius,
        resolvedAddress: selected.address
      });
    }

    // Step 3: 多候选 → 返回候选列表让用户选择
    console.log(`\n🔀 找到多个候选地址，需要用户选择`);
    return {
      success: true,
      needsDisambiguation: true,
      candidates: geoResult.candidates,
      markdown: buildCandidateListMarkdown(geoResult.candidates, address),
      count: 0,
      message: '请从候选列表中选择具体位置'
    };
  }

  // ===== 无参数：使用默认坐标 =====
  console.log(`📍 默认模式: 使用默认坐标, type=${type}`);
  return executeQuery({
    lng: DEFAULT_CENTER[1],
    lat: DEFAULT_CENTER[0],
    radius: parsedRadius
  });
}

// ============================================================
// 导出模块
// ============================================================
module.exports = {
  default: queryAndMap,
  CAMERA_DATA_URL,
  GEOCODING_URL,
  SUPERMAP_MAP_URL,
  SUPERMAP_CHINA_MAP_URL,
  SUPERMAP_BOUNDARY_MAP_URL,
  SUPERMAP_SHANXI_MAP_URL,
  VIDEO_STREAM_API,
  DATASET_NAME,
  DEFAULT_CENTER,
  DEFAULT_ZOOM,

  // 秦岭数据服务（camera / uav / member / satellite）
  QINLING_DATA_BASE_URL,
  QINLING_DATASOURCE,
  QINLING_FEATURE_URL,
  QINLING_DATASETS_URL,
  QINLING_DATASOURCES,
  ALL_ENTITY_TYPES,
  DEFAULT_ENTITY_RADIUS,
  FIRE_RESOURCE_RADIUS,
  FIRE_UAV_RECOMMEND_COUNT,
  executeMultiEntityQueryAndBuildMap,
  queryQinlingData,
  queryUAV,
  queryMember,
  queryQinlingCamera,
  querySatellite,

  queryCamera,
  queryAndMap,
  extractFeatures,
  geocodeAddress,
  haversineDistance,
  shouldAutoSelect,
  buildCandidateListMarkdown,

  // 工具函数
  queryByBuffer,
  annotateFeaturesDistance,
  computeDistanceStats,
  formatDistance,
  extractFeatureName,
  buildMapLayers,
  buildBaseMapConfig,
  wrapMapMarkdown,

  // 查询执行器
  executeQueryAndBuildMap,
  executeCameraQueryAndBuildMap,
  executeQinlingQueryAndBuildMap,

  // 火情应急响应
  queryFireResponse,
  queryFireResources,
  buildFireResponse
};

// ============================================================
// CLI 入口
// ============================================================
if (require.main === module) {
  (async () => {
    try {
      const args = process.argv.slice(2);

      // 解析参数
      let address = null;
      let lng = null;
      let lat = null;
      let radius = 5000;

      // 检查 --address 标志
      const addressFlagIndex = args.indexOf('--address');
      if (addressFlagIndex !== -1 && args[addressFlagIndex + 1]) {
        address = args[addressFlagIndex + 1];
        if (args[addressFlagIndex + 2]) {
          radius = parseFloat(args[addressFlagIndex + 2]) || 5000;
        }
      } else if (args.length > 0) {
        // 判断第一个参数是否为数字（坐标）还是地址
        const firstArg = args[0];
        if (!isNaN(parseFloat(firstArg)) && args.length >= 2) {
          // 坐标模式
          lng = parseFloat(firstArg);
          lat = parseFloat(args[1]);
          radius = parseFloat(args[2]) || 5000;
        } else {
          // 地址模式
          address = firstArg;
          radius = parseFloat(args[1]) || 5000;
        }
      }

      console.log(`\n🗺️  SuperMap 摄像头周边查询工具`);
      console.log(`   =${'='.repeat(40)}`);

      if (address) {
        console.log(`   查询地址: "${address}", 搜索半径: ${radius}米\n`);
      } else if (lng != null && lat != null) {
        console.log(`   中心坐标: [${lng}, ${lat}], 搜索半径: ${radius}米\n`);
      } else {
        console.log(`   使用默认坐标, 搜索半径: ${radius}米\n`);
      }

      const result = await queryAndMap({ address, lng, lat, radius });

      if (result.needsDisambiguation) {
        console.log(`\n🔀 需要用户选择，候选地址:`);
        result.candidates.forEach((c, i) => {
          console.log(`   ${i + 1}. ${c.address} (匹配度: ${c.score}%, 坐标: ${c.lng}, ${c.lat})`);
        });
      } else if (result.success) {
        console.log(`\n📊 查询到 ${result.count} 个摄像头`);
        if (result.distance && result.distance.minDistance != null) {
          console.log(`📏 最近: ${result.distance.minDistance}m, 最远: ${result.distance.maxDistance}m, 平均: ${result.distance.avgDistance}m`);
        }
      } else {
        console.log('\n❌ 查询失败:', result.message || result.markdown);
      }
    } catch (error) {
      console.error('执行失败:', error.message);
      process.exit(1);
    }
  })();
}
