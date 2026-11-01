export interface RuntimeConfig {
  API_BASE_URL: string;
  COPYRIGHT?: string;
  SYSTEM_NAME?: string;
  APP_VERSION?: string;
  FILE_UPLOAD_MAX_SIZE?: number;
  KB_UPLOAD_DEFAULT_CHUNK_SIZE?: number;
  ASR_SERVER?: string;
  TTS_SERVER?: string;
  KB_EMBEDDING_MODELS?: string[];
  KB_VECTOR_STORE_TYPES?: string[];
  DEFAULT_USER_GROUP_IDS?: string[];
  MAP_SERVICE_URL?: string;
  MAP_CHINA_URL?: string;
  MAP_BOUNDARY_URL?: string;
  MAP_SHANXI_URL?: string;
  MAP_DATA_URL?: string;
  MAP_QINLING_DATA_URL?: string;
  MAP_NETWORK_ANALYST_URL?: string;
  MAP_VIDEO_STREAM_API?: string;
}

const defaultConfig: RuntimeConfig = {
  API_BASE_URL: "",
  COPYRIGHT: "",
  SYSTEM_NAME: "",
  APP_VERSION: "1.0.0",
  FILE_UPLOAD_MAX_SIZE: 10,
  KB_UPLOAD_DEFAULT_CHUNK_SIZE: 500,
  ASR_SERVER: "ws://localhost:10095/",
  TTS_SERVER: "ws://localhost:8778",
  KB_EMBEDDING_MODELS: ["Qwen/Qwen3-Embedding-4B"],
  KB_VECTOR_STORE_TYPES: ["milvus", "hippo"],
  DEFAULT_USER_GROUP_IDS: [],
  MAP_SERVICE_URL: "http://172.16.235.50:18090/iserver/services/map-ugcv5-wj_gis_chinaworld_img/rest/maps/world_image",
  MAP_CHINA_URL: "http://172.16.235.50:18090/iserver/services/map-ugcv5-wj_gis_china_img/rest/maps/china_image",
  MAP_BOUNDARY_URL: "http://172.16.235.50:18090/iserver/services/map-wj_gis_ZhongGuo_XingZhengJingJie/rest/maps/wj_gis_中国_行政境界",
  MAP_SHANXI_URL: "http://172.16.235.50:18090/iserver/services/map-ugcv5-wj_gis_YingXiang_ShanXi3/rest/maps/wj_gis_%E5%BD%B1%E5%83%8F_%E9%99%95%E8%A5%BF",
  MAP_DATA_URL: "http://172.16.235.50:18090/iserver/services/data-ShiLiangShuJu/rest/data",
  MAP_QINLING_DATA_URL: "http://172.16.235.50:18090/iserver/services/data-qinling/rest/data",
  MAP_NETWORK_ANALYST_URL: "http://172.16.235.50:18090/iserver/services/transportationAnalyst-ShiLiangShuJu/rest/networkanalyst/道路@矢量数据4490",
  MAP_VIDEO_STREAM_API: "http://10.17.49.196:36003/jeecg-boot/camera/newCameraInfo/getCameraUrl",
};

let runtimeConfig: RuntimeConfig = { ...defaultConfig };

export async function loadRuntimeConfig(): Promise<void> {
  try {
    // 兼容子路径部署：使用 BASE_URL 作为前缀查找配置文件
    const base = (((import.meta as any)?.env?.BASE_URL) || "/").replace(/\/+$|^$/, "/");
    const configUrl = `${base}runtime-config.json`;
    const res = await fetch(configUrl, { cache: "no-store" });
    if (res.ok) {
      const data = (await res.json()) as Partial<RuntimeConfig>;
      runtimeConfig = { ...defaultConfig, ...data };
    }
  } catch (err) {
    runtimeConfig = { ...defaultConfig };
    if (typeof window !== 'undefined') {
      console.warn('[RuntimeConfig] 加载失败，使用默认配置');
    }
  }
}

export function getRuntimeConfig(): RuntimeConfig {
  return runtimeConfig;
}

export function getApiBaseUrl(): string {
  const val = runtimeConfig.API_BASE_URL ?? "";
  return val.trim();
}

export function getCopyright(): string {
  const val = runtimeConfig.COPYRIGHT ?? "";
  return val.trim();
}

export function getSystemName(): string {
  const val = runtimeConfig.SYSTEM_NAME ?? "";
  return val.trim();
}

export function getAppVersion(): string {
  const val = runtimeConfig.APP_VERSION ?? "";
  return val.trim();
}

export function getFileUploadMaxSize(): number {
  return runtimeConfig.FILE_UPLOAD_MAX_SIZE ?? 10;
}

export function getKbUploadDefaultChunkSize(): number {
  const value = Number(runtimeConfig.KB_UPLOAD_DEFAULT_CHUNK_SIZE);
  if (!Number.isFinite(value) || value < 1) {
    return 500;
  }
  return Math.floor(value);
}

export function getAsrServer(): string {
  const val = runtimeConfig.ASR_SERVER ?? "";
  return val.trim();
}

export function getTtsServer(): string {
  const val = runtimeConfig.TTS_SERVER ?? "";
  return val.trim();
}

export function getKbEmbeddingModels(): string[] {
  const list = runtimeConfig.KB_EMBEDDING_MODELS ?? [];
  return list.map(item => String(item).trim()).filter(item => item.length > 0);
}

export function getKbVectorStoreTypes(): string[] {
  const list = runtimeConfig.KB_VECTOR_STORE_TYPES ?? [];
  return list.map(item => String(item).trim()).filter(item => item.length > 0);
}

export function getDefaultUserGroupIds(): string[] {
  const list = runtimeConfig.DEFAULT_USER_GROUP_IDS ?? [];
  return list.map(item => String(item).trim()).filter(item => item.length > 0);
}

export function getMapServiceUrl(): string {
  const val = runtimeConfig.MAP_SERVICE_URL ?? "";
  return val.trim();
}

export function getChinaMapServiceUrl(): string {
  const val = runtimeConfig.MAP_CHINA_URL ?? "";
  return val.trim();
}

export function getBoundaryMapServiceUrl(): string {
  const val = runtimeConfig.MAP_BOUNDARY_URL ?? "";
  return val.trim();
}

export function getShanxiMapServiceUrl(): string {
  const val = runtimeConfig.MAP_SHANXI_URL ?? "";
  return val.trim();
}

export function getMapDataUrl(): string {
  const val = runtimeConfig.MAP_DATA_URL ?? "";
  return val.trim();
}

export function getQinlingMapDataUrl(): string {
  const val = runtimeConfig.MAP_QINLING_DATA_URL ?? "";
  return val.trim();
}

export function getMapNetworkAnalystUrl(): string {
  const val = runtimeConfig.MAP_NETWORK_ANALYST_URL ?? "";
  return val.trim();
}

export function getMapVideoStreamApi(): string {
  const val = runtimeConfig.MAP_VIDEO_STREAM_API ?? "";
  return val.trim();
}
