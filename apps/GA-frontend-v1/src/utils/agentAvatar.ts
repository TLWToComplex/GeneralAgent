import defaultAgentAvatar from '@/assets/image/png/angent-bg.png';

// 智能体头像的「稳定标识」与「渲染值」解耦：
// - 预设头像通过 import.meta.glob 的 ?inline 内联为 base64 data URL，
//   作为内置资源随 JS 打包，与 dev / Docker 构建环境的文件路径彻底无关，
//   也不会因中文文件名在静态服务器下被 percent-encoding 导致 404（模型 icon 同理，均为代码内嵌）。
// - 数据库里持久化稳定 key（预设头像为相对路径，如 linear/蓝1.png；默认头像为 default），
//   而不是 base64 本体，避免列表接口返回海量 base64 字符串。
// - 渲染时用 resolveAgentAvatar() 把持久化 key 映射回内联 data URL。
// - 写库时用 agentAvatarToKey() 把前端当前值（base64 / 路径）归一化回稳定 key，并向后兼容老数据。

const AVATAR_DIR = 'agent-avatars/';
const DEFAULT_AGENT_AVATAR_KEY = 'default';
// dev 环境下静态资源导入返回的原始路径，用于向后兼容历史已入库的默认头像
const DEFAULT_AGENT_AVATAR_DEV_PATH = '/src/assets/image/png/angent-bg.png';

/** 预设头像资源：文件路径 -> 内联 data URL（环境无关） */
export const avatarFiles = import.meta.glob<string>('/src/assets/agent-avatars/**/*.{svg,png}', {
  eager: true,
  query: '?inline',
  import: 'default',
});

// 稳定 key（如 linear/蓝1.png）-> 内联 data URL
const urlByKey = new Map<string, string>();
// base64 内联值 / 文件路径 -> 稳定 key
const keyByUrl = new Map<string, string>();

for (const [file, url] of Object.entries(avatarFiles)) {
  const normalized = file.replace(/^\/+/, '');
  const idx = normalized.indexOf(AVATAR_DIR);
  const key = idx >= 0 ? normalized.slice(idx + AVATAR_DIR.length) : normalized;
  urlByKey.set(key, url);
  keyByUrl.set(file, key);
  keyByUrl.set('/' + normalized, key);
  keyByUrl.set(url, key);
}

// 默认头像同样纳入映射，避免其 URL 随构建环境改变
urlByKey.set(DEFAULT_AGENT_AVATAR_KEY, defaultAgentAvatar);
keyByUrl.set(defaultAgentAvatar, DEFAULT_AGENT_AVATAR_KEY);
keyByUrl.set(DEFAULT_AGENT_AVATAR_DEV_PATH, DEFAULT_AGENT_AVATAR_KEY);

// 上传的自定义头像为压缩后的 dataURL，或外链图片，均无需映射
const isExternalImage = (value: string) => /^(data:|https?:|blob:|file:)/i.test(value);

/** 把持久化值解析为可直接渲染的值（预设头像返回内联 data URL） */
export function resolveAgentAvatar(value?: string | null): string {
  if (!value) return '';
  if (isExternalImage(value)) return value;
  const key = keyByUrl.get(value) ?? value;
  return urlByKey.get(key) ?? value;
}

/** 把前端当前使用的 URL 归一化成语义稳定的 key，供持久化 */
export function agentAvatarToKey(value?: string | null): string {
  if (!value) return '';
  // 优先匹配预设头像（可为 base64 内联值 / dev 路径 / 打包路径），命中则归一化为稳定 key
  const known = keyByUrl.get(value);
  if (known) return known;
  // 上传的自定义头像（base64）或外链图片直接透传，不参与 key 归一化
  if (isExternalImage(value)) return value;
  return value;
}