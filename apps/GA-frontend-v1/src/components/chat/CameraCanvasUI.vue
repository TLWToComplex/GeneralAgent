<template>
  <div class="supermap-wrapper" ref="wrapper">
    <!-- Map container -->
    <div ref="mapContainer" class="map-container"></div>

    <!-- 工具栏 -->
    <div class="draw-toolbar">
      <div class="tool-group">
        <button @click="zoomIn" class="tool-btn" title="放大 (+)">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="16"></line>
            <line x1="8" y1="12" x2="16" y2="12"></line>
          </svg>
        </button>
        <button @click="zoomOut" class="tool-btn" title="缩小 (-)">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="8" y1="12" x2="16" y2="12"></line>
          </svg>
        </button>
        <button @click="resetView" class="tool-btn" title="重置视图 (R)">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="1 4 1 10 7 10"></polyline>
            <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"></path>
          </svg>
        </button>
        <div class="tool-divider"></div>
        <button @click="toggleFullScreen" class="tool-btn" :title="isFullScreen ? '退出全屏 (Esc)' : '全屏浏览 (F)'">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path v-if="!isFullScreen" d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" />
            <path v-else d="M4 14h6v6M20 10h-6V4M14 10l7-7M10 14l-7 7" />
          </svg>
        </button>
      </div>
    </div>

    <!-- 数据条数标签 -->
    <div v-if="dataCount > 0" class="data-count-badge">📹 {{ dataCount }} 个摄像头</div>

    <!-- 加载提示 -->
    <div class="loading-toast" :class="{ show: isLoading }">
      <div class="loading-spinner-small"></div>
      <span>{{ loadingMessage }}</span>
    </div>

    <!-- 初始化提示 -->
    <div class="init-toast" :class="{ show: showInitToast }">{{ initToastMessage }}</div>

    <!-- 无人机飞行目的地设置面板（支持地图点选与输入坐标） -->
    <div v-if="uavPickMode" class="uav-pick-panel">
      <div class="uav-pick-head">
        <span class="uav-pick-dot"></span>
        <span class="uav-pick-title">🛫 设置无人机飞行目的地</span>
        <button class="uav-pick-cancel" @click="exitUavPickMode">取消</button>
      </div>

      <div class="uav-pick-tabs">
        <button
          class="uav-pick-tab"
          :class="{ active: uavPickTab === 'map' }"
          @click="switchUavPickTab('map')"
        >🖥️ 地图点选</button>
        <button
          class="uav-pick-tab"
          :class="{ active: uavPickTab === 'coord' }"
          @click="switchUavPickTab('coord')"
        >⌨️ 输入坐标</button>
      </div>

      <div v-if="uavPickTab === 'map'" class="uav-pick-hint">
        请在地图上点击火情报警位置，放置 🎯 标记后确认起飞
      </div>

      <div v-else class="uav-pick-coord">
        <div class="uav-pick-fields">
          <label class="uav-pick-field">
            <span>经度</span>
            <input
              v-model="uavCoordLng"
              type="number"
              step="0.000001"
              placeholder="108.689005"
              @keyup.enter="submitUavCoord"
            />
          </label>
          <label class="uav-pick-field">
            <span>纬度</span>
            <input
              v-model="uavCoordLat"
              type="number"
              step="0.000001"
              placeholder="33.972476"
              @keyup.enter="submitUavCoord"
            />
          </label>
        </div>
        <div class="uav-pick-range">
          可飞范围：经度 {{ MAP_BOUNDS_LNG[0] }} ~ {{ MAP_BOUNDS_LNG[1] }}，纬度 {{ MAP_BOUNDS_LAT[0] }} ~ {{ MAP_BOUNDS_LAT[1] }}
        </div>
        <div v-if="uavCoordError" class="uav-pick-error">⚠️ {{ uavCoordError }}</div>
        <div class="uav-pick-actions">
          <button class="uav-pick-btn ghost" @click="previewUavCoord">🎯 定位预览</button>
          <button class="uav-pick-btn primary" @click="submitUavCoord">✅ 确认起飞</button>
        </div>
      </div>
    </div>

    <!-- 错误面板 -->
    <div v-if="error" class="error-panel">
      <div class="error-header" @click="isErrorExpanded = !isErrorExpanded">
        <div class="error-summary">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="error-icon">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
            <line x1="12" y1="9" x2="12" y2="13"></line>
            <line x1="12" y1="17" x2="12.01" y2="17"></line>
          </svg>
          <span class="error-text-summary">{{ error }}</span>
        </div>
        <div class="header-actions">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="chevron-icon" :class="{ rotated: isErrorExpanded }">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </div>
      </div>
      <div class="error-details-wrapper" :class="{ expanded: isErrorExpanded }">
        <div class="error-details-inner">
          <div class="error-full-text">{{ error }}</div>
        </div>
      </div>
    </div>

    <!-- 视频流播放模态框 -->
    <div v-if="videoModalVisible" class="video-modal-overlay" @click.self="closeVideoModal">
      <div class="video-modal">
        <div class="video-modal-header">
          <span>{{ currentCameraName || '视频播放' }}</span>
          <button class="video-modal-close-btn" @click="closeVideoModal">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
        <div class="video-modal-body">
          <div v-if="videoLoading" class="video-loading">
            <div class="loading-spinner-small"></div>
            <span>正在获取视频流地址...</span>
          </div>
          <div ref="h5playerContainer" class="h5player-container"></div>
        </div>
      </div>
    </div>

    <!-- 右键菜单 -->
    <div
      v-show="contextMenuVisible"
      class="map-context-menu"
      :style="{ left: contextMenuPos.x + 'px', top: contextMenuPos.y + 'px' }"
      @click.stop
    >
      <div class="context-menu-header">
        <span class="context-menu-coord">📍 {{ contextMenuLatLng ? `${contextMenuLatLng.lng.toFixed(6)}, ${contextMenuLatLng.lat.toFixed(6)}` : '' }}</span>
        <button class="context-menu-close" title="关闭" @click="closeContextMenu">✕</button>
      </div>
      <div class="context-menu-divider"></div>
      <div
        v-for="opt in queryMenuOptions"
        :key="opt.key"
        class="context-menu-item"
        @click="selectQueryOption(opt.key)"
      >
        <span class="context-menu-icon">{{ opt.icon }}</span>
        <span class="context-menu-label">{{ opt.label }}</span>
      </div>
    </div>

    <!-- 查询对话框 -->
    <div v-if="queryDialogVisible" class="map-query-dialog-overlay" @click.self="closeQueryDialog">
      <div class="map-query-dialog">
        <div class="query-dialog-header">
          <span>{{ selectedQueryType?.icon }} {{ selectedQueryType?.label }}</span>
          <button class="query-dialog-close" @click="closeQueryDialog">✕</button>
        </div>
        <div class="query-dialog-body">
          <div class="query-field">
            <label>📍 查询坐标</label>
            <div class="query-coord-display">
              经度: {{ contextMenuLatLng?.lng.toFixed(6) }} &nbsp;|&nbsp; 纬度: {{ contextMenuLatLng?.lat.toFixed(6) }}
            </div>
          </div>
          <div class="query-field">
            <label>📏 查询半径: <strong>{{ queryRadius }}m</strong></label>
            <div class="query-radius-control">
              <input type="range" v-model.number="queryRadius" min="500" max="50000" step="500" />
              <input type="number" v-model.number="queryRadius" min="500" max="50000" step="500" />
            </div>
          </div>
          <div class="query-field">
            <label>💬 补充提示词（可选）</label>
            <textarea
              v-model="queryPrompt"
              placeholder="例如：重点关注高速公路沿线、只查询在线设备..."
              rows="3"
            ></textarea>
          </div>
        </div>
        <div class="query-dialog-footer">
          <button class="query-btn query-btn-cancel" @click="closeQueryDialog">取消</button>
          <button class="query-btn query-btn-confirm" @click="confirmQuery">🔍 发送查询</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import markerIcon2xUrl from 'leaflet/dist/images/marker-icon-2x.png?url';
import markerIconUrl from 'leaflet/dist/images/marker-icon.png?url';
import markerShadowUrl from 'leaflet/dist/images/marker-shadow.png?url';

import { useChatStore } from '@/stores/chat-store';
import iconDrone from '@/assets/image/png/icon-drone.png';
import fireVideoUrl from '@/assets/video/mp4/fire.mp4';
import fireVisibleLightUrl from '@/assets/image/jpg/可见光.jpg';
import fireThermalUrl from '@/assets/image/jpg/热成像.png';
import {
  getBoundaryMapServiceUrl,
  getChinaMapServiceUrl,
  getMapDataUrl,
  getMapServiceUrl,
  getMapVideoStreamApi,
  getQinlingMapDataUrl,
  getShanxiMapServiceUrl,
} from '@/utils/RuntimeConfig';

// SuperMap iClient
import * as SuperMapICL from '@supermapgis/iclient-leaflet';
void SuperMapICL;

// ============ Props ============
const props = defineProps<{
  content?: string;
  isComplete?: boolean;
  id?: string;
  title?: string;
  suspend?: boolean;
}>();

const emit = defineEmits<{
  (e: 'toggle-fullscreen'): void;
  (e: 'close'): void;
  (e: 'update:status', value: string): void;
}>();

// ============ Constants ============
const DEFAULT_QINLING_DATA_BASE_URL = 'http://172.16.235.50:18090/iserver/services/data-qinling/rest/data';
const DEFAULT_MAP_DATA_BASE_URL = 'http://172.16.235.50:18090/iserver/services/data-ShiLiangShuJu/rest/data';
const DEFAULT_VIDEO_STREAM_API = 'http://10.17.49.196:36003/jeecg-boot/camera/newCameraInfo/getCameraUrl';
const DEFAULT_SUPERMAP_MAP_URL = 'http://172.16.235.50:18090/iserver/services/map-ugcv5-wj_gis_chinaworld_img/rest/maps/world_image';
const DEFAULT_SUPERMAP_CHINA_MAP_URL = 'http://172.16.235.50:18090/iserver/services/map-ugcv5-wj_gis_china_img/rest/maps/china_image';
const DEFAULT_SUPERMAP_BOUNDARY_MAP_URL = 'http://172.16.235.50:18090/iserver/services/map-wj_gis_ZhongGuo_XingZhengJingJie/rest/maps/wj_gis_中国_行政境界';
const DEFAULT_SUPERMAP_SHANXI_MAP_URL = 'http://172.16.235.50:18090/iserver/services/map-ugcv5-wj_gis_YingXiang_ShanXi3/rest/maps/wj_gis_%E5%BD%B1%E5%83%8F_%E9%99%95%E8%A5%BF';

// 秦岭数据服务（统一数据源 qinling：摄像头 / 无人机 / 网格员 / 历史火情）
const QINLING_DATA_BASE_URL = getQinlingMapDataUrl() || DEFAULT_QINLING_DATA_BASE_URL;
const QINLING_DATA_URL = `${QINLING_DATA_BASE_URL}/featureResults.json?returnContent=true`;
// data-camera 已并入秦岭数据服务，保留常量名以兼容既有引用
const CAMERA_DATA_URL = QINLING_DATA_URL;
const VIDEO_STREAM_API = getMapVideoStreamApi() || DEFAULT_VIDEO_STREAM_API;

const SUPERMAP_MAP_URL = getMapServiceUrl() || DEFAULT_SUPERMAP_MAP_URL;
const SUPERMAP_CHINA_MAP_URL = getChinaMapServiceUrl() || DEFAULT_SUPERMAP_CHINA_MAP_URL;
const SUPERMAP_BOUNDARY_MAP_URL = getBoundaryMapServiceUrl() || DEFAULT_SUPERMAP_BOUNDARY_MAP_URL;
const SUPERMAP_SHANXI_MAP_URL = getShanxiMapServiceUrl() || DEFAULT_SUPERMAP_SHANXI_MAP_URL;
const MAP_DATA_BASE_URL = getMapDataUrl() || DEFAULT_MAP_DATA_BASE_URL;

// 矢量数据服务（区县 + 村庄）
const VILLAGE_DATA_URL = `${MAP_DATA_BASE_URL}/datasources/矢量数据4490/datasets/村庄`;
const DISTRICT_DATA_URL = `${MAP_DATA_BASE_URL}/datasources/矢量数据4490/datasets/区县级行政区`;

// 实体类型查询配置（URL + 数据集 + 名称字段）
const ENTITY_QUERY_CONFIG: Record<string, { url: string; datasetName: string; nameField: string }> = {
  camera:    { url: CAMERA_DATA_URL,  datasetName: 'qinling:camera',    nameField: 'name' },
  uav:       { url: QINLING_DATA_URL, datasetName: 'qinling:uav',       nameField: 'DEVICENAME' },
  member:    { url: QINLING_DATA_URL, datasetName: 'qinling:member',    nameField: 'USERNAME' },
  satellite: { url: QINLING_DATA_URL, datasetName: 'qinling:satellite', nameField: 'NAME' },
};

const DEFAULT_CENTER: [number, number] = [33.972476, 108.689005];
const DEFAULT_ZOOM = 13;

// 右键菜单查询类型配置
const QUERY_TYPES = [
  { key: 'uav', label: '查询附近无人机', icon: '🚁', typeName: '无人机', defaultRadius: 3000 },
  { key: 'camera', label: '查询附近摄像头', icon: '📹', typeName: '摄像头', defaultRadius: 5000 },
  { key: 'member', label: '查询附近网格员', icon: '👤', typeName: '网格员', defaultRadius: 3000 },
  { key: 'satellite', label: '查询历史火情', icon: '🔥', typeName: '历史火情', defaultRadius: 5000 },
  { key: 'custom', label: '自定义查询...', icon: '🔍', typeName: '自定义', defaultRadius: 5000 },
];

// 地图可视范围（同时作为无人机目的地坐标输入的合法区间）
const MAP_BOUNDS_LAT: [number, number] = [15.68, 53.56];
const MAP_BOUNDS_LNG: [number, number] = [73.5, 135.09];
const MAP_BOUNDS: L.LatLngBoundsExpression = [
  [MAP_BOUNDS_LAT[0], MAP_BOUNDS_LNG[0]],
  [MAP_BOUNDS_LAT[1], MAP_BOUNDS_LNG[1]]
];

// 超时和延迟常量
const TIMEOUT_DELAY_MS = 300;
const INIT_TOAST_DELAY_MS = 1500;
const MAP_INVALIDATE_DELAY_MS = 100;
const POPUP_OPEN_DELAY_MS = 300;
const ZOOM_THRESHOLD = 15; // 大于此值显示散开视图，小于等于此值显示聚合视图

// ============ Refs ============
const wrapper = ref<HTMLElement | null>(null);
const mapContainer = ref<HTMLElement | null>(null);
const h5playerContainer = ref<HTMLElement | null>(null);

// 查询中心点（由 skill 通过 map config 传入）
const queryCenter = ref<{ lng: number; lat: number; radius: number }>({ lng: 108.689005, lat: 33.972476, radius: 5000 });
const dataCount = ref(0);

// 全屏
const isFullScreen = ref(false);

// 提示
const showInitToast = ref(false);
const initToastMessage = ref('');

// 加载状态
const isLoading = ref(false);
const loadingMessage = ref('加载摄像头数据...');

const entityType = ref<string>('camera');

// 视频播放
const videoModalVisible = ref(false);
const currentCameraName = ref('');
const videoLoading = ref(false);
let h5player: any = null;
let h5playerScriptPromise: Promise<void> | null = null;

// 错误
const error = ref<string | null>(null);
const isErrorExpanded = ref(false);

// 右键菜单 & 查询对话框
const chatStore = useChatStore();
const contextMenuVisible = ref(false);
const contextMenuPos = ref({ x: 0, y: 0 });
const contextMenuLatLng = ref<{ lng: number; lat: number } | null>(null);
const queryDialogVisible = ref(false);
const queryType = ref('');
const queryRadius = ref(3000);
const queryPrompt = ref('');
const queryMenuOptions = QUERY_TYPES;
const selectedQueryType = computed(() => QUERY_TYPES.find(q => q.key === queryType.value) || null);

// ============ Map State ============
let map: L.Map | null = null;
let cameraLayer: L.FeatureGroup | null = null;
let bufferLayer: L.LayerGroup | null = null;
let cameraClusterLayer: L.FeatureGroup | null = null; // 聚合视图（缩小时显示）
let cameraSpreadLayer: L.FeatureGroup | null = null;  // 散开视图（放大时显示）
let villageLayer: L.LayerGroup | null = null;          // 村庄图层
let districtLayer: L.LayerGroup | null = null;          // 区县图层
let dispatchLayer: L.LayerGroup | null = null;         // 调度图层（动画路径 + 被调度实体 marker）
let firePoint: { lng: number; lat: number } | null = null; // 火情报警位置（网格员调度目的地）
const uavPickMode = ref(false);                        // 无人机飞行目的地设置面板是否开启
const uavPickTab = ref<'map' | 'coord'>('map');        // 目的地录入方式：地图点选 / 输入坐标
const uavCoordLng = ref('');                           // 手动输入的目的地经度（字符串以区分未填写）
const uavCoordLat = ref('');                           // 手动输入的目的地纬度
const uavCoordError = ref('');                         // 坐标校验错误提示
let pendingDispatchUav: { marker: L.Marker; info: Record<string, any> } | null = null;
let pickTargetMarker: L.Marker | null = null;           // 选点确认标记
const activeTrailCancels = new Set<() => void>();       // 进行中的轨迹动画取消器
const dispatchingMarkers = new Set<L.Marker>();         // 正在执行调度任务的实体（防重复调度）

// 调度动画参数（航线采样段数 / 动画时长 / 航线弯曲度）
const DISPATCH_TRAIL_SEGMENTS = 90;
const UAV_ANIM_DURATION_MS = 18000;
const MEMBER_ANIM_DURATION_MS = 40000;
// 弯曲系数：侧向最大偏移占起终点直线距离的比例（0 为纯直线，取值过大即变成绕行）
const UAV_TRAIL_BOW = 0.08;
const MEMBER_TRAIL_BOW = 0.15;
let resizeObserver: ResizeObserver | null = null;

// 组件卸载标志
let isUnmounted = false;

// ============ Helper Functions ============
function showNotification(msg: string, type: 'success' | 'error' | 'warning' | 'info' = 'info') {
  const colors = { success: '#28a745', error: '#dc3545', warning: '#ffc107', info: '#fa8c16' };
  const div = document.createElement('div');
  div.style.cssText = `
    position: fixed;
    top: 20px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 9999;
    padding: 10px 20px;
    border-radius: 8px;
    color: white;
    font-size: 14px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    background: ${colors[type]};
    transition: opacity 0.3s;
    max-width: 90%;
    text-align: center;
  `;
  div.textContent = msg;
  document.body.appendChild(div);
  setTimeout(() => {
    div.style.opacity = '0';
    setTimeout(() => div.remove(), 300);
  }, 3000);
}

function getPublicAssetUrl(path: string): string {
  const base = (((import.meta as any)?.env?.BASE_URL) || '/').replace(/\/?$/, '/');
  return `${base}${path.replace(/^\/+/, '')}`;
}

function ensureH5PlayerScript(): Promise<void> {
  if (typeof window === 'undefined' || typeof (window as any).JSPlugin !== 'undefined') {
    return Promise.resolve(undefined);
  }
  if (h5playerScriptPromise) {
    return h5playerScriptPromise;
  }

  h5playerScriptPromise = new Promise<void>((resolve, reject) => {
    const scriptId = 'camera-canvas-h5player-script';
    const existingScript = document.getElementById(scriptId) as HTMLScriptElement | null;
    if (existingScript) {
      existingScript.addEventListener('load', () => resolve(), { once: true });
      existingScript.addEventListener('error', () => reject(new Error('加载 h5player 脚本失败')), { once: true });
      return;
    }

    const script = document.createElement('script');
    script.id = scriptId;
    script.src = getPublicAssetUrl('resource/h5player.min.js');
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('加载 h5player 脚本失败'));
    document.body.appendChild(script);
  }).catch((error) => {
    h5playerScriptPromise = null;
    throw error;
  });

  return h5playerScriptPromise ?? Promise.resolve(undefined);
}

// 从 SuperMap 响应中提取 features
function extractFeatures(data: any): any[] | null {
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

// 从 feature 属性中提取 cascadeCode
function extractCascadeCode(info: Record<string, any>): string {
  return info.CASCADE_CODE
    || info.cameraIndexCode
    || info.CAMERA_INDEX_CODE
    || info.indexCode
    || info.INDEX_CODE
    || info.cascade_code
    || info.cascadeCode
    || info.id
    || info.SmID
    || '';
}

// ============ Map Initialization ============
function initMap() {
  if (!mapContainer.value || map) return;

  map = L.map(mapContainer.value, {
    crs: L.CRS.EPSG4326,
    center: DEFAULT_CENTER,
    maxZoom: 18,
    zoom: DEFAULT_ZOOM,
    zoomControl: false,
    attributionControl: false,
  });

  map.setMaxBounds(MAP_BOUNDS);

  const LSuperMap = (L as any).supermap;
  if (LSuperMap && typeof LSuperMap.tiledMapLayer === 'function') {
    try {
      LSuperMap.tiledMapLayer(SUPERMAP_MAP_URL, { prjCoordSys: { epsgCode: 4490 } }).addTo(map);
      LSuperMap.tiledMapLayer(SUPERMAP_CHINA_MAP_URL, { prjCoordSys: { epsgCode: 4490 } }).addTo(map);
      LSuperMap.tiledMapLayer(SUPERMAP_BOUNDARY_MAP_URL, { prjCoordSys: { epsgCode: 4490 } }).addTo(map);
      LSuperMap.tiledMapLayer(SUPERMAP_SHANXI_MAP_URL, { prjCoordSys: { epsgCode: 4490 } }).addTo(map);
    } catch (e) {
      addFallbackTileLayer();
    }
  } else {
    addFallbackTileLayer();
  }

  cameraLayer = L.featureGroup().addTo(map);
  bufferLayer = L.layerGroup().addTo(map);

  L.control.scale({ position: 'bottomleft', metric: true, imperial: false }).addTo(map);

  // 初始化区县 + 村庄行政图层
  initAdminLayers();

  // 注册右键菜单事件
  map.on('contextmenu', openContextMenu);
  // 注册地图点击事件（无人机目的地选点）
  map.on('click', onMapClick);

  setTimeout(() => map?.invalidateSize(), 100);
}

function addFallbackTileLayer() {
  if (!map) return;
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 18 }).addTo(map);
}

// ============ Admin Layers (区县 + 村庄) ============

// 将 SuperMap 数据服务返回的几何格式转换为 GeoJSON
function supermapGeomToGeoJSON(geom: any): any | null {
  if (!geom) return null;

  const geomType = (geom.type || geom.geometryType || '').toUpperCase();

  // ── 辅助：闭合一个环（首尾点不同时自动闭合） ──
  function closeRing(ring: number[][]): number[][] {
    if (ring.length > 0) {
      const first = ring[0];
      const last = ring[ring.length - 1];
      if (first[0] !== last[0] || first[1] !== last[1]) {
        ring.push([first[0], first[1]]);
      }
    }
    return ring;
  }

  // ── 辅助：根据 parts(数字数组) + points(扁平点数组) 拆分出多个环 ──
  // SuperMap iServer 实际格式: parts = [3875, 1200], points = [{x,y}, {x,y}, ...]
  function splitFlatPointsIntoRings(parts: number[], points: any[]): number[][][] {
    const rings: number[][][] = [];
    let offset = 0;
    for (const count of parts) {
      if (typeof count !== 'number' || count <= 0) continue;
      const ring: number[][] = [];
      for (let i = offset; i < offset + count && i < points.length; i++) {
        const p = points[i];
        if (p && p.x != null && p.y != null) {
          ring.push([p.x, p.y]);
        }
      }
      if (ring.length > 0) {
        rings.push(closeRing(ring));
      }
      offset += count;
    }
    return rings;
  }

  // ── 辅助：从嵌套 parts 对象数组中提取环 (parts[].points 格式) ──
  function extractRingsFromNestedParts(parts: any[]): number[][][] {
    const rings: number[][][] = [];
    for (const part of parts) {
      if (part && Array.isArray(part.points) && part.points.length > 0) {
        const ring = part.points.map((p: any) => [p.x, p.y]);
        rings.push(closeRing(ring));
      }
    }
    return rings;
  }

  // ── 辅助：从 partPoints 嵌套数组中提取环 ──
  function extractRingsFromPartPoints(partPoints: any[][]): number[][][] {
    const rings: number[][][] = [];
    for (const part of partPoints) {
      if (Array.isArray(part) && part.length > 0) {
        const ring = part.map((p: any) => [p.x, p.y]);
        rings.push(closeRing(ring));
      }
    }
    return rings;
  }

  // ── 辅助：根据类型决定返回 Polygon 还是 LineString ──
  function makePolygonOrLine(rings: number[][][]): any {
    if (rings.length === 0) return null;
    if (geomType === 'LINE' || geomType === 'POLYLINE') {
      return rings.length === 1
        ? { type: 'LineString', coordinates: rings[0] }
        : { type: 'MultiLineString', coordinates: rings };
    }
    // REGION / 默认 → Polygon
    if (rings.length === 1) {
      return { type: 'Polygon', coordinates: rings };
    }
    // 多环：检查 partTopo 判断是否为 MultiPolygon
    // partTopo[i] === 1 表示外环，其他值表示内环（孔洞）
    if (geom.partTopo && Array.isArray(geom.partTopo)) {
      const polygons: number[][][][] = [];
      let currentPoly: number[][][] = [];
      for (let i = 0; i < rings.length; i++) {
        if (geom.partTopo[i] === 1 && currentPoly.length > 0) {
          polygons.push(currentPoly);
          currentPoly = [];
        }
        currentPoly.push(rings[i]);
      }
      if (currentPoly.length > 0) polygons.push(currentPoly);
      if (polygons.length === 1) {
        return { type: 'Polygon', coordinates: polygons[0] };
      }
      return { type: 'MultiPolygon', coordinates: polygons };
    }
    // 无 partTopo → 全部作为单个 Polygon 的环
    return { type: 'Polygon', coordinates: rings };
  }

  // ══════════════════════════════════════════
  // 格式匹配（按优先级排列）
  // ══════════════════════════════════════════

  // ── 1. GeoJSON 原生格式 ──
  if (geom.type && geom.coordinates) {
    return { type: geom.type, coordinates: geom.coordinates };
  }

  // ── 2. SuperMap iServer 标准格式: parts(数字[]) + points(扁平点[]) ──
  // 这是实际 SuperMap iServer 返回的最常见格式
  if (Array.isArray(geom.parts) && geom.parts.length > 0
    && Array.isArray(geom.points) && geom.points.length > 0
    && typeof geom.parts[0] === 'number') {
    const rings = splitFlatPointsIntoRings(geom.parts, geom.points);
    const result = makePolygonOrLine(rings);
    if (result) return result;
  }

  // ── 3. 嵌套 parts 对象格式: parts[].points (某些 SuperMap 版本) ──
  if (Array.isArray(geom.parts) && geom.parts.length > 0
    && geom.parts[0] && typeof geom.parts[0] === 'object' && geom.parts[0].points) {
    const rings = extractRingsFromNestedParts(geom.parts);
    if (rings.length > 0) {
      const result = makePolygonOrLine(rings);
      if (result) return result;
    }
  }

  // ── 4. partPoints 嵌套数组格式 ──
  if (geom.partPoints && Array.isArray(geom.partPoints) && geom.partPoints.length > 0) {
    if (Array.isArray(geom.partPoints[0])) {
      const rings = extractRingsFromPartPoints(geom.partPoints);
      if (rings.length > 0) {
        const result = makePolygonOrLine(rings);
        if (result) return result;
      }
    } else if (geom.partPoints[0]?.x != null) {
      // 扁平点数组
      const coords = geom.partPoints.map((p: any) => [p.x, p.y]);
      if (coords.length === 1) {
        return { type: 'Point', coordinates: coords[0] };
      }
      return { type: 'Polygon', coordinates: [closeRing(coords)] };
    }
  }

  // ── 5. 只有 points 数组（无 parts） ──
  if (Array.isArray(geom.points) && geom.points.length > 0 && geom.points[0]?.x != null) {
    if (geom.points.length === 1) {
      return { type: 'Point', coordinates: [geom.points[0].x, geom.points[0].y] };
    }
    const coords = geom.points.map((p: any) => [p.x, p.y]);
    return { type: 'Polygon', coordinates: [closeRing(coords)] };
  }

  // ── 6. 单点格式 ──
  if (geom.centerPoint && geom.centerPoint.x != null) {
    return { type: 'Point', coordinates: [geom.centerPoint.x, geom.centerPoint.y] };
  }
  if (geom.center && geom.center.x != null) {
    return { type: 'Point', coordinates: [geom.center.x, geom.center.y] };
  }
  if (geom.x != null && geom.y != null) {
    return { type: 'Point', coordinates: [geom.x, geom.y] };
  }

  console.warn('[CameraCanvasUI] 无法转换 SuperMap 几何格式:', Object.keys(geom), 'type:', geomType);
  return null;
}

// 空间查询 SuperMap 数据服务，返回 GeoJSON features
// SuperMap 数据服务 featureResults 端点（正确的查询入口）
const SUPERMAP_FEATURE_RESULTS_URL = `${MAP_DATA_BASE_URL}/featureResults.json?returnContent=true`;

async function querySupermapSpatial(baseUrl: string, bounds: L.LatLngBounds): Promise<any[]> {
  const sw = bounds.getSouthWest();
  const ne = bounds.getNorthEast();

  // 从 URL 提取 datasource:dataset 格式
  const dsMatch = baseUrl.match(/\/datasources\/([^/]+)\/datasets\/([^/]+)/);
  const datasetName = dsMatch ? `${dsMatch[1]}:${dsMatch[2]}` : baseUrl.split('/').pop() || '';

  const requestBody = {
    getFeatureMode: 'BOUNDS',
    datasetNames: [datasetName],
    bounds: {
      leftBottom: { x: sw.lng, y: sw.lat },
      rightTop: { x: ne.lng, y: ne.lat }
    },
    hasGeometry: true,
    maxFeatures: 500
  };

  try {
    const res = await fetch(SUPERMAP_FEATURE_RESULTS_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json; charset=utf-8' },
      body: JSON.stringify(requestBody)
    });
    const data = await res.json();

    if (data?.succeed === false || data?.error) {
      console.error(`[CameraCanvasUI] SuperMap 查询失败 (${datasetName}):`, data?.error);
      return [];
    }

    const features = extractFeatures(data);
    if (!features) return [];

    return features.map((f: any) => {
      const geojson = supermapGeomToGeoJSON(f.geometry);
      if (!geojson) return null;

      // 从 fieldNames/fieldValues 构建属性对象
      const props: Record<string, any> = {};
      if (f.fieldNames && f.fieldValues) {
        f.fieldNames.forEach((name: string, idx: number) => {
          props[name] = f.fieldValues[idx];
        });
      }

      return { type: 'Feature', geometry: geojson, properties: props };
    }).filter(Boolean);
  } catch (e) {
    console.error(`[CameraCanvasUI] 查询数据服务失败 (${datasetName}):`, e);
    return [];
  }
}

// 提取 feature 的名称（尝试多种常见字段名，兜底取第一个非空字符串字段）
function extractAdminName(props: Record<string, any>): string {
  const excludeFields = ['SmID', 'SmGeometrySize', 'SmUserID', 'geometry', 'geometryType', 'geometryID', 'ADCODE', 'adcode', 'CODE', 'code'];
  // 优先尝试常见名称字段
  const nameFields = [
    'NAME', 'name', 'Name', 'DNAME', 'dname',
    // BZMC = 标准名称（区县=区县名, 村庄=村庄名）优先于 QXMC = 区县名称（村庄中是父级区县名）
    'BZMC', 'bzmc', 'QXMC', 'qxmc',
    '名称', '村庄名称', '区县名称', '行政区划名称', '地名',
    'XZQHMC', 'TOWN', 'VNAME', 'vname', 'CNAME', 'cname',
    '乡镇名称', '街道名称', '乡镇', '街道',
  ];
  for (const field of nameFields) {
    if (props[field] && typeof props[field] === 'string' && props[field].trim()) {
      return props[field].trim();
    }
  }
  // 兜底：取第一个非空、非数字的字符串字段作为名称
  for (const [key, value] of Object.entries(props)) {
    if (excludeFields.includes(key)) continue;
    if (typeof value === 'string' && value.trim() && isNaN(Number(value)) && value.trim().length <= 30) {
      return value.trim();
    }
  }
  return '';
}

// 初始化并加载区县 + 村庄图层
function initAdminLayers() {
  if (!map) return;

  villageLayer = L.layerGroup();
  districtLayer = L.layerGroup();

  // 默认添加到地图
  villageLayer.addTo(map);
  districtLayer.addTo(map);

  loadAdminLayers();

  // 地图移动/缩放结束后重新加载（防抖）
  let adminReloadTimer: ReturnType<typeof setTimeout> | null = null;
  const scheduleAdminReload = () => {
    if (adminReloadTimer) clearTimeout(adminReloadTimer);
    adminReloadTimer = setTimeout(() => loadAdminLayers(), 600);
  };
  map.on('moveend', scheduleAdminReload);
  // zoomend 不再重载行政图层（moveend 已覆盖缩放后的位置变化，减少不必要的网络请求）
}

// 加载区县和村庄数据并渲染
async function loadAdminLayers() {
  if (!map || !villageLayer || !districtLayer) return;

  const bounds = map.getBounds();
  const zoom = map.getZoom();

  villageLayer.clearLayers();
  districtLayer.clearLayers();

  // 区县：zoom >= 9 时显示
  if (zoom >= 9) {
    const districtFeatures = await querySupermapSpatial(DISTRICT_DATA_URL, bounds);
    const districtGeoJSON: any = { type: 'FeatureCollection', features: districtFeatures };

    if (districtFeatures.length > 0) {
      // 调试：打印第一个 feature 的字段名和名称提取结果
      if (districtFeatures[0]?.properties) {
        const fields = Object.keys(districtFeatures[0].properties);
        const extractedName = extractAdminName(districtFeatures[0].properties);
        console.log('[CameraCanvasUI] 区县数据字段:', fields, '| 提取名称:', `"${extractedName}"`, `| 共 ${districtFeatures.length} 个`);
      }

      L.geoJSON(districtGeoJSON, {
        style: () => ({
          color: '#e74c3c',
          weight: 2.5,
          opacity: 0.8,
          fillColor: '#e74c3c',
          fillOpacity: 0.05,
          dashArray: '6, 3',
        }),
        onEachFeature: (feature: any, layer: any) => {
          const name = extractAdminName(feature.properties || {});
          if (name) {
            // 计算多边形中心点用于放置标签
            const center = layer.getBounds ? layer.getBounds().getCenter() : null;
            if (center) {
              L.marker([center.lat, center.lng], {
                icon: L.divIcon({
                  className: 'district-label',
                  html: `<div style="
                    color: #c0392b;
                    font-size: 16px;
                    font-weight: bold;
                    text-shadow: 0 0 4px #fff, 0 0 4px #fff, 0 0 4px #fff, 1px 1px 2px #fff, -1px -1px 2px #fff, 1px -1px 2px #fff, -1px 1px 2px #fff;
                    white-space: nowrap;
                    text-align: center;
                    pointer-events: none;
                    letter-spacing: 2px;
                  ">${name}</div>`,
                  iconSize: [160, 28],
                  iconAnchor: [80, 14]
                }),
                interactive: false,
                zIndexOffset: -100
              }).addTo(districtLayer!);
            }

            // 弹窗显示区县信息
            if (layer.bindPopup) {
              const excludeFields = ['SmID', 'SmGeometrySize', 'SmUserID', 'geometry', 'geometryType', 'geometryID'];
              let popupHtml = `<div style="min-width:160px; font-size:13px; color:#333;">`;
              popupHtml += `<h5 style="margin:0 0 6px; color:#e74c3c; border-bottom:1px solid #eee; padding-bottom:4px;">🏛️ ${name}</h5>`;
              for (const [k, v] of Object.entries(feature.properties)) {
                if (excludeFields.includes(k) || !v) continue;
                popupHtml += `<div style="margin-bottom:3px;"><b style="color:#555;">${k}:</b> ${v}</div>`;
              }
              popupHtml += `</div>`;
              layer.bindPopup(popupHtml, { className: 'custom-camera-popup' });
            }
          }
        }
      }).addTo(districtLayer!);
    } else {
      console.log('[CameraCanvasUI] 区县数据为空 (zoom=' + zoom + ', bounds=' + JSON.stringify({ sw: bounds.getSouthWest(), ne: bounds.getNorthEast() }) + ')');
    }
  }

  // 村庄：zoom >= 12 时显示
  if (zoom >= 12) {
    const villageFeatures = await querySupermapSpatial(VILLAGE_DATA_URL, bounds);
    const villageGeoJSON: any = { type: 'FeatureCollection', features: villageFeatures };

    if (villageFeatures.length > 0) {
      // 调试：打印第一个 feature 的字段名和名称提取结果
      if (villageFeatures[0]?.properties) {
        const fields = Object.keys(villageFeatures[0].properties);
        const extractedName = extractAdminName(villageFeatures[0].properties);
        console.log('[CameraCanvasUI] 村庄数据字段:', fields, '| 提取名称:', `"${extractedName}"`, `| 共 ${villageFeatures.length} 个`);
      }

      L.geoJSON(villageGeoJSON, {
        style: () => ({
          color: '#2980b9',
          weight: 1.5,
          opacity: 0.7,
          fillColor: '#3498db',
          fillOpacity: 0.08,
        }),
        onEachFeature: (feature: any, layer: any) => {
          const name = extractAdminName(feature.properties || {});
          if (name) {
            const center = layer.getBounds ? layer.getBounds().getCenter() : null;
            if (center) {
              L.marker([center.lat, center.lng], {
                icon: L.divIcon({
                  className: 'village-label',
                  html: `<div style="
                    color: #2471a3;
                    font-size: 13px;
                    font-weight: 600;
                    text-shadow: 0 0 4px #fff, 0 0 4px #fff, 0 0 4px #fff, 1px 1px 2px #fff, -1px -1px 2px #fff, 1px -1px 2px #fff, -1px 1px 2px #fff;
                    white-space: nowrap;
                    text-align: center;
                    pointer-events: none;
                    letter-spacing: 1px;
                  ">🏘️ ${name}</div>`,
                  iconSize: [140, 24],
                  iconAnchor: [70, 12]
                }),
                interactive: false,
                zIndexOffset: -200
              }).addTo(villageLayer!);
            }

            // 弹窗显示村庄信息
            if (layer.bindPopup) {
              const excludeFields = ['SmID', 'SmGeometrySize', 'SmUserID', 'geometry', 'geometryType', 'geometryID'];
              let popupHtml = `<div style="min-width:150px; font-size:13px; color:#333;">`;
              popupHtml += `<h5 style="margin:0 0 6px; color:#2980b9; border-bottom:1px solid #eee; padding-bottom:4px;">🏘️ ${name}</h5>`;
              for (const [k, v] of Object.entries(feature.properties)) {
                if (excludeFields.includes(k) || !v) continue;
                popupHtml += `<div style="margin-bottom:3px;"><b style="color:#555;">${k}:</b> ${v}</div>`;
              }
              popupHtml += `</div>`;
              layer.bindPopup(popupHtml, { className: 'custom-camera-popup' });
            }
          }
        }
      }).addTo(villageLayer!);
    } else {
      console.log('[CameraCanvasUI] 村庄数据为空 (zoom=' + zoom + ')');
    }
  }

  console.log(`[CameraCanvasUI] 行政图层加载完成 (zoom=${zoom}, 区县=${districtLayer?.getLayers().length || 0}层, 村庄=${villageLayer?.getLayers().length || 0}层)`);
}

// ============ Entity Query (摄像头/无人机/网格员) ============

async function executeEntityQuery(lng: number, lat: number, radius: number, type?: string, append = false) {
  if (!map) return;

  const typeStr = type || entityType.value || 'camera';
  if (!append) entityType.value = typeStr;
  const typeCfg = getEntityTypeConfig(typeStr);
  const queryCfg = ENTITY_QUERY_CONFIG[typeStr];

  if (!queryCfg) {
    showNotification(`不支持的查询类型: ${typeStr}`, 'error');
    return;
  }

  // 重置已渲染签名，确保手动查询后 renderFromConfig 不会跳过
  lastRenderedSignature = '';

  if (append) {
    // 追加模式（右键连续查询）：保留已有查询结果，仅叠加本次范围圈与中心点（无结果也不白屏）
    L.circle([lat, lng], {
      radius: radius,
      color: typeCfg.color,
      fillColor: typeCfg.color,
      fillOpacity: 0.15,
      weight: 2,
      dashArray: '8, 4'
    }).addTo(bufferLayer!);
    addQueryPointMarker(lat, lng);
  } else {
    // 清除之前的图层（含进行中的调度动画）
    cancelAllTrailAnimations();
    if (cameraLayer) cameraLayer.clearLayers();
    if (bufferLayer) bufferLayer.clearLayers();
  }

  // 近似将米转为度
  const degrees = radius / 111319.49;

  const requestBody = {
    getFeatureMode: 'BUFFER',
    datasetNames: [queryCfg.datasetName],
    geometry: {
      type: 'POINT',
      points: [{ x: lng, y: lat }]
    },
    bufferDistance: degrees,
    hasGeometry: true,
    maxFeatures: 1000
  };

  try {
    isLoading.value = true;
    loadingMessage.value = `正在查询${typeCfg.label}数据...`;

    const res = await fetch(queryCfg.url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json; charset=utf-8' },
      body: JSON.stringify(requestBody)
    });
    const data = await res.json();

    if (isUnmounted) return;

    // 检查 SuperMap 错误
    if (data?.succeed === false || data?.error) {
      console.error(`[CameraCanvasUI] SuperMap 查询失败 (${typeStr}):`, data?.error);
      showNotification(`查询${typeCfg.label}失败: ${data?.error?.errorMsg || '服务异常'}`, 'error');
      isLoading.value = false;
      return;
    }

    const features = extractFeatures(data);

    // 调试日志
    if (features && features.length > 0) {
      const nameIdx = data?.features?.[0]?.fieldNames?.indexOf(queryCfg.nameField) ?? -1;
      console.log(`[CameraCanvasUI] ${typeCfg.label}查询返回 ${features.length} 个 feature:`);
      features.forEach((f: any, idx: number) => {
        const geom = f.geometry;
        const name = nameIdx >= 0 ? f.fieldValues?.[nameIdx] : `feature[${idx}]`;
        console.log(`  [${idx}] "${name}" geom:`, geom?.type, 'keys:', geom ? Object.keys(geom) : 'null');
      });
    }

    if (!features || features.length === 0) {
      showNotification(`在 (${lng.toFixed(4)}, ${lat.toFixed(4)}) 附近 ${radius}m 内未找到${typeCfg.label}`, 'warning');
      isLoading.value = false;
      return;
    }

    if (!append) {
      // 绘制查询范围缓冲区（颜色跟随实体类型；追加模式已在查询前绘制）
      L.circle([lat, lng], {
        radius: radius,
        color: typeCfg.color,
        fillColor: typeCfg.color,
        fillOpacity: 0.15,
        weight: 2,
        dashArray: '8, 4'
      }).addTo(bufferLayer!);

      // 绘制查询中心点标记
      addQueryPointMarker(lat, lng);
    }

    dataCount.value = features.length;
    renderCameraFeatures(features, lng, lat, radius, typeStr, append);

    // 调整视图以显示所有标记（自动适配边界）
    if (cameraLayer && cameraLayer.getLayers().length > 0) {
      const bounds = cameraLayer.getBounds();
      bounds.extend([lat, lng]);
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 15 });
    } else {
      map.setView([lat, lng], 14);
    }

    showNotification(`查询成功，共找到 ${features.length} 个${typeCfg.label}`, 'success');

    // 记录已渲染签名，防止后续 renderFromConfig 收到 AI 响应后重复清空 bufferLayer（圆圈和中心点）
    lastRenderedSignature = `${typeStr}:${features.length}`;
    // 记录本次本地查询的参数签名，用于匹配 AI 响应是否为同一查询
    lastLocalQuerySignature = `${lng},${lat},${radius},${typeStr}`;

    // 视图动画结束后主动刷新行政图层
    setTimeout(() => loadAdminLayers(), 800);
  } catch (err: any) {
    if (!isUnmounted) {
      console.error(`查询${typeCfg.label}失败:`, err);
      showNotification(`查询失败: ${err?.message || '请求异常'}`, 'error');
    }
  } finally {
    if (!isUnmounted) {
      isLoading.value = false;
    }
  }
}

// Issue 4: 在查询中心点添加醒目标记
function addQueryPointMarker(lat: number, lng: number) {
  if (!bufferLayer) return;

  const queryPointIcon = L.divIcon({
    className: 'query-point-marker',
    html: `<div style="
      position: relative;
      width: 28px; height: 28px;
    ">
      <div style="
        position: absolute; inset: 0;
        background: rgba(250, 140, 22, 0.25);
        border-radius: 50%;
        animation: query-point-pulse 2s ease-in-out infinite;
      "></div>
      <div style="
        position: absolute; top: 6px; left: 6px;
        width: 16px; height: 16px;
        background: #fa8c16;
        border: 3px solid #fff;
        border-radius: 50%;
        box-shadow: 0 2px 8px rgba(0,0,0,0.4);
      "></div>
    </div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14]
  });

  L.marker([lat, lng], { icon: queryPointIcon, zIndexOffset: 1000 })
    .bindPopup(`<div style="font-size:13px;"><b>📍 查询中心点</b><br>经度: ${lng}<br>纬度: ${lat}</div>`, { className: 'query-point-popup' })
    .addTo(bufferLayer!);
}

// ============ 右键菜单 & 查询对话框 ============

function openContextMenu(e: L.LeafletMouseEvent) {
  if (!map || !mapContainer.value) return;
  L.DomEvent.stopPropagation(e);

  const containerPoint = e.containerPoint;
  const containerRect = mapContainer.value.getBoundingClientRect();

  // 确保菜单不超出容器边界
  let x = containerPoint.x;
  let y = containerPoint.y;
  const menuWidth = 240;
  const menuHeight = 260;
  if (x + menuWidth > containerRect.width) x = containerRect.width - menuWidth - 8;
  if (y + menuHeight > containerRect.height) y = containerRect.height - menuHeight - 8;
  if (x < 0) x = 8;
  if (y < 0) y = 8;

  contextMenuPos.value = { x, y };
  // 地图选点默认使用当前搜索中心点经纬度，使查询围绕已有结果区域展开
  contextMenuLatLng.value = { lng: queryCenter.value.lng, lat: queryCenter.value.lat };
  contextMenuVisible.value = true;
}

function closeContextMenu() {
  contextMenuVisible.value = false;
}

function selectQueryOption(key: string) {
  closeContextMenu();
  const opt = QUERY_TYPES.find(q => q.key === key);
  if (!opt) return;

  queryType.value = key;
  queryRadius.value = opt.defaultRadius;
  queryPrompt.value = '';
  queryDialogVisible.value = true;
}

function closeQueryDialog() {
  queryDialogVisible.value = false;
}

async function confirmQuery() {
  if (!contextMenuLatLng.value) return;

  const opt = selectedQueryType.value;
  if (!opt) return;

  const { lng, lat } = contextMenuLatLng.value;
  const radius = queryRadius.value;
  const prompt = queryPrompt.value.trim();

  // 关闭对话框
  closeQueryDialog();

  // camera/uav/member/satellite 类型：先做客户端本地查询（在地图上显示），同时发送给 AI 处理
  if (ENTITY_QUERY_CONFIG[opt.key]) {
    console.log(`[CameraCanvasUI] 本地查询 + 发送AI: ${opt.typeName} (${lng}, ${lat}), radius=${radius}m`);
    executeEntityQuery(lng, lat, radius, opt.key, true);
  }

  // 所有类型均发送给 AI 处理（确保用户发起的查询始终触发 AI 响应）
  let message = `请查询坐标 (经度: ${lng.toFixed(6)}, 纬度: ${lat.toFixed(6)}) 附近 ${radius}m 范围内的${opt.typeName}数据。`;
  if (prompt) {
    message += `\n用户补充: ${prompt}`;
  }

  try {
    await chatStore.sendMessage(message);
    console.log(`[CameraCanvasUI] 已发送查询消息: ${message}`);
  } catch (err) {
    console.error('[CameraCanvasUI] 发送查询消息失败:', err);
    showNotification('发送查询失败，请重试', 'error');
  }
}

// 从 feature 的 geometry 中提取经纬度，兼容多种 SuperMap 返回格式
function extractGeometryXY(feature: any): { x: number; y: number } | null {
  const geom = feature.geometry;

  // 尝试从 geometry 提取
  if (geom) {
    // 格式1: { points: [{ x, y }] }
    if (geom.points && geom.points.length > 0) {
      const p = geom.points[0];
      if (p.x != null && p.y != null) return { x: p.x, y: p.y };
    }
    // 格式2: { partPoints: [[{ x, y }]] } — SuperMap iServer 常见 POINT 格式
    if (geom.partPoints && Array.isArray(geom.partPoints) && geom.partPoints.length > 0) {
      const firstPart = geom.partPoints[0];
      if (Array.isArray(firstPart) && firstPart.length > 0) {
        const p = firstPart[0];
        if (p.x != null && p.y != null) return { x: p.x, y: p.y };
      }
    }
    // 格式3: { point: { x, y } } (singular)
    if (geom.point && geom.point.x != null && geom.point.y != null) {
      return { x: geom.point.x, y: geom.point.y };
    }
    // 格式4: { x, y } 直接在 geometry 上
    if (geom.x != null && geom.y != null) {
      return { x: geom.x, y: geom.y };
    }
    // 格式5: { center: { x, y } }
    if (geom.center && geom.center.x != null && geom.center.y != null) {
      return { x: geom.center.x, y: geom.center.y };
    }
    // 格式6: GeoJSON { type: "Point", coordinates: [x, y] }
    if (geom.coordinates && Array.isArray(geom.coordinates) && geom.coordinates.length >= 2) {
      return { x: geom.coordinates[0], y: geom.coordinates[1] };
    }
    // 格式7: { centerPoint: { x, y } }
    if (geom.centerPoint && geom.centerPoint.x != null && geom.centerPoint.y != null) {
      return { x: geom.centerPoint.x, y: geom.centerPoint.y };
    }
  }

  // 回退：尝试从 feature 本身提取坐标（某些 SuperMap 响应格式）
  if (feature.x != null && feature.y != null) {
    return { x: feature.x, y: feature.y };
  }
  if (feature.lon != null && feature.lat != null) {
    return { x: Number(feature.lon), y: Number(feature.lat) };
  }
  if (feature.lng != null && feature.lat != null) {
    return { x: Number(feature.lng), y: Number(feature.lat) };
  }

  console.warn('[CameraCanvasUI] extractGeometryXY 无法识别的几何格式, geometry keys:',
    geom ? Object.keys(geom) : 'null',
    ', feature keys:', Object.keys(feature).slice(0, 15));
  return null;
}

// 实体类型配置（颜色、图标、标签）
const ENTITY_TYPE_CONFIG: Record<string, { color: string; emoji: string; label: string }> = {
  camera: { color: '#fa8c16', emoji: '📹', label: '摄像头' },
  uav:    { color: '#1890ff', emoji: '🚁', label: '无人机' },
  member: { color: '#52c41a', emoji: '👤', label: '网格员' },
  satellite: { color: '#dc2626', emoji: '🔥', label: '历史火情' },
};

function getEntityTypeConfig(type?: string) {
  return ENTITY_TYPE_CONFIG[type || 'camera'] || ENTITY_TYPE_CONFIG.camera;
}

// 摄像头 SVG path
const SVG_PATH_CAMERA = 'M864 248H728l-32.4-90.8a32.07 32.07 0 00-30.2-21.2H358.6c-13.5 0-25.6 8.5-30.1 21.2L296 248H160c-44.2 0-80 35.8-80 80v456c0 44.2 35.8 80 80 80h704c44.2 0 80-35.8 80-80V328c0-44.2-35.8-80-80-80zm8 536c0 4.4-3.6 8-8 8H160c-4.4 0-8-3.6-8-8V328c0-4.4 3.6-8 8-8h186.7l17.1-47.8 22.7-64.2h250.9l22.7 64.2 17.1 47.8H864c4.4 0 8 3.6 8 8v456zM512 384c-88.4 0-160 71.6-160 160s71.6 160 160 160 160-71.6 160-160-71.6-160-160-160zm0 256c-53 0-96-43-96-96s43-96 96-96 96 43 96 96-43 96-96 96z';
// 网格员 SVG path
const SVG_PATH_MEMBER = 'M858.5 763.6a374 374 0 00-80.6-119.5 375.63 375.63 0 00-119.5-80.6c-.4-.2-.8-.3-1.2-.5C719.5 518 760 444.7 760 362c0-137-111-248-248-248S264 225 264 362c0 82.7 40.5 156 102.8 201.1-.4.2-.8.3-1.2.5-44.8 18.9-85 46-119.5 80.6a375.63 375.63 0 00-80.6 119.5A371.7 371.7 0 00136 901.8a8 8 0 008 8.2h60c4.4 0 7.9-3.5 8-7.8 2-77.2 33-149.5 87.8-204.3 56.7-56.7 132-87.9 212.2-87.9s155.5 31.2 212.2 87.9C779.8 752.7 810.8 825 812.8 902.2c.1 4.3 3.6 7.8 8 7.8h60c4.5 0 8.1-3.7 8-8.2a371.7 371.7 0 00-29.5-138.2zM512 534c-45.9 0-89.1-17.9-121.6-50.4S340 407.9 340 362c0-45.9 17.9-89.1 50.4-121.6S466.1 190 512 190s89.1 17.9 121.6 50.4S684 316.1 684 362c0 45.9-17.9 89.1-50.4 121.6S557.9 534 512 534z';

// 通用实体图标（根据类型选择颜色和 SVG）
function createEntityIcon(type?: string): L.DivIcon {
  const cfg = getEntityTypeConfig(type);
  // 无人机使用 PNG 图片图标
  if (type === 'uav') {
    return L.divIcon({
      className: 'custom-camera-icon',
      html: `<div style="width: 28px; height: 28px; display: flex; align-items: center; justify-content: center;">
               <img src="${iconDrone}" style="width: 28px; height: 28px; object-fit: contain; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.4));" />
             </div>`,
      iconSize: [28, 28],
      iconAnchor: [14, 14]
    });
  }
  // 历史火情使用火焰图标
  if (type === 'satellite') {
    return L.divIcon({
      className: 'custom-camera-icon',
      html: `<div style="background: ${cfg.color}; width: 22px; height: 22px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 2px solid #fff; box-shadow: 0 2px 6px rgba(0,0,0,0.4);">
               <span style="font-size: 13px; line-height: 1;">🔥</span>
             </div>`,
      iconSize: [22, 22],
      iconAnchor: [11, 11]
    });
  }
  // 摄像头和网格员使用 SVG 图标
  let svgContent: string;
  if (type === 'member') {
    svgContent = `<svg viewBox="64 64 896 896" width="14px" height="14px" fill="#fff"><path d="${SVG_PATH_MEMBER}"></path></svg>`;
  } else {
    svgContent = `<svg viewBox="64 64 896 896" width="14px" height="14px" fill="#fff"><path d="${SVG_PATH_CAMERA}"></path></svg>`;
  }
  return L.divIcon({
    className: 'custom-camera-icon',
    html: `<div style="background: ${cfg.color}; width: 20px; height: 20px; border-radius: 4px; display: flex; align-items: center; justify-content: center; border: 2px solid #fff; box-shadow: 0 2px 6px rgba(0,0,0,0.4);">
             ${svgContent}
           </div>`,
    iconSize: [20, 20],
    iconAnchor: [10, 10]
  });
}

// 通用聚合图标（带数字角标，缩小视图时使用）
function createClusterIcon(count: number, type?: string): L.DivIcon {
  const cfg = getEntityTypeConfig(type);
  const badgeHtml = `<div style="position:absolute; top:-6px; right:-10px; background:#e74c3c; color:#fff; font-size:11px; font-weight:bold; min-width:18px; height:18px; padding:0 4px; border-radius:9px; display:flex; align-items:center; justify-content:center; border:1.5px solid #fff; box-shadow:0 1px 3px rgba(0,0,0,0.3); line-height:1;">${count}</div>`;

  // 无人机聚合：使用 PNG 图标 + 数字角标
  if (type === 'uav') {
    return L.divIcon({
      className: 'custom-camera-icon',
      html: `<div style="position:relative;">
               <div style="width: 32px; height: 32px; display: flex; align-items: center; justify-content: center;">
                 <img src="${iconDrone}" style="width: 32px; height: 32px; object-fit: contain; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.4));" />
               </div>
               ${badgeHtml}
             </div>`,
      iconSize: [32, 32],
      iconAnchor: [16, 16]
    });
  }

  // 历史火情聚合：火焰图标 + 数字角标
  if (type === 'satellite') {
    return L.divIcon({
      className: 'custom-camera-icon',
      html: `<div style="position:relative;">
               <div style="background: ${cfg.color}; width: 26px; height: 26px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 2px solid #fff; box-shadow: 0 2px 8px rgba(0,0,0,0.4);">
                 <span style="font-size: 15px; line-height: 1;">🔥</span>
               </div>
               ${badgeHtml}
             </div>`,
      iconSize: [26, 26],
      iconAnchor: [13, 13]
    });
  }

  // 摄像头和网格员：使用 SVG 圆形背景 + 数字角标
  let svgContent: string;
  if (type === 'member') {
    svgContent = `<svg viewBox="64 64 896 896" width="12px" height="12px" fill="#fff"><path d="${SVG_PATH_MEMBER}"></path></svg>`;
  } else {
    svgContent = `<svg viewBox="64 64 896 896" width="12px" height="12px" fill="#fff"><path d="${SVG_PATH_CAMERA}"></path></svg>`;
  }
  return L.divIcon({
    className: 'custom-camera-icon',
    html: `<div style="position:relative;">
             <div style="background: ${cfg.color}; width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 2px solid #fff; box-shadow: 0 2px 8px rgba(0,0,0,0.4);">
               ${svgContent}
             </div>
             ${badgeHtml}
           </div>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12]
  });
}

// 将 feature 的原始数据解析为结构化属性
function extractFeatureInfo(feature: any): Record<string, any> {
  const info: Record<string, any> = {};

  // 优先使用 SuperMap 的 fieldNames/fieldValues 格式
  const fieldValues = feature.fieldValues || [];
  const fieldNames = feature.fieldNames || [];
  if (fieldNames.length > 0) {
    fieldNames.forEach((name: string, idx: number) => {
      info[name] = fieldValues[idx];
    });
  } else if (feature.properties && typeof feature.properties === 'object') {
    // 兼容 GeoJSON properties 格式（AI 模型可能在复述时转换格式）
    Object.assign(info, feature.properties);
  }

  info.cascadeCode = extractCascadeCode(info);
  return info;
}

// 提取实体名称（根据类型使用不同字段优先级）
function extractEntityName(info: Record<string, any>, type?: string): string {
  const typeStr = type || 'camera';
  // 按类型优先的名称字段
  const fieldPriority: Record<string, string[]> = {
    camera: ['name', 'NAME', '摄像头名称', 'cascadeCode', 'CASCADE_CODE'],
    uav:    ['DEVICENAME', 'DEPARTNAME', 'name', 'NAME', 'ID'],
    member: ['USERNAME', 'REAL_NAME', 'POSITION', 'name', 'NAME'],
    satellite: ['NAME', 'name', 'FIRE_NAME', 'ADDRESS', 'POSITION', 'LOCATION'],
  };
  const fields = fieldPriority[typeStr] || fieldPriority.camera;
  for (const f of fields) {
    if (info[f] && typeof info[f] === 'string' && info[f].trim()) return info[f].trim();
  }
  // 兜底
  const cfg = getEntityTypeConfig(typeStr);
  return info.cascadeCode || cfg.label;
}

// 弹窗字段白名单：仅展示列出的字段（数组顺序即渲染顺序），其余业务字段与敏感字段一律隐藏
// 未在此配置的类型（摄像头 / 历史火情）仍按 excludeFields 排除法渲染全部字段
const ENTITY_VISIBLE_FIELDS: Record<string, string[]> = {
  uav: ['DEVICENAME', 'DEPARTNAME', 'ORGANIZATION'],
  member: ['USERNAME', 'CHARGE_REGION'],
};

// 为单个实体构建弹窗 HTML
function buildEntityPopup(info: Record<string, any>, type?: string): { html: string; btnId: string } {
  const typeStr = type || 'camera';
  const typeCfg = getEntityTypeConfig(typeStr);
  const btnId = 'btn-play-' + typeStr + '-' + (info.SmID || Math.random().toString(36).substr(2, 9));
  const entityName = extractEntityName(info, typeStr);

  let html = `<div style="min-width:220px; font-size:13px; max-height:400px; overflow-y:auto; color:#333;">`;
  html += `<h5 style="margin:0 0 8px 0; color:${typeCfg.color}; border-bottom:1px solid #eee; padding-bottom:4px;">${typeCfg.emoji} ${entityName}</h5>`;

  // 隐藏的字段（系统字段 + 敏感字段）
  const excludeFields = [
    'SmID', 'SMID', 'SmGeometrySize', 'SmUserID', 'SMUSERID',
    'geometry', 'geometryType', 'geometryID', 'cascadeCode',
    'PASSWORD', 'ENCRYDATA', 'ENTRY', 'DEL_FLAG', 'CREATE_BY', 'UPDATE_BY',
  ];
  // 字段显示名映射（中英对照）
  const fieldLabels: Record<string, string> = {
    DEVICENAME: '设备名称', DEPARTNAME: '所属部门', ORGANIZATION: '组织机构',
    LONGITUDE: '经度', LATITUDE: '纬度', TRACE_CREATETIME: '最后上报时间',
    REAL_NAME: '姓名', USERNAME: '用户名', POSITION: '职位',
    CHARGE_REGION: '负责区域', GRID_NO: '网格编号', GRID_LEVEL: '网格等级',
    PHONENUMBER: '手机号', PHONE: '电话', ONLINE_STATUS: '在线状态',
    LOGIN_TIME: '最后登录', AGE: '年龄', SEX: '性别',
    MEMBER_ID: '成员ID', USER_UNIT: '所属单位',
    name: '名称', NAME: '名称', cascadeCode: '编码',
  };

  // 配置了白名单的类型按白名单固定顺序取字段；其余类型仍按原始字段顺序并排除系统/敏感字段
  const visibleFields = ENTITY_VISIBLE_FIELDS[typeStr];
  const fieldEntries: [string, any][] = visibleFields
    ? visibleFields.map((field) => {
        // SuperMap 字段名为大写，GeoJSON properties 可能为小写，故不区分大小写匹配；标签仍用规范名查表
        const key = Object.keys(info).find((k) => k.toLowerCase() === field.toLowerCase());
        return [field, key ? info[key] : undefined] as [string, any];
      })
    : Object.entries(info).filter(([key]) => !excludeFields.includes(key));

  for (const [key, value] of fieldEntries) {
    if (!value) continue;
    const label = fieldLabels[key] || key;
    let displayVal = String(value);
    // 在线状态特殊显示
    if (key === 'ONLINE_STATUS') displayVal = value === '1' || value === 1 ? '🟢 在线' : '⚪ 离线';
    // 年龄取整展示（SuperMap 数值字段可能返回 35.0 这类浮点值）
    if (key === 'AGE') {
      const age = Number(value);
      if (Number.isFinite(age)) displayVal = String(Math.round(age));
    }
    html += `<div style="margin-bottom:4px;"><b style="color:#555;">${label}:</b> <span style="color:#333;">${displayVal}</span></div>`;
  }

  // 仅摄像头显示视频流按钮
  if (typeStr === 'camera') {
    html += `<button id="${btnId}" style="margin-top:10px; width:100%; padding:8px; background:${typeCfg.color}; color:#fff; border:none; border-radius:6px; cursor:pointer; font-size:13px; font-weight:bold; transition:background 0.2s;"
      onmouseover="this.style.opacity='0.85'"
      onmouseout="this.style.opacity='1'"
    >🎥 查看视频流</button>`;
  }
  // 无人机：设置飞行目的地（火情侦察调度入口）
  if (typeStr === 'uav') {
    html += `<button id="${btnId}" style="margin-top:10px; width:100%; padding:8px; background:${typeCfg.color}; color:#fff; border:none; border-radius:6px; cursor:pointer; font-size:13px; font-weight:bold; transition:background 0.2s;"
      onmouseover="this.style.opacity='0.85'"
      onmouseout="this.style.opacity='1'"
    >🛫 设置飞行目的地</button>`;
    html += `<button id="${btnId}-direct" style="margin-top:6px; width:100%; padding:8px; background:#dc2626; color:#fff; border:none; border-radius:6px; cursor:pointer; font-size:13px; font-weight:bold; transition:background 0.2s;"
      onmouseover="this.style.opacity='0.85'"
      onmouseout="this.style.opacity='1'"
    >🚀 直接到目的地</button>`;
    html += `<p style="margin:6px 0 0 0; font-size:11px; color:#999;">💡 「设置飞行目的地」可在地图点选或输入经纬度；「直接到目的地」免输入，确认后径直飞往火情报警位置</p>`;
  }
  // 网格员：安排前往火情现场
  if (typeStr === 'member') {
    html += `<button id="${btnId}" style="margin-top:10px; width:100%; padding:8px; background:${typeCfg.color}; color:#fff; border:none; border-radius:6px; cursor:pointer; font-size:13px; font-weight:bold; transition:background 0.2s;"
      onmouseover="this.style.opacity='0.85'"
      onmouseout="this.style.opacity='1'"
    >🚶 安排前往火情现场</button>`;
  }
  html += `<p style="margin:6px 0 0 0; font-size:11px; color:#999;">📍 数据来自 SuperMap (EPSG:4490)</p>`;
  html += '</div>';
  return { html, btnId };
}

// 为单个标记绑定弹窗和视频按钮事件
function bindEntityPopup(marker: L.Marker, info: Record<string, any>, type?: string) {
  const typeStr = type || 'camera';
  const { html, btnId } = buildEntityPopup(info, typeStr);
  marker.bindPopup(html, { closeButton: true, autoClose: true, className: 'custom-camera-popup' });
  marker.on('click', function(this: any) { this.openPopup(); });
  // 仅摄像头绑定视频播放事件
  if (typeStr === 'camera') {
    marker.on('popupopen', () => {
      setTimeout(() => {
        const btn = document.getElementById(btnId);
        if (btn) {
          btn.onclick = () => { openVideoModal(info); };
        }
      }, 50);
    });
  }
  // 无人机：绑定“设置飞行目的地”与“直接到目的地”
  if (typeStr === 'uav') {
    marker.on('popupopen', () => {
      setTimeout(() => {
        const btn = document.getElementById(btnId);
        if (btn) btn.onclick = () => { startUavPickMode(marker, info); };
        const directBtn = document.getElementById(`${btnId}-direct`);
        if (directBtn) directBtn.onclick = () => { dispatchUavToDefaultTarget(marker, info); };
      }, 50);
    });
  }
  // 网格员：绑定“安排前往火情现场”
  if (typeStr === 'member') {
    marker.on('popupopen', () => {
      setTimeout(() => {
        const btn = document.getElementById(btnId);
        if (btn) btn.onclick = () => { dispatchMemberToFire(marker, info); };
      }, 50);
    });
  }
}

// 根据缩放级别切换聚合/散开图层的可见性
function updateCameraLayerVisibility() {
  if (!map || !cameraClusterLayer || !cameraSpreadLayer) return;
  const zoom = map.getZoom();
  if (zoom > ZOOM_THRESHOLD) {
    // 放大状态：显示散开的单个摄像头
    if (map.hasLayer(cameraClusterLayer)) map.removeLayer(cameraClusterLayer);
    if (!map.hasLayer(cameraSpreadLayer)) map.addLayer(cameraSpreadLayer);
  } else {
    // 缩小状态：显示聚合标记（带数字）
    if (map.hasLayer(cameraSpreadLayer)) map.removeLayer(cameraSpreadLayer);
    if (!map.hasLayer(cameraClusterLayer)) map.addLayer(cameraClusterLayer);
  }
}

// 强制重绘 bufferLayer（查询圈和中心点标记），解决 EPSG:4326 下缩放后 L.circle 未正确重绘的问题
function forceBufferLayerRedraw() {
  if (!map || !bufferLayer || !bufferLayer.getLayers().length) return;
  // 先移除再重新添加，强制 Leaflet 在新的缩放级别下重新投影和渲染所有子图层
  map.removeLayer(bufferLayer);
  map.addLayer(bufferLayer);
}

// 缩放结束综合处理：重绘缓冲区 + 切换聚合/散开
function onZoomEnd() {
  forceBufferLayerRedraw();
  updateCameraLayerVisibility();
}

function renderCameraFeatures(features: any[], _lng: number, _lat: number, _radius: number, type?: string, append = false) {
  if (!map || !cameraLayer) return;

  const typeStr = type || entityType.value || 'camera';
  if (!append) entityType.value = typeStr;
  const typeCfg = getEntityTypeConfig(typeStr);

  const COORD_TOLERANCE = 0.00005; // ~5m，小于此值视为同一点
  const SPREAD_RADIUS_DEG = 0.00025; // ~25m 散开半径

  if (append) {
    // 追加模式（多类型合并渲染）：共用同一对聚合/散开图层累积 marker。
    // 禁止 tempLayer 双父节点技巧：一个图层挂两个父组后 remove 任一父组都会把 marker 从地图摘除。
    if (!cameraClusterLayer || !cameraLayer.hasLayer(cameraClusterLayer)) {
      cameraClusterLayer = L.featureGroup();
      cameraLayer.addLayer(cameraClusterLayer);
    }
    if (!cameraSpreadLayer || !cameraLayer.hasLayer(cameraSpreadLayer)) {
      cameraSpreadLayer = L.featureGroup();
      cameraLayer.addLayer(cameraSpreadLayer);
    }
  } else {
    // 移除旧的缩放监听
    if (map) map.off('zoomend', onZoomEnd);

    // 清理旧图层（含调度动画取消）
    cancelAllTrailAnimations();
    if (cameraClusterLayer) { cameraLayer.removeLayer(cameraClusterLayer); }
    if (cameraSpreadLayer) { cameraLayer.removeLayer(cameraSpreadLayer); }
    cameraClusterLayer = L.featureGroup();
    cameraSpreadLayer = L.featureGroup();
    cameraLayer.addLayer(cameraClusterLayer);
    cameraLayer.addLayer(cameraSpreadLayer);
  }

  // 按坐标分组
  const groups: { x: number; y: number; features: any[] }[] = [];
  features.forEach((feature: any) => {
    const coords = extractGeometryXY(feature);
    if (!coords) return;
    let found = false;
    for (const g of groups) {
      if (Math.abs(g.x - coords.x) < COORD_TOLERANCE && Math.abs(g.y - coords.y) < COORD_TOLERANCE) {
        g.features.push(feature);
        found = true;
        break;
      }
    }
    if (!found) {
      groups.push({ x: coords.x, y: coords.y, features: [feature] });
    }
  });

  const entityIcon = createEntityIcon(typeStr);
  let renderedCount = 0;

  for (const g of groups) {
    const n = g.features.length;

    if (n === 1) {
      // ── 单个实体：两个图层都显示普通图标 ──
      const feature = g.features[0];
      const info = extractFeatureInfo(feature);

      // 聚合/散开两个图层副本共用 entityKey，调度时用于识别孪生 marker
      const entityKey = `${typeStr}:${info.SmID || extractEntityName(info, typeStr)}`;
      const clusterMarker = L.marker([g.y, g.x], { icon: entityIcon, entityKey } as any);
      bindEntityPopup(clusterMarker, info, typeStr);
      cameraClusterLayer.addLayer(clusterMarker);

      // 散开图层
      const spreadMarker = L.marker([g.y, g.x], { icon: entityIcon, entityKey } as any);
      bindEntityPopup(spreadMarker, info, typeStr);
      cameraSpreadLayer.addLayer(spreadMarker);

      renderedCount++;
    } else {
      // ── 多实体同坐标：聚合图层显示一个带数字的标记，散开图层显示圆形散开 ──

      // 聚合图层：一个标记 + 数字角标
      const clusterIcon = createClusterIcon(n, typeStr);
      const clusterMarker = L.marker([g.y, g.x], { icon: clusterIcon });
      // 聚合弹窗：列出该位置所有实体（摄像头可点击播放视频）
      const clusterBtnIds: string[] = [];
      const clusterFeatureInfos: Record<string, any>[] = [];
      const isClickable = typeStr === 'camera';
      let clusterPopupHtml = `<div style="min-width:240px; font-size:13px; max-height:300px; overflow-y:auto; color:#333;">`;
      clusterPopupHtml += `<h5 style="margin:0 0 8px; color:${typeCfg.color}; border-bottom:1px solid #eee; padding-bottom:4px;">${typeCfg.emoji} 该位置共 ${n} 个${typeCfg.label}</h5>`;
      g.features.forEach((f: any, i: number) => {
        const fInfo = extractFeatureInfo(f);
        clusterFeatureInfos.push(fInfo);
        const defaultName = `${typeCfg.label} ${i + 1}`;
        const fName = fInfo.name || fInfo.NAME || fInfo['名称'] || fInfo.cascadeCode || defaultName;
        const btnId = 'cluster-cam-' + (fInfo.SmID || Math.random().toString(36).substr(2, 9));
        clusterBtnIds.push(btnId);
        if (isClickable) {
          clusterPopupHtml += `<div id="${btnId}" style="padding:6px 8px; border-bottom:1px solid #f0f0f0; font-size:12px; cursor:pointer; display:flex; align-items:center; gap:6px; border-radius:4px; margin:2px 0; transition:background 0.15s;"
            onmouseover="this.style.background='#fff7e6'"
            onmouseout="this.style.background='transparent'"
          >
            <span>📷</span>
            <span style="flex:1; color:#1890ff; text-decoration:underline;">${fName}</span>
            <span style="font-size:11px; color:${typeCfg.color};">▶</span>
          </div>`;
        } else {
          clusterPopupHtml += `<div style="padding:6px 8px; border-bottom:1px solid #f0f0f0; font-size:12px; display:flex; align-items:center; gap:6px;">
            <span>${typeCfg.emoji}</span>
            <span style="flex:1;">${fName}</span>
          </div>`;
        }
      });
      if (isClickable) {
        clusterPopupHtml += `<p style="margin:6px 0 0; font-size:11px; color:#999;">💡 点击${typeCfg.label}名称可查看视频流</p>`;
      }
      clusterPopupHtml += `</div>`;
      clusterMarker.bindPopup(clusterPopupHtml, { closeButton: true, className: 'custom-camera-popup' });
      clusterMarker.on('click', function(this: any) { this.openPopup(); });
      if (isClickable) {
        clusterMarker.on('popupopen', () => {
          setTimeout(() => {
            clusterBtnIds.forEach((btnId, idx) => {
              const btn = document.getElementById(btnId);
              if (btn) {
                btn.onclick = () => { openVideoModal(clusterFeatureInfos[idx]); };
              }
            });
          }, 50);
        });
      }
      cameraClusterLayer.addLayer(clusterMarker);

      // 散开图层：每个实体圆形散开，无数字角标
      g.features.forEach((feature: any, i: number) => {
        const angle = (2 * Math.PI * i) / n - Math.PI / 2;
        const dx = SPREAD_RADIUS_DEG * Math.cos(angle);
        const dy = SPREAD_RADIUS_DEG * Math.sin(angle);
        const info = extractFeatureInfo(feature);

        // 必须携带 entityKey（格式与单实体分支一致），否则 removeTwinMarkers 无法识别并清除孪生副本，
        // 调度后原位置会残留一个不动的幽灵标记
        const spreadEntityKey = `${typeStr}:${info.SmID || extractEntityName(info, typeStr)}`;
        const spreadMarker = L.marker([g.y + dy, g.x + dx], { icon: entityIcon, entityKey: spreadEntityKey } as any);
        bindEntityPopup(spreadMarker, info, typeStr);
        cameraSpreadLayer?.addLayer(spreadMarker);
        renderedCount++;
      });
    }
  }

  // 绑定缩放监听（包含缓冲区重绘 + 聚合/散开切换）
  map.on('zoomend', onZoomEnd);
  // 根据当前缩放级别初始化可见性
  updateCameraLayerVisibility();

  // 单结果时自动打开弹窗（在两个图层上都打开，确保无论哪个可见都能看到）
  if (!append && renderedCount === 1) {
    setTimeout(() => {
      cameraClusterLayer?.eachLayer((l: any) => l.openPopup?.());
      cameraSpreadLayer?.eachLayer((l: any) => l.openPopup?.());
    }, POPUP_OPEN_DELAY_MS);
  }

  if (!append) dataCount.value = renderedCount;
  console.log(`[CameraCanvasUI] 渲染完成${append ? '（追加）' : ''}: ${renderedCount}/${features.length} 个${typeCfg.label}，${groups.length} 个位置分组`);
}


// ============ 资源调度（无人机 / 网格员） ============

function ensureDispatchLayer(): L.LayerGroup {
  if (!dispatchLayer) {
    dispatchLayer = L.layerGroup();
    map?.addLayer(dispatchLayer);
  }
  return dispatchLayer;
}

// 取消所有进行中的轨迹动画并清理调度图层（新查询 / 清场 / 卸载时调用）
function cancelAllTrailAnimations() {
  activeTrailCancels.forEach((cancel) => cancel());
  activeTrailCancels.clear();
  dispatchingMarkers.clear();
  if (map && dispatchLayer) {
    map.removeLayer(dispatchLayer);
    dispatchLayer = null;
  }
  pickTargetMarker = null;
  pendingDispatchUav = null;
  uavPickMode.value = false;
  const el = map?.getContainer();
  if (el) el.classList.remove('uav-pick-cursor');
}

// 移除同一实体在聚合/散开图层中的孪生副本（每个单实体会在两个图层各建一个 marker）
function removeTwinMarkers(clicked: L.Marker, info: Record<string, any>, typeStr: string) {
  // 优先取 marker 自身携带的 entityKey（创建时写入 options），避免重算不一致导致副本残留
  const key = (clicked as any).options?.entityKey
    || `${typeStr}:${info.SmID || extractEntityName(info, typeStr)}`;
  [cameraClusterLayer, cameraSpreadLayer].forEach((group) => {
    if (!group) return;
    const twins: L.Marker[] = [];
    group.eachLayer((l: any) => {
      const layerOptions = (l as any).options as { entityKey?: string } | undefined;
      if (l !== clicked && l instanceof L.Marker && layerOptions?.entityKey === key) twins.push(l);
    });
    twins.forEach((l) => group.removeLayer(l));
  });
}

// 把被调度的 marker 移入调度图层，避免缩放切换聚合/散开时被隐藏
function moveMarkerToDispatchLayer(marker: L.Marker) {
  cameraClusterLayer?.removeLayer(marker);
  cameraSpreadLayer?.removeLayer(marker);
  ensureDispatchLayer().addLayer(marker);
}

// 由起终点坐标派生稳定伪随机数：同一条调度航线形状固定，避免重复调度时路线跳变
function hashTrailCoords(startLng: number, startLat: number, endLng: number, endLat: number): number {
  let h = 2166136261;
  [startLng, startLat, endLng, endLat].forEach((v) => {
    const n = Math.round(v * 1e6) | 0;
    for (let shift = 0; shift < 32; shift += 8) {
      h ^= (n >>> shift) & 0xff;
      h = Math.imul(h, 16777619);
    }
  });
  return (h >>> 0) / 4294967295;
}

// 按弧长等距重采样：动画按索引插值推进，点距均等才能保证视觉匀速
function resampleByArcLength(raw: [number, number][], segments: number, lngScale: number): [number, number][] {
  const dist = (a: [number, number], b: [number, number]) =>
    Math.hypot((b[0] - a[0]) * lngScale, b[1] - a[1]);
  const cumulative: number[] = [0];
  for (let i = 1; i < raw.length; i++) cumulative.push(cumulative[i - 1] + dist(raw[i - 1], raw[i]));
  const total = cumulative[cumulative.length - 1];
  if (total <= 0) return [raw[0], raw[raw.length - 1]];
  const result: [number, number][] = [];
  let cursor = 1;
  for (let s = 0; s <= segments; s++) {
    const target = (total * s) / segments;
    while (cursor < raw.length - 1 && cumulative[cursor] < target) cursor++;
    const prev = cursor - 1;
    const span = cumulative[cursor] - cumulative[prev] || 1;
    const f = Math.min(1, Math.max(0, (target - cumulative[prev]) / span));
    result.push([
      raw[prev][0] + (raw[cursor][0] - raw[prev][0]) * f,
      raw[prev][1] + (raw[cursor][1] - raw[prev][1]) * f,
    ]);
  }
  result[segments] = [raw[raw.length - 1][0], raw[raw.length - 1][1]];
  return result;
}

// 调度航线：起终点间带轻微弯曲的路线。主方向严格单调推进（不回折、不绕圈），
// 侧向偏移用 sin(πt) 包络使首末点精确锚定；bends 控制弧段数（无人机平缓、网格员贴近街道）
function buildDispatchTrail(
  startLng: number,
  startLat: number,
  endLng: number,
  endLat: number,
  bow: number = UAV_TRAIL_BOW,
  bends: number = 1,
): [number, number][] {
  // 坐标守卫：任一端非法（如目的地缺失传入 undefined）则退化为起点，避免 NaN 航线静默失败
  if (![startLng, startLat, endLng, endLat].every((v) => typeof v === 'number' && Number.isFinite(v))) {
    return [[startLng, startLat], [startLng, startLat]];
  }
  if (startLng === endLng && startLat === endLat) return [[startLng, startLat], [endLng, endLat]];
  const dLng = endLng - startLng;
  const dLat = endLat - startLat;
  const lngScale = Math.cos(((startLat + endLat) / 2) * Math.PI / 180) || 1;
  const len = Math.hypot(dLng * lngScale, dLat);
  const nx = -dLat / len;
  const ny = (dLng * lngScale) / len;
  const rnd = hashTrailCoords(startLng, startLat, endLng, endLat);
  const side = rnd < 0.5 ? -1 : 1;
  const amp = (len * bow * (0.7 + rnd * 0.6)) / lngScale;
  const phase = Math.PI * (0.3 + rnd * 0.4);
  const RAW_SAMPLES = 240;
  const raw: [number, number][] = [];
  for (let i = 0; i <= RAW_SAMPLES; i++) {
    const t = i / RAW_SAMPLES;
    // 调制因子恒为正，偏移始终偏向同一侧，因此不会出现穿越直线的反向摆动
    const shape = 0.55 + 0.45 * Math.sin(Math.PI * 2 * bends * t + phase);
    const offset = Math.sin(Math.PI * t) * amp * side * shape;
    raw.push([
      startLng + dLng * t + nx * offset,
      startLat + dLat * t + ny * offset,
    ]);
  }
  return resampleByArcLength(raw, DISPATCH_TRAIL_SEGMENTS, lngScale);
}

// 轨迹动画：驱动 marker 沿轨迹移动，同步绘制计划路径（虚线）与已走路径（实线）
function animateEntityAlongTrail(marker: L.Marker, trail: [number, number][], opts: { color: string; durationMs: number; onArrive?: () => void }) {
  if (!map || trail.length < 2) {
    console.warn('[CameraCanvasUI] 轨迹动画未启动：', { hasMap: !!map, trailLen: trail?.length });
    return;
  }
  const layer = ensureDispatchLayer();
  console.log('[CameraCanvasUI] 轨迹动画启动：', {
    points: trail.length,
    start: trail[0],
    end: trail[trail.length - 1],
    durationMs: opts.durationMs,
    layerOnMap: map.hasLayer(layer),
    markerInLayer: layer.hasLayer(marker),
    hasMarkerEl: !!marker.getElement(),
  });
  marker.closePopup();
  dispatchingMarkers.add(marker);
  L.polyline(trail.map((p) => [p[1], p[0]] as L.LatLngExpression), { color: opts.color, weight: 2, opacity: 0.45, dashArray: '6, 8' }).addTo(layer);
  const progress = L.polyline([], { color: opts.color, weight: 4, opacity: 0.9 }).addTo(layer);
  const markerEl = marker.getElement();
  if (markerEl) markerEl.style.filter = `drop-shadow(0 0 6px ${opts.color})`;
  let cancelled = false;
  let rafId = 0;
  const startTs = performance.now();
  // 统一释放：动画自然结束 / 被取消 / marker 已脱离调度图层，均需解除守卫并清除高亮
  const release = () => {
    activeTrailCancels.delete(cancel);
    dispatchingMarkers.delete(marker);
    if (markerEl) markerEl.style.filter = '';
  };
  const cancel = () => {
    cancelled = true;
    if (rafId) cancelAnimationFrame(rafId);
    release();
  };
  activeTrailCancels.add(cancel);
  const stepFn = (ts: number) => {
    // marker 已被图层移除（清场 / 缩放切换）时终止，避免操作已脱离地图的对象
    if (cancelled || !map || !layer.hasLayer(marker)) {
      console.warn('[CameraCanvasUI] 轨迹动画中途终止：', { cancelled, hasMap: !!map, markerInLayer: layer.hasLayer(marker) });
      release();
      return;
    }
    const t = Math.min(1, (ts - startTs) / opts.durationMs);
    const idxF = t * (trail.length - 1);
    const i = Math.floor(idxF);
    const frac = idxF - i;
    const [x1, y1] = trail[i];
    const [x2, y2] = trail[Math.min(i + 1, trail.length - 1)];
    const cur: [number, number] = [x1 + (x2 - x1) * frac, y1 + (y2 - y1) * frac];
    marker.setLatLng([cur[1], cur[0]]);
    progress.setLatLngs(trail.slice(0, i + 1).concat([cur]).map((p) => [p[1], p[0]] as L.LatLngExpression));
    if (t < 1) {
      rafId = requestAnimationFrame(stepFn);
    } else {
      release();
      opts.onArrive?.();
    }
  };
  rafId = requestAnimationFrame(stepFn);
}

// 十字光标仅在地图点选模式生效（坐标输入模式不应改变光标）
function applyPickCursor() {
  const el = map?.getContainer();
  if (!el) return;
  if (uavPickMode.value && uavPickTab.value === 'map') el.classList.add('uav-pick-cursor');
  else el.classList.remove('uav-pick-cursor');
}

// 进入无人机飞行目的地设置
function startUavPickMode(marker: L.Marker, info: Record<string, any>) {
  if (dispatchingMarkers.has(marker)) {
    showNotification('该无人机正在执行任务中，请等待其抵达后再调度', 'warning');
    return;
  }
  exitUavPickMode();
  pendingDispatchUav = { marker, info };
  uavPickMode.value = true;
  uavPickTab.value = 'map';
  // 火情应急场景预填报警位置，切到坐标页可直接确认无需手输
  if (firePoint) {
    uavCoordLng.value = String(Number(firePoint.lng.toFixed(6)));
    uavCoordLat.value = String(Number(firePoint.lat.toFixed(6)));
  }
  map?.closePopup();
  applyPickCursor();
  showNotification('🛫 可在地图上点选，或切换到「输入坐标」直接填写经纬度', 'info');
}

// 直接到目的地：免录入经纬度，以火情报警位置（缺失时回退到搜索中心点）为目的地，确认后径直飞往
function dispatchUavToDefaultTarget(marker: L.Marker, info: Record<string, any>) {
  if (dispatchingMarkers.has(marker)) {
    showNotification('该无人机正在执行任务中，请等待其抵达后再调度', 'warning');
    return;
  }
  const name = extractEntityName(info, 'uav');
  const target = firePoint || { lng: queryCenter.value.lng, lat: queryCenter.value.lat };
  const targetLabel = firePoint ? '火情报警位置' : '搜索中心点';
  // 不进入目的地设置面板：清理上一次状态后直接锁定默认目的地
  exitUavPickMode();
  pendingDispatchUav = { marker, info };
  map?.closePopup();
  // 瞬时定位（非动画），避免 openPopup 内部的 _adjustPan 在平移动画中读到中间态位移而追加 panBy
  map?.panTo([target.lat, target.lng], { animate: false });
  placePickTargetMarker(target.lat, target.lng, true);
  showNotification(`🚀 ${name} 目的地已锁定：${targetLabel}，请在 🎯 标记处确认起飞`, 'info');
}

// 切换目的地录入方式
function switchUavPickTab(tab: 'map' | 'coord') {
  if (uavPickTab.value === tab) return;
  uavPickTab.value = tab;
  uavCoordError.value = '';
  // 已在地图上点选过时回填坐标，避免重复录入
  if (tab === 'coord' && pickTargetMarker) {
    const pos = pickTargetMarker.getLatLng();
    uavCoordLng.value = String(Number(pos.lng.toFixed(6)));
    uavCoordLat.value = String(Number(pos.lat.toFixed(6)));
  }
  applyPickCursor();
}

// 校验坐标输入（合法区间与地图可视范围一致，超出后 marker 会被 setMaxBounds 推出视野）
function parseUavCoord(): { lat: number; lng: number } | null {
  uavCoordError.value = '';
  const lngText = uavCoordLng.value.trim();
  const latText = uavCoordLat.value.trim();
  if (!lngText || !latText) {
    uavCoordError.value = '请填写完整的经度与纬度';
    return null;
  }
  const lng = Number(lngText);
  const lat = Number(latText);
  if (!Number.isFinite(lng) || !Number.isFinite(lat)) {
    uavCoordError.value = '坐标格式无效，请输入数字';
    return null;
  }
  if (lng < MAP_BOUNDS_LNG[0] || lng > MAP_BOUNDS_LNG[1]) {
    uavCoordError.value = `经度需在 ${MAP_BOUNDS_LNG[0]} ~ ${MAP_BOUNDS_LNG[1]} 之间`;
    return null;
  }
  if (lat < MAP_BOUNDS_LAT[0] || lat > MAP_BOUNDS_LAT[1]) {
    uavCoordError.value = `纬度需在 ${MAP_BOUNDS_LAT[0]} ~ ${MAP_BOUNDS_LAT[1]} 之间`;
    return null;
  }
  return { lat, lng };
}

// 定位预览：仅落 🎯 标记并平移到视野中心，不起飞，供用户核对位置
function previewUavCoord() {
  const coord = parseUavCoord();
  if (!coord) return;
  placePickTargetMarker(coord.lat, coord.lng, false);
  map?.flyTo([coord.lat, coord.lng], Math.max(map?.getZoom() ?? DEFAULT_ZOOM, 15), { duration: 0.8 });
  showNotification(`🎯 已定位到 ${coord.lng.toFixed(6)}, ${coord.lat.toFixed(6)}`, 'info');
}

// 输入坐标方式确认起飞（复用地图点选同一条调度链路）
function submitUavCoord() {
  const coord = parseUavCoord();
  if (!coord) return;
  if (!pendingDispatchUav) {
    uavCoordError.value = '调度任务已失效，请重新点击无人机图标';
    return;
  }
  confirmUavDispatch(coord.lat, coord.lng);
}

// 退出目的地设置（清空标记、输入与光标状态）
function exitUavPickMode() {
  if (pickTargetMarker) {
    pickTargetMarker.remove();
    pickTargetMarker = null;
  }
  pendingDispatchUav = null;
  uavPickMode.value = false;
  uavPickTab.value = 'map';
  uavCoordLng.value = '';
  uavCoordLat.value = '';
  uavCoordError.value = '';
  const el = map?.getContainer();
  if (el) el.classList.remove('uav-pick-cursor');
}

// 放置 🎯 飞行目的地预览标记（地图点选与坐标输入共用，保证视觉与确认路径一致）
function placePickTargetMarker(lat: number, lng: number, withConfirmPopup: boolean) {
  if (!map) return;
  if (pickTargetMarker) pickTargetMarker.remove();
  const icon = L.divIcon({
    className: 'uav-target-marker',
    html: `<div style="position:relative; width:30px; height:30px;">
      <div style="position:absolute; inset:0; border:2px solid #dc2626; border-radius:50%; animation:query-point-pulse 1.5s ease-in-out infinite;"></div>
      <div style="position:absolute; top:2px; left:2px; width:26px; height:26px; background:rgba(220,38,38,0.85); border:2px solid #fff; border-radius:50%;
        display:flex; align-items:center; justify-content:center; font-size:14px;">🎯</div>
    </div>`,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
  });
  pickTargetMarker = L.marker([lat, lng], { icon, zIndexOffset: 1500 }).addTo(ensureDispatchLayer());
  if (!withConfirmPopup) return;
  const okId = 'uav-target-ok';
  const cancelId = 'uav-target-cancel';
  pickTargetMarker
    .bindPopup(`<div style="min-width:190px; font-size:13px; color:#333;">
      <h5 style="margin:0 0 6px 0; color:#dc2626; border-bottom:1px solid #eee; padding-bottom:4px;">🎯 飞行目的地</h5>
      <div style="margin-bottom:4px;"><b>经度:</b> ${lng.toFixed(6)}</div>
      <div style="margin-bottom:4px;"><b>纬度:</b> ${lat.toFixed(6)}</div>
      <div style="display:flex; gap:8px; margin-top:8px;">
        <button id="${okId}" style="flex:1; padding:7px; background:#fa8c16; color:#fff; border:none; border-radius:6px; cursor:pointer; font-weight:bold;">✅ 确认起飞</button>
        <button id="${cancelId}" style="flex:1; padding:7px; background:#999; color:#fff; border:none; border-radius:6px; cursor:pointer;">取消</button>
      </div>
    </div>`, { closeButton: true, className: 'custom-camera-popup' });
  // Leaflet 在 openPopup 内部同步 fire('popupopen')，必须先注册监听再打开，否则确认/取消按钮绑不上事件
  pickTargetMarker.on('popupopen', () => {
    setTimeout(() => {
      const okBtn = document.getElementById(okId);
      const cancelBtn = document.getElementById(cancelId);
      if (okBtn) okBtn.onclick = () => confirmUavDispatch(lat, lng);
      if (cancelBtn) cancelBtn.onclick = () => exitUavPickMode();
    }, 50);
  });
  pickTargetMarker.openPopup();
}

// 地图点击：仅点选模式下放置目的地标记并弹出确认气泡
function onMapClick(e: L.LeafletMouseEvent) {
  if (!uavPickMode.value || uavPickTab.value !== 'map' || !pendingDispatchUav) return;
  const target = e.originalEvent?.target as HTMLElement | undefined;
  if (target?.closest?.('.leaflet-marker-icon, .leaflet-popup')) return;
  const { lat, lng } = e.latlng;
  placePickTargetMarker(lat, lng, true);
}

// 抵达火情点后的现场视频（无人机与网格员共用同一份素材与样式，保证两处观感一致）
const FIRE_RECON_VIDEO_HTML = `<video
    src="${fireVideoUrl}"
    style="display:block; width:100%; max-height:180px; margin-bottom:8px; border-radius:6px; background:#000; object-fit:cover;"
    muted autoplay loop playsinline controls></video>`;

// 无人机抵达火情点后的现场侦察图片（可见光 + 热成像并排展示，不含叠加文字）
const FIRE_RECON_IMAGES_HTML = `<div style="display:flex; gap:6px; margin-bottom:8px; align-items:stretch;">
  <img src="${fireVisibleLightUrl}" alt="火情可见光" style="flex:1; width:50%; min-width:0; max-height:160px; border-radius:6px; object-fit:cover; display:block;">
  <img src="${fireThermalUrl}" alt="真实火情热成像" style="flex:1; width:50%; min-width:0; max-height:160px; border-radius:6px; object-fit:cover; display:block;">
</div>`;

// popup 关闭时 Leaflet 已先行摘除容器，需显式停止解码与缓冲
function bindFireReconVideoRelease(popup: L.Popup) {
  const openedVideo = popup.getElement()?.querySelector('video');
  popup.on('popupclose', () => {
    const v = openedVideo ?? popup.getElement()?.querySelector('video');
    if (!v) return;
    v.pause();
    v.removeAttribute('src');
    v.load();
  });
}

// 确认无人机起飞：沿规划航线前往点选的火情报警位置
function confirmUavDispatch(targetLat: number, targetLng: number) {
  if (!pendingDispatchUav) return;
  const { marker, info } = pendingDispatchUav;
  const name = extractEntityName(info, 'uav');
  exitUavPickMode();
  if (dispatchingMarkers.has(marker)) {
    showNotification('该无人机正在执行任务中，请等待其抵达后再调度', 'warning');
    return;
  }
  removeTwinMarkers(marker, info, 'uav');
  moveMarkerToDispatchLayer(marker);
  const start = marker.getLatLng();
  const trail = buildDispatchTrail(start.lng, start.lat, targetLng, targetLat, UAV_TRAIL_BOW, 1);
  showNotification(`🚁 ${name} 已起飞，沿规划航线前往火情位置侦察`, 'info');
  animateEntityAlongTrail(marker, trail, {
    color: '#fa8c16',
    durationMs: UAV_ANIM_DURATION_MS,
    onArrive: () => {
      map?.panTo([targetLat, targetLng]);
      showNotification(`🚁 ${name} 已抵达火情位置上空，开始火情侦察`, 'success');
      if (!map) return;
      const reconPopup = L.popup({ className: 'custom-camera-popup', offset: [0, -14], minWidth: 300, maxWidth: 340 })
        .setLatLng(marker.getLatLng())
        .setContent(`<div style="min-width:300px; font-size:13px;">
          <h5 style="margin:0 0 6px; color:#fa8c16;">🚁 火情侦察报告</h5>
          ${FIRE_RECON_IMAGES_HTML}
          <div>✅ ${name} 已抵达火情报警位置上空</div>
        </div>`);
      reconPopup.openOn(map);
    },
  });
}

// 安排网格员前往火情现场侦察（目的地：火情报警位置，缺失时回退到最近查询中心）
function dispatchMemberToFire(marker: L.Marker, info: Record<string, any>) {
  if (dispatchingMarkers.has(marker)) {
    showNotification('该网格员正在执行任务中，请等待其抵达后再调度', 'warning');
    return;
  }
  const name = extractEntityName(info, 'member');
  const target = firePoint || { lng: queryCenter.value.lng, lat: queryCenter.value.lat };
  map?.closePopup();
  removeTwinMarkers(marker, info, 'member');
  moveMarkerToDispatchLayer(marker);
  const start = marker.getLatLng();
  const trail = buildDispatchTrail(start.lng, start.lat, target.lng, target.lat, MEMBER_TRAIL_BOW, 2);
  console.log('[CameraCanvasUI] 网格员调度：', {
    name,
    hasFirePoint: !!firePoint,
    start: [start.lng, start.lat],
    target: [target.lng, target.lat],
    sameSpot: start.lng === target.lng && start.lat === target.lat,
  });
  showNotification(`👤 ${name} 已接受调度，正在前往火情现场`, 'info');
  animateEntityAlongTrail(marker, trail, {
    color: '#52c41a',
    durationMs: MEMBER_ANIM_DURATION_MS,
    onArrive: () => {
      showNotification(`👤 ${name} 已抵达火情现场，开始现场侦察`, 'success');
      if (!map) return;
      const memberReconPopup = L.popup({ className: 'custom-camera-popup', offset: [0, -14], minWidth: 300, maxWidth: 340 })
        .setLatLng(marker.getLatLng())
        .setContent(`<div style="min-width:300px; font-size:13px;">
          <h5 style="margin:0 0 6px; color:#52c41a;">👤 网格员现场反馈</h5>
          ${FIRE_RECON_VIDEO_HTML}
          <div>✅ ${name} 已抵达火情现场</div>
          <div>🔍 正在实地核实火情并回传信息</div>
        </div>`);
      memberReconPopup.openOn(map);
      bindFireReconVideoRelease(memberReconPopup);
    },
  });
}

// ============ Video Stream Playback ============

async function openVideoModal(cameraInfoData: Record<string, any>) {
  currentCameraName.value = cameraInfoData.name || cameraInfoData.NAME || cameraInfoData['摄像头名称'] || cameraInfoData.cascadeCode || '视频播放';
  videoModalVisible.value = true;
  videoLoading.value = true;

  let cascadeCode = extractCascadeCode(cameraInfoData);

  console.log('[CameraCanvasUI] Fetching video URL for cascadeCode:', cascadeCode, 'Camera Info:', cameraInfoData);

  if (!cascadeCode) {
    console.error('[CameraCanvasUI] 无法获取到摄像头 cascadeCode');
    videoLoading.value = false;
    showNotification('无法获取摄像头编码，无法播放视频', 'error');
    return;
  }

  try {
    const requestUrl = `${VIDEO_STREAM_API}?cascadeCode=${cascadeCode}`;
    console.log('[CameraCanvasUI] Sending request to:', requestUrl);

    const response = await fetch(requestUrl);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const result = await response.json();
    console.log('[CameraCanvasUI] Response from getCameraUrl:', result);

    const videoUrl = result.data?.url || result.url || result.result?.url;
    if (result.success && videoUrl) {
      videoLoading.value = false;
      initPlayer(videoUrl);
    } else {
      console.warn('[CameraCanvasUI] 获取视频流失败, 接口返回业务失败或无URL', result);
      videoLoading.value = false;
      showNotification('获取视频流地址失败', 'warning');
    }
  } catch (err: any) {
    console.error('[CameraCanvasUI] 获取视频流出错:', err);
    videoLoading.value = false;
    showNotification(`获取视频流出错: ${err?.message || '请求异常'}`, 'error');
  }
}

async function initPlayer(videoUrl: string) {
  await nextTick();
  if (!h5playerContainer.value) return;
  h5playerContainer.value.innerHTML = '';

  try {
    await ensureH5PlayerScript();
  } catch (error) {
    console.warn('[CameraCanvasUI] h5player 脚本加载失败，回退使用原生 video 标签', error);
  }

  // 如果存在海康的 JSPlugin 则用它播放
  if (typeof (window as any).JSPlugin !== 'undefined') {
    console.log('[CameraCanvasUI] 检测到 JSPlugin，创建播放器容器');
    const playerDiv = document.createElement('div');
    playerDiv.id = 'h5player-camera-' + Date.now();
    playerDiv.style.width = '100%';
    playerDiv.style.height = '100%';
    h5playerContainer.value.appendChild(playerDiv);

    try {
      h5player = new (window as any).JSPlugin({
        szId: playerDiv.id,
        szBasePath: getPublicAssetUrl('resource'),
        iWidth: '100%',
        iHeight: '100%',
        openDebug: false,
        mseWorkerEnable: true,
        bSupporDoubleClickFull: true,
        bWarnBrowsers: [],
        oStyle: {
          borderSelect: '#fa8c16',
        },
      });

      const isWs = videoUrl.startsWith('ws://') || videoUrl.startsWith('wss://');
      console.log('[CameraCanvasUI] 开始初始化海康播放器, playURL:', videoUrl, 'protocol:', isWs ? 'ws' : 'http');

      h5player.JS_SetWindowControlCallback({
        pluginErrorHandler: function (_iWndIndex: number, iErrorCode: number, oError: any) {
          console.error('[CameraCanvasUI] 播放器错误:', iErrorCode, oError);
        }
      });

      h5player.JS_Play(videoUrl, {
        playURL: videoUrl,
        mode: 0,
        keepDecoder: 1,
        token: '',
        protocol: isWs ? 'ws' : 'http',
        decodeType: 'auto'
      }, 0)
        .then(
          () => console.log('[CameraCanvasUI] JS_Play success! 视频已开始播放'),
          (err: any) => {
            console.error('[CameraCanvasUI] JS_Play failed! 播放失败', err);
            showNotification('视频播放失败，请检查视频流地址', 'error');
          }
        );
      return;
    } catch (e) {
      console.error('[CameraCanvasUI] JSPlugin 播放失败', e);
    }
  } else {
    console.warn('[CameraCanvasUI] 未检测到 JSPlugin (海康H5Player库)，回退使用原生 video 标签');
  }

  fallbackToHtml5Video(videoUrl);
}

function fallbackToHtml5Video(videoUrl: string) {
  if (!h5playerContainer.value) return;
  h5playerContainer.value.innerHTML = '';
  const videoEl = document.createElement('video');
  videoEl.style.width = '100%';
  videoEl.style.height = '100%';
  videoEl.controls = true;
  videoEl.autoplay = true;
  videoEl.src = videoUrl;
  h5playerContainer.value.appendChild(videoEl);
}

function closeVideoModal() {
  if (h5player && typeof h5player.JS_Stop === 'function') {
    try { h5player.JS_Stop(0); } catch (e) { /* ignore */ }
  }
  h5player = null;
  videoModalVisible.value = false;
  currentCameraName.value = '';
  videoLoading.value = false;
  if (h5playerContainer.value) {
    h5playerContainer.value.innerHTML = '';
  }
}

// ============ Parse Map Config from Content ============
function parseMapConfig(content: string): any {
  // 检查是否包含 markdown 代码块包裹
  const fenceMatch = content.match(/```(?:map)?\s*\n?([\s\S]*?)```/);
  if (fenceMatch) {
    content = fenceMatch[1];
  }

  try {
    const trimmed = content.trim();
    if (!trimmed) return null;
    return JSON.parse(trimmed);
  } catch (e: any) {
    // 尝试 unescape 双重转义内容后重新解析（execute 工具输出可能含 \"、\\）
    if (content.includes('\\"')) {
      try {
        const unescaped = content.replace(/\\"/g, '"').replace(/\\\\/g, '\\');
        const result = JSON.parse(unescaped.trim());
        if (result && typeof result === 'object') return result;
      } catch (_) { /* fall through to existing fallbacks */ }
    }

    const isTruncated = e?.message?.includes('position') &&
      parseInt(e?.message?.match(/position\s+(\d+)/)?.[1] || '-1') >= content.length - 1;

    if (isTruncated) {
      // JSON 可能被截断，尝试提取可用信息
      const nameMatch = content.match(/"name"\s*:\s*"([^"]+)"/);
      if (nameMatch) {
        return {
          type: 'map',
          name: nameMatch[1],
          isCamera: true,
          queryResult: { features: [], _queryParams: {} }
        };
      }
    }

    try {
      const match = content.match(/\{[\s\S]*\}/);
      if (match) return JSON.parse(match[0]);
    } catch (_e2) {
      // 正则提取也失败
    }
    return null;
  }
}

// ============ Fire Response (火情应急响应级联渲染) ============

async function renderFireResponse(config: any) {
  if (!map || !cameraLayer || !bufferLayer) return;
  const currentMap = map;
  const currentCameraLayer = cameraLayer;
  const currentBufferLayer = bufferLayer;

  const [lat, lng] = config.fireCenter || config.center || [DEFAULT_CENTER[0], DEFAULT_CENTER[1]];
  // 记录火情报警位置，作为无人机点选目的地与网格员调度目的地
  firePoint = { lng, lat };
  const fireArea = config.fireArea || '';
  const summary = config.summary || {};
  const historyFireCount = summary.historyFireCount || 0;
  const recommendedUAVs = summary.recommendedUAVs || [];

  // 各资源类型查询半径（skill 下发，缺失时回退到默认值）
  const radii = config.radii || summary.radii || {};
  const DEFAULT_FIRE_RADIUS: Record<string, number> = { camera: 5000, uav: 10000, member: 5000, satellite: 5000 };
  const radiusOf = (type: string) => radii[type] || DEFAULT_FIRE_RADIUS[type] || 5000;
  const radiusKm = (type: string) => (radiusOf(type) / 1000).toFixed(radiusOf(type) % 1000 === 0 ? 0 : 1);
  const fmtDist = (m?: number) => (m == null ? '-' : (m < 1000 ? `${m}m` : `${(m / 1000).toFixed(1)}km`));

  // 清空旧图层（含进行中的调度动画）
  cancelAllTrailAnimations();
  currentCameraLayer.clearLayers();
  currentBufferLayer.clearLayers();

  // ── 1. 绘制火情中心标记（🔥 红色脉冲） ──
  const fireIcon = L.divIcon({
    className: 'fire-center-marker',
    html: `<div style="position:relative; width:40px; height:40px;">
      <div style="position:absolute; inset:0; background:rgba(220,38,38,0.3); border-radius:50%;
        animation: query-point-pulse 2s ease-in-out infinite;"></div>
      <div style="position:absolute; top:4px; left:4px; width:32px; height:32px;
        background:rgba(220,38,38,0.85); border:3px solid #fff; border-radius:50%;
        box-shadow:0 2px 12px rgba(220,38,38,0.5); display:flex; align-items:center;
        justify-content:center; font-size:18px;">🔥</div>
    </div>`,
    iconSize: [40, 40],
    iconAnchor: [20, 20]
  });

  let firePopupHtml = `<div style="min-width:200px; font-size:13px; color:#333;">`;
  firePopupHtml += `<h5 style="margin:0 0 8px; color:#dc2626; border-bottom:1px solid #eee; padding-bottom:4px;">🔥 火情中心</h5>`;
  firePopupHtml += `<div style="margin-bottom:4px;"><b>经度:</b> ${lng.toFixed(6)}</div>`;
  firePopupHtml += `<div style="margin-bottom:4px;"><b>纬度:</b> ${lat.toFixed(6)}</div>`;
  if (fireArea) firePopupHtml += `<div style="margin-bottom:4px;"><b>火情面积:</b> ${fireArea}</div>`;
  firePopupHtml += `<hr style="border:none; border-top:1px solid #eee; margin:8px 0;">`;
  firePopupHtml += `<div style="margin-bottom:3px;">📹 摄像头: <b>${summary.cameraCount || 0}</b> 个 <span style="color:#999;">(${radiusKm('camera')}km)</span></div>`;
  firePopupHtml += `<div style="margin-bottom:3px;">🚁 无人机: <b>${summary.uavCount || 0}</b> 台 <span style="color:#999;">(${radiusKm('uav')}km)</span></div>`;
  firePopupHtml += `<div style="margin-bottom:3px;">👤 网格员: <b>${summary.memberCount || 0}</b> 名 <span style="color:#999;">(${radiusKm('member')}km)</span></div>`;
  firePopupHtml += `<div style="margin-top:6px; color:#666;">可调度资源总计: <b style="color:#dc2626;">${summary.totalResources || 0}</b></div>`;

  if (recommendedUAVs.length > 0) {
    const lines = recommendedUAVs
      .map((u: any, i: number) => `${i + 1}. ${u.name || `无人机 ${i + 1}`}（${fmtDist(u.distance)}）`)
      .join('<br>');
    firePopupHtml += `<div style="margin-top:6px; padding:6px 8px; background:#fff7e6; border-radius:4px; font-size:12px; line-height:1.6;">
      <b style="color:#fa8c16;">🚁 建议优先调派</b><br>${lines}
    </div>`;
  }

  firePopupHtml += `<hr style="border:none; border-top:1px solid #eee; margin:8px 0;">`;
  firePopupHtml += `<div style="color:${historyFireCount > 0 ? '#dc2626' : '#52c41a'};">
    🔥 历史火情(${radiusKm('satellite')}km): <b>${historyFireCount}</b> 处${historyFireCount > 0 ? ' — 注意复燃风险' : ''}
  </div>`;
  firePopupHtml += `</div>`;

  L.marker([lat, lng], { icon: fireIcon, zIndexOffset: 2000 })
    .bindPopup(firePopupHtml, { className: 'custom-camera-popup' })
    .addTo(currentBufferLayer);

  // ── 2. 按各资源类型半径绘制查询范围圈（大圈先画，颜色与图标一致） ──
  ['uav', 'camera', 'member'].forEach((type) => {
    const cfg = getEntityTypeConfig(type);
    L.circle([lat, lng], {
      radius: radiusOf(type),
      color: cfg.color,
      fillColor: cfg.color,
      fillOpacity: 0.05,
      weight: 1.5,
      dashArray: '6, 4'
    })
      .bindTooltip(`${cfg.emoji} ${cfg.label} ${radiusKm(type)}km`, { direction: 'top' })
      .addTo(currentBufferLayer);
  });

  // ── 3. 逐类以 append 模式渲染到共用的聚合/散开图层 ──
  const allBounds = L.latLngBounds([[lat, lng]]);

  const entityTypes: Array<{ preset: any[]; type: string; radius: number }> = [
    { preset: config.cameras?.features || [], type: 'camera', radius: radiusOf('camera') },
    { preset: config.uavs?.features || [], type: 'uav', radius: radiusOf('uav') },
    { preset: config.members?.features || [], type: 'member', radius: radiusOf('member') },
    { preset: config.historyFires?.features || [], type: 'satellite', radius: radiusOf('satellite') },
  ];

  const summaryParts: string[] = [];

  for (const { preset, type, radius } of entityTypes) {
    // 轻量配置不携带 features，前端自查；旧版全量配置直接使用
    let features = preset;
    if (features.length === 0) {
      features = await fetchEntitiesFromServer({ lng, lat, radius }, type);
    }
    if (features.length === 0) continue;

    renderCameraFeatures(features, lng, lat, radius, type, true);

    // 扩展 bounds
    if (currentCameraLayer.getLayers().length > 0) {
      try { allBounds.extend(cameraLayer!.getBounds()); } catch (_e) { /* ignore */ }
    }
    summaryParts.push(`${getEntityTypeConfig(type).emoji}${features.length}`);
  }

  // ── 4. 适配视图 ──
  try {
    currentMap.fitBounds(allBounds, { padding: [60, 60], maxZoom: 15 });
  } catch (_e) {
    currentMap.setView([lat, lng], 13);
  }

  // ── 5. 通知 ──
  showNotification(`火情响应: ${summaryParts.join(' ')}`, 'success');

  // 视图动画结束后刷新行政图层
  setTimeout(() => loadAdminLayers(), 800);
}

// ============ 实体数据自查（multiEntity / fireResponse 轻量配置用） ============
// 轻量 mapConfig 不携带全量 features，前端按查询参数自行请求 SuperMap
async function fetchEntitiesFromServer(
  params: { lng: number; lat: number; radius: number },
  type: string,
  expectedCount?: number
): Promise<any[]> {
  const queryCfg = ENTITY_QUERY_CONFIG[type];
  if (!queryCfg || !map) return [];

  const degrees = params.radius / 111319.49;
  const requestBody = {
    getFeatureMode: 'BUFFER',
    datasetNames: [queryCfg.datasetName],
    geometry: { type: 'POINT', points: [{ x: params.lng, y: params.lat }] },
    bufferDistance: degrees,
    hasGeometry: true,
    maxFeatures: 1000
  };

  try {
    isLoading.value = true;
    loadingMessage.value = `正在加载${getEntityTypeConfig(type).label}数据...`;
    const res = await fetch(queryCfg.url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json; charset=utf-8' },
      body: JSON.stringify(requestBody)
    });
    const data = await res.json();
    if (data?.succeed === false || data?.error) {
      console.error(`[CameraCanvasUI] SuperMap 查询失败 (${type}):`, data?.error);
      return [];
    }
    const features = extractFeatures(data) || [];
    console.log(`[CameraCanvasUI] fetchEntitiesFromServer(${type}): ${features.length} 个${expectedCount != null ? `（skill 报告 ${expectedCount}）` : ''}`);
    return features;
  } catch (err: any) {
    console.error(`[CameraCanvasUI] fetchEntitiesFromServer(${type}) 请求失败:`, err?.message || err);
    return [];
  } finally {
    isLoading.value = false;
  }
}

// ============ 多类型合并渲染（同一张地图叠加多类实体） ============
// 对应 skill 的 type='all'：一个 map 配置携带 entityGroups，
// 避免多次调用生成多个 map 代码块（客户端只保留第一个，其余会被丢弃）
async function renderMultiEntity(config: any) {
  const lng = config.queryParams?.lng ?? config.center?.[1];
  const lat = config.queryParams?.lat ?? config.center?.[0];
  const groups = (config.entityGroups || []).filter((g: any) => g.entityType && ENTITY_QUERY_CONFIG[g.entityType]);
  if (lng == null || lat == null || groups.length === 0 || !map || !cameraLayer || !bufferLayer) return;
  const currentMap = map;
  const currentCameraLayer = cameraLayer;
  const currentBufferLayer = bufferLayer;

  // ── 1. 清理旧图层（含进行中的调度动画），按各类型半径绘制范围圈 ──
  cancelAllTrailAnimations();
  currentCameraLayer.clearLayers();
  currentBufferLayer.clearLayers();

  groups.forEach((g: any) => {
    const cfg = getEntityTypeConfig(g.entityType);
    L.circle([lat, lng], {
      radius: g.radius,
      color: cfg.color,
      fillColor: cfg.color,
      fillOpacity: 0.05,
      weight: 1.5,
      dashArray: '5, 4'
    })
      .bindTooltip(`${cfg.emoji} ${cfg.label} ${Math.round(g.radius / 1000)}km`, { direction: 'top' })
      .addTo(currentBufferLayer);
  });
  addQueryPointMarker(lat, lng);

  // ── 2. 逐类查询并以 append 模式渲染到共用的聚合/散开图层 ──
  const allBounds = L.latLngBounds([[lat, lng]]);
  const summaryParts: string[] = [];
  let totalRendered = 0;

  for (const g of groups) {
    const features = await fetchEntitiesFromServer(
      { lng, lat, radius: g.radius },
      g.entityType,
      g.count
    );
    if (features.length === 0) continue;

    renderCameraFeatures(features, lng, lat, g.radius, g.entityType, true);

    try { allBounds.extend(currentCameraLayer.getBounds()); } catch (_e) { /* ignore */ }
    totalRendered += features.length;
    summaryParts.push(`${getEntityTypeConfig(g.entityType).emoji}${features.length}`);
  }

  // ── 3. 适配视图 + 信息面板 ──
  try {
    currentMap.fitBounds(allBounds, { padding: [60, 60], maxZoom: 15 });
  } catch (_e) {
    currentMap.setView([lat, lng], DEFAULT_ZOOM);
  }

  emit('update:status', 'complete');

  showNotification(
    totalRendered > 0 ? `已加载 ${totalRendered} 个（${summaryParts.join(' ')}）` : '未找到匹配数据',
    totalRendered > 0 ? 'success' : 'warning'
  );

  setTimeout(() => loadAdminLayers(), 800);
}

// ============ Render from Config ============
let autoQueryTimer: ReturnType<typeof setTimeout> | null = null;
let lastQuerySignature = '';
let lastRenderedSignature = ''; // 已渲染的 queryResult.features 数据签名（防止流式更新重复清空图层）
let lastLocalQuerySignature = ''; // 最近一次 executeEntityQuery 完成的查询签名（防止 AI 响应覆盖本地渲染结果）

function renderFromConfig(config: any) {
  if (!config || !map) return;

  const lng = config.queryParams?.lng ?? config.center?.[1] ?? queryCenter.value.lng;
  const lat = config.queryParams?.lat ?? config.center?.[0] ?? queryCenter.value.lat;
  const radius = config.queryParams?.radius ?? queryCenter.value.radius;
  const type = config.entityType || config.queryParams?.type || 'camera';
  entityType.value = type;
  const typeCfg = getEntityTypeConfig(type);

  // 更新查询中心点
  queryCenter.value = { lng, lat, radius };

  // ── 火情应急响应：优先级最高，需在 multiEntity / 本地查询去重守卫之前处理，避免被误拦截 ──
  if (config.fireResponse) {
    if (config.center) map.flyTo(config.center, config.zoom || DEFAULT_ZOOM, { duration: 1 });
    renderFireResponse(config).catch((e: any) => console.error('[CameraCanvasUI] renderFireResponse failed:', e));
    return;
  }

  // ── 多类型合并查询：需在本地查询去重守卫之前处理，避免被误判为重复查询而跳过 ──
  if (config.multiEntity && Array.isArray(config.entityGroups) && config.entityGroups.length > 0) {
    if (config.center) map.flyTo(config.center, config.zoom || DEFAULT_ZOOM, { duration: 1 });
    void renderMultiEntity(config);
    return;
  }

  // 如果 AI 响应的查询参数与最近一次本地 executeEntityQuery 相同，跳过渲染
  // （本地查询已渲染了圆圈、中心点和点位，不需要 AI 响应覆盖）
  const currentQuerySignature = `${lng},${lat},${radius},${type}`;
  if (lastLocalQuerySignature && currentQuerySignature === lastLocalQuerySignature) {
    console.log('[CameraCanvasUI] AI 响应与本地查询相同，跳过重复渲染:', currentQuerySignature);
    lastLocalQuerySignature = ''; // 重置，只跳过一次
    return;
  }

  // 如果有 center，飞到该位置
  if (config.center) {
    map.flyTo(config.center, config.zoom || DEFAULT_ZOOM, { duration: 1 });
  }

  // 如果有 queryResult.features，先验证数据质量再渲染
  // AI 模型可能在复述 tool 输出时丢失 fieldNames/fieldValues 等关键属性，
  // 导致摄像头名称和视频流无法获取。检测到不完整数据时回退到自己查询 SuperMap。
  const hasValidFeatures = config.queryResult?.features
    && config.queryResult.features.length > 0
    && config.queryResult.features.some((f: any) =>
      (f.fieldNames && f.fieldNames.length > 0) || (f.properties && Object.keys(f.properties).length > 0)
    );

  if (hasValidFeatures) {
    const features = config.queryResult.features;

    // 去重检查：如果已渲染过相同数据，跳过重复渲染（防止流式更新反复清空图层导致缩放时消失）
    const featureSignature = `${type}:${features.length}`;
    if (featureSignature === lastRenderedSignature) {
      console.log('[CameraCanvasUI] 数据未变化，跳过重复渲染:', featureSignature);
      return;
    }
    lastRenderedSignature = featureSignature;

    // 清除旧图层（含调度动画取消）
    cancelAllTrailAnimations();
    if (cameraLayer) cameraLayer.clearLayers();
    if (bufferLayer) bufferLayer.clearLayers();

    // 绘制缓冲区（颜色跟随实体类型）
    if (bufferLayer) {
      L.circle([lat, lng], {
        radius: radius,
        color: typeCfg.color,
        fillColor: typeCfg.color,
        fillOpacity: 0.15,
        weight: 2,
        dashArray: '8, 4'
      }).addTo(bufferLayer);
    }

    // Issue 4: 绘制查询中心点标记
    addQueryPointMarker(lat, lng);

    renderCameraFeatures(features, lng, lat, radius, type);

    // 自动适配视图以显示所有实体
    if (cameraLayer && cameraLayer.getLayers().length > 0) {
      const bounds = cameraLayer.getBounds();
      bounds.extend([lat, lng]);
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 15 });
    }

    showNotification(`已加载 ${features.length} 个${typeCfg.label}`, 'success');

    // 视图动画结束后主动刷新行政图层
    setTimeout(() => loadAdminLayers(), 800);
    return;
  }

  // 如果有 queryParams 但没有 features，自动执行查询（Issue 7: 防抖 + 去重）
  if (config.queryParams && (config.queryParams.lng || config.queryParams.lat)) {
    const signature = `${lng},${lat},${radius},${type}`;
    // 如果和上次查询完全相同，跳过（防止重复查询）
    if (signature === lastQuerySignature) return;

    // 清除之前的定时器（Issue 7: 防止多次快速触发）
    if (autoQueryTimer) {
      clearTimeout(autoQueryTimer);
      autoQueryTimer = null;
    }

    autoQueryTimer = setTimeout(() => {
      lastQuerySignature = signature;
      executeEntityQuery(lng, lat, radius, type);
    }, TIMEOUT_DELAY_MS);
    return;
  }
}

// ============ Watch Content ============
function tryRenderContent() {
  if (props.suspend) return;
  if (!props.content) return;
  if (!map) return;

  const config = parseMapConfig(props.content);
  if (config) {
    renderFromConfig(config);
    error.value = null;
  } else if (props.isComplete !== false) {
    error.value = '地图配置数据解析失败，请检查 JSON 格式';
  } else {
    error.value = null;
  }
}

watch(
  () => props.content,
  (_newContent, _oldContent) => {
    tryRenderContent();
  },
  { immediate: true }
);

watch(
  () => props.suspend,
  (suspended) => {
    if (suspended) {
      closeContextMenu();
      closeQueryDialog();
      if (videoModalVisible.value) {
        closeVideoModal();
      }
      return;
    }

    nextTick(() => {
      setTimeout(() => map?.invalidateSize(), MAP_INVALIDATE_DELAY_MS);
      tryRenderContent();
    });
  }
);

// ============ View Controls ============
function zoomIn() { map?.zoomIn(); }
function zoomOut() { map?.zoomOut(); }

function resetView() {
  map?.flyTo(DEFAULT_CENTER, DEFAULT_ZOOM, { duration: 1 });
}

function toggleFullScreen() {
  emit('toggle-fullscreen');
}


// ============ Keyboard Shortcuts ============
function handleKeyDown(e: KeyboardEvent) {
  const target = e.target as HTMLElement;
  if (['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName) || target.isContentEditable) return;

  switch (e.key) {
    case 'Escape':
      if (videoModalVisible.value) { closeVideoModal(); e.preventDefault(); break; }
      if (isFullScreen.value) { toggleFullScreen(); e.preventDefault(); }
      break;
    case '+': case '=':
      zoomIn(); e.preventDefault(); break;
    case '-':
      zoomOut(); e.preventDefault(); break;
    case 'r': case 'R':
      resetView(); e.preventDefault(); break;
  }
}

// ============ Lifecycle ============
onMounted(() => {
  delete (L.Icon.Default.prototype as any)._getIconUrl;
  L.Icon.Default.mergeOptions({
    iconRetinaUrl: markerIcon2xUrl,
    iconUrl: markerIconUrl,
    shadowUrl: markerShadowUrl,
  });

  initMap();
  tryRenderContent();

  if (wrapper.value) {
    resizeObserver = new ResizeObserver(() => {
      if (props.suspend) return;
      setTimeout(() => map?.invalidateSize(), MAP_INVALIDATE_DELAY_MS);
    });
    resizeObserver.observe(wrapper.value);
  }

  window.addEventListener('keydown', handleKeyDown);

  showInitToast.value = true;
  initToastMessage.value = '📹 正在初始化摄像头监控...';
  setTimeout(() => {
    showInitToast.value = false;
  }, INIT_TOAST_DELAY_MS);
});

onUnmounted(() => {
  isUnmounted = true;

  if (autoQueryTimer) {
    clearTimeout(autoQueryTimer);
    autoQueryTimer = null;
  }

  cancelAllTrailAnimations();
  closeVideoModal();

  if (map) {
    map.off('zoomend', onZoomEnd);
    map.off('click', onMapClick);
    map.off('contextmenu', openContextMenu);
    map.remove();
    map = null;
  }
  cameraLayer = null;
  cameraClusterLayer = null;
  cameraSpreadLayer = null;
  bufferLayer = null;
  villageLayer = null;
  districtLayer = null;

  resizeObserver?.disconnect();
  resizeObserver = null;

  window.removeEventListener('keydown', handleKeyDown);
});

// ============ Expose ============
defineExpose({
  fitToScreen: () => setTimeout(() => map?.invalidateSize(), MAP_INVALIDATE_DELAY_MS),
});
</script>

<style scoped>
.supermap-wrapper {
  width: 100%;
  height: 100%;
  position: absolute;
  top: 0;
  left: 0;
  overflow: hidden;
  background: #e8ecf0;
}

.map-container {
  width: 100%;
  height: 100%;
  z-index: 1;
}

/* ── 查询中心点标记 ── */
:deep(.query-point-marker) {
  background: transparent !important;
  border: none !important;
}

:deep(.fire-center-marker) {
  background: transparent !important;
  border: none !important;
}

:deep(.query-point-popup .leaflet-popup-content-wrapper) {
  border-radius: 10px;
}

/* ── 工具栏 ── */
.draw-toolbar {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 6px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  z-index: 1000;
  user-select: none;
}

.tool-group {
  display: flex;
  flex-direction: column;
  gap: 2px;
  align-items: center;
}

.tool-divider {
  width: 24px;
  height: 1px;
  background: rgba(0, 0, 0, 0.12);
  margin: 2px auto;
}

.tool-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  border-radius: 8px;
  color: #475569;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
}

.tool-btn:hover {
  background: rgba(250, 140, 22, 0.1);
  color: #1e293b;
}

.tool-btn:active {
  transform: scale(0.92);
}

/* ── 数据条数标签 ── */
.data-count-badge {
  position: absolute;
  bottom: 80px;
  right: 24px;
  z-index: 1000;
  background: rgba(250, 140, 22, 0.85);
  color: white;
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 12px;
  backdrop-filter: blur(4px);
  pointer-events: none;
  user-select: none;
}

/* ── 加载提示 ── */
.loading-toast {
  position: absolute;
  bottom: 130px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 999;
  background: rgba(0, 0, 0, 0.75);
  color: white;
  padding: 10px 24px;
  border-radius: 24px;
  font-size: 13px;
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  gap: 12px;
  pointer-events: none;
  user-select: none;
  transition: opacity 0.5s ease;
  opacity: 0;
}

.loading-toast.show {
  opacity: 1;
}

.loading-spinner-small {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
}

/* ── 初始化提示 ── */
.init-toast {
  position: absolute;
  bottom: 130px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 999;
  background: rgba(0, 0, 0, 0.75);
  color: white;
  padding: 8px 20px;
  border-radius: 24px;
  font-size: 13px;
  backdrop-filter: blur(8px);
  pointer-events: none;
  user-select: none;
  transition: opacity 0.8s ease;
  opacity: 0;
}

.init-toast.show {
  opacity: 1;
}

/* ── 错误面板 ── */
.error-panel {
  position: absolute;
  top: 16px;
  left: 16px;
  z-index: 1100;
  max-width: 380px;
  background-color: #fef2f2;
  border: 1px solid #fee2e2;
  border-radius: 8px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  overflow: hidden;
  transition: all 0.3s ease;
}

.error-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  gap: 12px;
  cursor: pointer;
  background-color: #fef2f2;
  user-select: none;
}

.error-header:hover {
  background-color: #fee2e2;
}

.error-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
  color: #ef4444;
}

.error-icon {
  flex-shrink: 0;
  opacity: 0.8;
}

.error-text-summary {
  font-size: 12px;
  font-family: monospace;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  color: #b91c1c;
  margin-top: 1px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #ef4444;
}

.chevron-icon {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  opacity: 0.6;
  width: 14px;
  height: 14px;
}

.chevron-icon.rotated {
  transform: rotate(180deg);
}

.error-details-wrapper {
  display: grid;
  grid-template-rows: 0fr;
  transition: grid-template-rows 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  background-color: #fff1f2;
}

.error-details-wrapper.expanded {
  grid-template-rows: 1fr;
}

.error-details-inner {
  overflow: hidden;
  border-top: 1px solid #fee2e2;
  min-height: 0;
}

.error-full-text {
  font-family: monospace;
  font-size: 11px;
  color: #991b1b;
  white-space: pre-wrap;
  word-break: break-all;
  line-height: 1.5;
  max-height: 200px;
  overflow-y: auto;
  padding: 10px;
}

/* ── 视频播放模态框 ── */
.video-modal-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.6);
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(4px);
}

.video-modal {
  width: 800px;
  max-width: 90%;
  background: #1a1a2e;
  border: 1px solid rgba(250, 140, 22, 0.4);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
}

.video-modal-header {
  padding: 12px 16px;
  background: linear-gradient(135deg, rgba(250, 140, 22, 0.2) 0%, rgba(212, 107, 8, 0.2) 100%);
  border-bottom: 1px solid rgba(250, 140, 22, 0.3);
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 15px;
  font-weight: bold;
  color: #fff;
}

.video-modal-close-btn {
  background: transparent;
  border: none;
  color: #fff;
  font-size: 16px;
  cursor: pointer;
  transition: color 0.3s;
  padding: 4px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.video-modal-close-btn:hover {
  color: #ff4d4f;
  background: rgba(255, 77, 79, 0.1);
}

.video-modal-body {
  position: relative;
  height: 450px;
  background: #000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.video-loading {
  position: absolute;
  color: #fa8c16;
  font-size: 14px;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 8px;
}

.h5player-container {
  width: 100%;
  height: 100%;
}

/* ── Leaflet 覆盖 ── */
:deep(.leaflet-popup-content-wrapper) {
  border-radius: 10px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
}

:deep(.leaflet-popup-content) {
  margin: 10px 14px;
  font-size: 13px;
  line-height: 1.5;
}

:deep(.leaflet-control-attribution) {
  display: none;
}

/* ── 行政图层标签 ── */
:deep(.district-label),
:deep(.village-label) {
  background: transparent !important;
  border: none !important;
}

/* ── Animations ── */
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* ── 右键上下文菜单 ── */
.map-context-menu {
  position: absolute;
  z-index: 2000;
  background: rgba(255, 255, 255, 0.97);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 10px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.18);
  padding: 6px 0;
  min-width: 210px;
  animation: contextMenuFadeIn 0.15s ease-out;
}

@keyframes contextMenuFadeIn {
  from { opacity: 0; transform: scale(0.95) translateY(-4px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

.context-menu-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 8px 6px 14px;
  font-size: 11px;
  color: #888;
  font-family: 'SF Mono', 'Fira Code', monospace;
}

.context-menu-coord {
  flex: 1;
  min-width: 0;
}

.context-menu-close {
  flex-shrink: 0;
  background: none;
  border: none;
  color: #999;
  font-size: 13px;
  line-height: 1;
  cursor: pointer;
  padding: 3px 5px;
  border-radius: 4px;
  transition: all 0.2s;
}

.context-menu-close:hover {
  background: rgba(220, 38, 38, 0.12);
  color: #dc2626;
}

.context-menu-divider {
  height: 1px;
  background: rgba(0, 0, 0, 0.08);
  margin: 4px 10px;
}

.context-menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 14px;
  cursor: pointer;
  transition: background 0.15s ease;
  font-size: 13px;
  color: #333;
  user-select: none;
}

.context-menu-item:hover {
  background: rgba(250, 140, 22, 0.12);
  color: #d46b08;
}

.context-menu-icon {
  font-size: 16px;
  width: 20px;
  text-align: center;
  flex-shrink: 0;
}

.context-menu-label {
  flex: 1;
  white-space: nowrap;
}

/* ── 查询对话框 ── */
.map-query-dialog-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.45);
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(3px);
}

.map-query-dialog {
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.25);
  width: 400px;
  max-width: 92%;
  overflow: hidden;
  animation: dialogSlideIn 0.25s ease-out;
}

@keyframes dialogSlideIn {
  from { opacity: 0; transform: translateY(20px) scale(0.97); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.query-dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  background: linear-gradient(135deg, #fa8c16 0%, #d46b08 100%);
  color: #fff;
  font-size: 15px;
  font-weight: 600;
}

.query-dialog-close {
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.8);
  font-size: 16px;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
  transition: all 0.2s;
}

.query-dialog-close:hover {
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
}

.query-dialog-body {
  padding: 18px;
}

.query-field {
  margin-bottom: 16px;
}

.query-field:last-child {
  margin-bottom: 0;
}

.query-field label {
  display: block;
  font-size: 13px;
  color: #555;
  margin-bottom: 6px;
  font-weight: 500;
}

.query-field label strong {
  color: #fa8c16;
}

.query-coord-display {
  background: #f7f8fa;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 12px;
  color: #555;
  font-family: 'SF Mono', 'Fira Code', monospace;
  border: 1px solid #e8e8e8;
}

.query-radius-control {
  display: flex;
  align-items: center;
  gap: 12px;
}

.query-radius-control input[type="range"] {
  flex: 1;
  height: 6px;
  -webkit-appearance: none;
  appearance: none;
  background: #e8e8e8;
  border-radius: 3px;
  outline: none;
}

.query-radius-control input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #fa8c16;
  cursor: pointer;
  border: 2px solid #fff;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
}

.query-radius-control input[type="number"] {
  width: 80px;
  padding: 6px 8px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 13px;
  text-align: center;
  outline: none;
  transition: border-color 0.2s;
}

.query-radius-control input[type="number"]:focus {
  border-color: #fa8c16;
  box-shadow: 0 0 0 2px rgba(250, 140, 22, 0.15);
}

.query-field textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 13px;
  resize: vertical;
  min-height: 70px;
  outline: none;
  font-family: inherit;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.query-field textarea:focus {
  border-color: #fa8c16;
  box-shadow: 0 0 0 2px rgba(250, 140, 22, 0.15);
}

.query-dialog-footer {
  display: flex;
  gap: 10px;
  padding: 14px 18px;
  border-top: 1px solid #f0f0f0;
  justify-content: flex-end;
}

.query-btn {
  padding: 9px 20px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  transition: all 0.2s;
}

.query-btn-cancel {
  background: #f5f5f5;
  color: #666;
}

.query-btn-cancel:hover {
  background: #e8e8e8;
}

.query-btn-confirm {
  background: linear-gradient(135deg, #fa8c16 0%, #d46b08 100%);
  color: #fff;
  box-shadow: 0 2px 8px rgba(250, 140, 22, 0.3);
}

.query-btn-confirm:hover {
  box-shadow: 0 4px 12px rgba(250, 140, 22, 0.4);
  transform: translateY(-1px);
}

/* ── Responsive ── */
@media (max-width: 768px) {
  .draw-toolbar {
    left: 8px;
    padding: 4px;
  }
  .tool-btn {
    width: 32px;
    height: 32px;
  }
  .video-modal {
    max-width: 95%;
  }
  .video-modal-body {
    height: 300px;
  }
}
/* ── 无人机飞行目的地设置面板（地图点选 / 输入坐标） ── */
.uav-pick-panel {
  position: absolute;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1000;
  width: 330px;
  max-width: calc(100% - 32px);
  padding: 10px 14px 12px;
  background: rgba(250, 140, 22, 0.96);
  color: #fff;
  border-radius: 10px;
  box-shadow: 0 4px 16px rgba(250, 140, 22, 0.4);
  font-size: 13px;
}

.uav-pick-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.uav-pick-title {
  flex: 1;
  font-weight: 600;
  white-space: nowrap;
}

.uav-pick-dot {
  flex-shrink: 0;
  width: 10px;
  height: 10px;
  background: #fff;
  border-radius: 50%;
  animation: uavPickBlink 1s ease-in-out infinite;
}

@keyframes uavPickBlink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.2; }
}

.uav-pick-tabs {
  display: flex;
  gap: 6px;
  margin: 10px 0 8px;
}

.uav-pick-tab {
  flex: 1;
  padding: 5px 0;
  background: rgba(255, 255, 255, 0.18);
  color: #fff;
  border: 1px solid rgba(255, 255, 255, 0.35);
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
}

.uav-pick-tab.active {
  background: #fff;
  color: #fa8c16;
  font-weight: 700;
  border-color: #fff;
}

.uav-pick-hint {
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.95);
}

.uav-pick-fields {
  display: flex;
  gap: 8px;
}

.uav-pick-field {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 3px;
  font-size: 12px;
}

.uav-pick-field input {
  width: 100%;
  padding: 5px 8px;
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: 6px;
  background: #fff;
  color: #1a202c;
  font-size: 12px;
  box-sizing: border-box;
}

.uav-pick-field input:focus {
  outline: none;
  border-color: #fff;
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.4);
}

.uav-pick-range {
  margin-top: 6px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.8);
}

.uav-pick-error {
  margin-top: 6px;
  padding: 4px 8px;
  background: rgba(220, 38, 38, 0.9);
  border-radius: 5px;
  font-size: 11px;
}

.uav-pick-actions {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

.uav-pick-btn {
  flex: 1;
  padding: 6px 0;
  border: 1px solid transparent;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
}

.uav-pick-btn.ghost {
  background: rgba(255, 255, 255, 0.18);
  color: #fff;
  border-color: rgba(255, 255, 255, 0.6);
}

.uav-pick-btn.primary {
  background: #fff;
  color: #fa8c16;
}

.uav-pick-btn:hover {
  filter: brightness(1.06);
}

.uav-pick-cancel {
  flex-shrink: 0;
  padding: 3px 10px;
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
  border: 1px solid rgba(255, 255, 255, 0.6);
  border-radius: 5px;
  cursor: pointer;
  font-size: 12px;
}

.uav-pick-cancel:hover {
  background: rgba(255, 255, 255, 0.35);
}

/* 地图容器十字光标（选点模式） */
.map-container.uav-pick-cursor {
  cursor: crosshair !important;
}
</style>

<style>
/* 全局（非 scoped）keyframes：Leaflet divIcon 内联 HTML 中的动画引用不会被 scoped 编译器改名，必须放全局块 */
@keyframes query-point-pulse {
  0%, 100% { transform: scale(1); opacity: 0.6; }
  50% { transform: scale(1.8); opacity: 0; }
}
</style>
