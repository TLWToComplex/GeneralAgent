import { httpKb } from '@/utils/http'
import { replaceServerUrlPlaceholders } from '@/utils/serverUrl'

// 远端返回的数据结构
export interface RemoteKnowledgeBaseItem {
  id: number
  kb_name: string
  kb_uuid?: string
  uuid?: string
  kb_info: string
  permission_code?: string
  permission_group_ids?: string[]
  permissionGroupIds?: string[]
  vs_type: string
  embed_model: string
  file_count: number
  create_time: string
  include_kg: boolean
}

export interface RemoteKnowledgeBaseListResponse {
  code: number
  msg: string
  data: RemoteKnowledgeBaseItem[]
}

export interface RemoteCreateKnowledgeBaseResponse {
  code: number
  msg: string
  data?: any
  uuid?: string
}

export interface RemoteCommonResponse {
  code: number
  msg: string
  data?: any
}

// 列出知识库文件的远端结构
export interface RemoteFileItem {
  kb_name: string
  file_name: string
  file_ext: string
  file_version: number
  document_loader: string
  docs_count: number
  text_splitter: string
  create_time: string
  in_folder: boolean
  in_db: boolean
  file_mtime: number
  file_size: number
  custom_docs: boolean
  No: number
  graph_status?: {
    completed: boolean
    error_msg: string
  }
}

export interface RemoteListFilesResponse {
  code: number
  msg: string
  data: RemoteFileItem[]
}

// 视图层使用的数据结构（与 KnowledgeBaseView.vue 中一致）
export interface KnowledgeBaseVM {
  id: string
  kbUuid?: string
  name: string
  description?: string
  permissionCode?: KnowledgeBasePermissionCode
  permissionGroupIds?: string[]
  documentCount: number
  updatedAt: Date
  vsType?: string
  embedModel?: string
  includeKg?: boolean
  documents: Array<{
    id: string
    name: string
    size: number
    uploadedAt: Date
  }>
}

function normalizePermissionCode(permissionCode?: string): KnowledgeBasePermissionCode | undefined {
  if (permissionCode === 'public') return 'public'
  if (permissionCode === 'private') return 'private'
  return undefined
}

function mapRemoteToVM(item: RemoteKnowledgeBaseItem): KnowledgeBaseVM {
  const permissionGroupIds = Array.from(
    new Set(
      (Array.isArray(item.permission_group_ids)
        ? item.permission_group_ids
        : Array.isArray(item.permissionGroupIds)
          ? item.permissionGroupIds
          : []
      ).filter((groupId): groupId is string => typeof groupId === 'string' && groupId.trim().length > 0)
    )
  )
  return {
    id: String(item.id),
    kbUuid: String(item.kb_uuid || item.uuid || '').trim() || undefined,
    name: item.kb_name,
    description: item.kb_info,
    permissionCode: normalizePermissionCode(item.permission_code),
    permissionGroupIds,
    documentCount: item.file_count ?? 0,
    updatedAt: new Date(item.create_time),
    vsType: item.vs_type,
    embedModel: item.embed_model,
    includeKg: item.include_kg,
    documents: []
  }
}

// 获取知识库列表（统一走 API_BASE_URL 转发）
export type KnowledgeBasePermissionCode = 'private' | 'public'

export async function listKnowledgeBases(permission_code?: KnowledgeBasePermissionCode): Promise<KnowledgeBaseVM[]> {
  const res = await httpKb.get<RemoteKnowledgeBaseListResponse>('/kb_chat/knowledge_base/list_knowledge_bases', {
    params: permission_code ? { permission_code } : undefined
  })
  if (res.data.code !== 200) {
    throw new Error(res.data.msg || '知识库列表获取失败')
  }
  return (res.data.data || []).map(mapRemoteToVM)
}

// 创建知识库
export interface CreateKnowledgeBasePayload {
  knowledge_base_name: string
  vector_store_type: string
  kb_info: string
  embed_model: string
  permission_code?: string
  permission_group_ids?: string[]
  permissionGroupIds?: string[]
  enable_graph_rag?: boolean
  kb_type?: string
  kg_type?: string
  allowed_nodes?: string[]
  allowed_relationships?: string[]
  node_properties?: boolean
}

export async function createKnowledgeBase(payload: CreateKnowledgeBasePayload): Promise<RemoteCreateKnowledgeBaseResponse> {
  const res = await httpKb.post<RemoteCreateKnowledgeBaseResponse>('/kb_chat/knowledge_base/create_knowledge_base', payload)
  if (res.data.code !== 200) {
    throw new Error(res.data.msg || '创建知识库失败')
  }
  return res.data
}

// 更新知识库信息
export interface UpdateKnowledgeBaseInfoPayload {
  knowledge_base_name: string
  kb_info: string
  new_kb_name?: string
  new_permission_code?: string
  permission_group_ids?: string[]
  permissionGroupIds?: string[]
  enable_graph_rag?: boolean
}

export async function updateKnowledgeBaseInfo(payload: UpdateKnowledgeBaseInfoPayload): Promise<RemoteCommonResponse> {
  const res = await httpKb.post<RemoteCommonResponse>('/kb_chat/knowledge_base/update_info', payload)
  if (res.data.code !== 200) {
    throw new Error(res.data.msg || '更新知识库信息失败')
  }
  return res.data
}

// 删除知识库（统一走 API_BASE_URL 转发）
export async function deleteKnowledgeBase(name: string, enable_graph_rag?: boolean): Promise<RemoteCommonResponse> {
  const body = {
    payload: {
      knowledge_base_name: name
    },
    enable_graph_rag: enable_graph_rag ?? false
  }
  const res = await httpKb.post<RemoteCommonResponse>('/kb_chat/knowledge_base/delete_knowledge_base', body)
  if (res.data.code !== 200) {
    throw new Error(res.data.msg || '删除知识库失败')
  }
  return res.data
}

// 获取指定知识库的文件列表（统一走 API_BASE_URL 转发）
export interface KnowledgeBaseFileVM {
  id: string
  name: string
  size: number
  uploadedAt: Date
  ext?: string
  version?: number
  loader?: string
  docsCount?: number
  splitter?: string
  inFolder?: boolean
  inDb?: boolean
  mtime?: number
  customDocs?: boolean
  no?: number
  graphStatus?: {
    completed: boolean
    errorMsg: string
  }
}

export async function listKnowledgeBaseFiles(knowledgeBaseName: string): Promise<KnowledgeBaseFileVM[]> {
  const res = await httpKb.get<RemoteListFilesResponse>('/kb_chat/knowledge_base/list_files', {
    params: { knowledge_base_name: knowledgeBaseName }
  })
  if (res.data.code !== 200) {
    throw new Error(res.data.msg || '获取文件列表失败')
  }
  const items = res.data.data || []
  return items.map((item) => ({
    id: item.file_name,
    name: item.file_name,
    size: item.file_size,
    uploadedAt: new Date(item.create_time),
    ext: item.file_ext,
    version: item.file_version,
    loader: item.document_loader,
    docsCount: item.docs_count,
    splitter: item.text_splitter,
    inFolder: item.in_folder,
    inDb: item.in_db,
    mtime: item.file_mtime,
    customDocs: item.custom_docs,
    no: item.No,
    graphStatus: item.graph_status ? {
      completed: item.graph_status.completed,
      errorMsg: item.graph_status.error_msg
    } : undefined
  }))
}

// 上传文档到知识库（统一走 API_BASE_URL 转发）
export interface UploadKnowledgeBaseDocsPayload {
  knowledge_base_name: string
  files: File[]
  chunk_size: number
  chunk_overlap: number
  zh_title_enhance?: boolean
  override?: boolean // 默认 false
  to_vector_store?: boolean // 默认 true
  not_refresh_vs_cache?: boolean // 默认 false
  enable_graph_rag?: boolean
  classification?: 'public' | 'internal' // 文档密级
  // docs?: 未使用，按照后端说明留空或不传
}

export interface UploadDocsResponseData {
  success_files?: string[]
  failed_files?: Record<string, string>
}

export interface RemoteUploadDocsResponse {
  code: number
  msg: string
  data?: UploadDocsResponseData
}

export class UploadDocsError extends Error {
  code: number
  data?: UploadDocsResponseData

  constructor(message: string, code: number, data?: UploadDocsResponseData) {
    super(message)
    this.name = 'UploadDocsError'
    this.code = code
    this.data = data
  }
}

export async function uploadKnowledgeBaseDocs(payload: UploadKnowledgeBaseDocsPayload): Promise<RemoteUploadDocsResponse> {
  const formData = new FormData();
  // 文件
  const files: File[] = payload.files ?? [];
  files.forEach((file: File) => {
    formData.append('files', file, file.name);
  });
  // 必填与配置项
  formData.append('knowledge_base_name', payload.knowledge_base_name);
  formData.append('chunk_size', String(payload.chunk_size));
  formData.append('chunk_overlap', String(payload.chunk_overlap));
  formData.append('zh_title_enhance', payload.zh_title_enhance ? 'true' : 'false');
  // 固定或默认值
  formData.append('override', String(payload.override ?? false));
  formData.append('to_vector_store', String(payload.to_vector_store ?? true));
  formData.append('not_refresh_vs_cache', String(payload.not_refresh_vs_cache ?? false));
  if (payload.enable_graph_rag !== undefined) {
    formData.append('enable_graph_rag', String(payload.enable_graph_rag));
  }
  if (payload.classification) {
    formData.append('classification', payload.classification);
  }
  // docs 不传

  // 避免泛型调用在某些编译路径下被误解析，直接调用并按返回结构处理
  try {
    const res = await httpKb.postForm('/kb_chat/knowledge_base/upload_docs', formData, {
      timeout: 600000
    })
    if (res.data.code !== 200) {
      throw new UploadDocsError(res.data.msg || '上传文档失败', res.data.code, res.data.data)
    }
    return res.data as RemoteUploadDocsResponse
  } catch (error: any) {
    if (error instanceof UploadDocsError) {
      throw error
    }
    const payload = error?.response?.data as RemoteUploadDocsResponse | undefined
    if (payload && typeof payload.code === 'number') {
      throw new UploadDocsError(payload.msg || '上传文档失败', payload.code, payload.data)
    }
    throw error
  }
}

// 获取知识图谱任务状态
export interface KnowledgeGraphTaskStatus {
  file_name: string
  progress: number
  message: string
  status: string
  timestamp: string
  task_id?: string
}

export async function getKnowledgeGraphTaskStatus(knowledge_base_name: string, task_id: string): Promise<KnowledgeGraphTaskStatus> {
  const res = await httpKb.get<{code: number, msg: string, data: KnowledgeGraphTaskStatus}>('/kb_chat/knowledge_base/get_knowledge_graph_task_status', {
    params: {
      knowledge_base_name,
      task_id
    }
  })
  if (res.data.code !== 200) {
    throw new Error(res.data.msg || '获取知识图谱任务状态失败')
  }
  return res.data.data
}

// 获取所有知识图谱任务列表
export async function listAllKnowledgeGraphTask(knowledge_base_name: string): Promise<KnowledgeGraphTaskStatus[]> {
  const res = await httpKb.get<{code: number, msg: string, data: KnowledgeGraphTaskStatus[]}>('/kb_chat/knowledge_base/list_all_knowledge_graph_task', {
    params: {
      knowledge_base_name
    }
  })
  if (res.data.code !== 200) {
    throw new Error(res.data.msg || '获取所有知识图谱任务列表失败')
  }
  return res.data.data
}

export interface ShowGraphPayload {
  knowledge_base_name: string
  graph_size?: number
}

// 获取知识图谱数据
export async function showKnowledgeBaseGraph(payload: ShowGraphPayload): Promise<any> {
  const res = await httpKb.post<any>('/kb_chat/knowledge_base/show_knowledge_base_graph', payload)
  if (Array.isArray(res.data)) {
    return res.data
  }
  if (res.data && res.data.code !== 200) {
    throw new Error(res.data.msg || '获取知识图谱失败')
  }
  return res.data.data
}

// 删除知识库中的文档（统一走 API_BASE_URL 转发）
export interface DeleteKnowledgeBaseDocsPayload {
  knowledge_base_name: string
  file_names: string[]
  delete_content?: boolean // 默认 true
  not_refresh_vs_cache?: boolean // 默认 false
  force_delete?: boolean
  enable_graph_rag?: boolean
}

export async function deleteKnowledgeBaseDocs(payload: DeleteKnowledgeBaseDocsPayload): Promise<RemoteCommonResponse> {
  const res = await httpKb.post<RemoteCommonResponse>('/kb_chat/knowledge_base/delete_docs', {
    knowledge_base_name: payload.knowledge_base_name,
    file_names: payload.file_names,
    delete_content: payload.delete_content ?? true,
    not_refresh_vs_cache: payload.not_refresh_vs_cache ?? false,
    force_delete: payload.force_delete ?? false,
    enable_graph_rag: payload.enable_graph_rag ?? false
  })
  if (res.data.code !== 200) {
    throw new Error(res.data.msg || '删除文档失败')
  }
  return res.data
}

// 查询指定文档的切片内容（统一走 API_BASE_URL 转发）
export interface SearchDocsPayload {
  /** 聊天检索时复用当前会话和轮次；文档切片查看无需提供 */
  session_thread_id?: string
  turn_id?: string
  /** 用户查询内容（可选，用于通用搜索；未提供时后端可按文件名返回切片） */
  query?: string
  /** 知识库名称，支持单个或多个 */
  knowledge_base_name: string | string[]
  /** 返回TopK数量（可选，默认3） */
  top_k?: number
  /** 相关性分数阈值（可选，默认0.3） */
  score_threshold?: number
  /** 仅限定在某个文件内搜索（可选） */
  file_name?: string
  /** 额外过滤或提示元数据（可选） */
  metadata?: Record<string, any>
  /** 是否启用重排（可选） */
  enable_rerank?: boolean
  /** 图谱本地检索TopK（可选） */
  graph_local_search_top_k?: number
  /** 图谱全局检索TopK（可选） */
  graph_global_search_top_k?: number
}

export interface SearchDocSliceItem {
  page_content: string
  metadata?: {
    source?: string
    pk?: number | string
    [key: string]: any
  }
  type?: string
  id?: string
  score?: number
  /** 原始文件路径，可用于 Canvas 预览 */
  file_path?: string
}

export async function searchKnowledgeBaseDocs(payload: SearchDocsPayload): Promise<SearchDocSliceItem[]> {
  // 后端该接口返回为数组，不包含通用 {code,msg,data} 包装
  const body = {
    ...(payload.session_thread_id ? { session_thread_id: payload.session_thread_id } : {}),
    ...(payload.turn_id ? { turn_id: payload.turn_id } : {}),
    query: payload.query ?? '',
    knowledge_base_name: Array.isArray(payload.knowledge_base_name) ? payload.knowledge_base_name : [payload.knowledge_base_name],
    top_k: payload.top_k ?? 3,
    score_threshold: payload.score_threshold ?? 0.1,
    file_name: payload.file_name ?? '',
    metadata: payload.metadata ?? {},
    enable_rerank: payload.enable_rerank ?? true,
    graph_local_search_top_k: payload.graph_local_search_top_k ?? 3,
    graph_global_search_top_k: payload.graph_global_search_top_k ?? 5
  }
  const res = await httpKb.post<SearchDocSliceItem[]>('/kb_chat/knowledge_base/search_docs', body, { timeout: 0 })
  const data = res.data as unknown
  if (!Array.isArray(data)) {
    throw new Error('切片查询返回格式异常')
  }
  return replaceServerUrlPlaceholders(data as SearchDocSliceItem[])
}

// 更新指定文件的文档切片内容（统一走 API_BASE_URL 转发）
export interface UpdateKnowledgeBaseDocsPayload {
  knowledge_base_name: string
  file_names: string[]
  override_custom_docs?: boolean // 默认 false
  chunk_size?: number // 默认 750（与旧版保持一致）
  chunk_overlap?: number // 默认 150（与旧版保持一致）
  zh_title_enhance?: boolean // 默认 false
  /**
   * docs 为后端要求的字符串化JSON，形如：
   * { "fileName": [{ page_content, type, metadata }, ...] }
   * 这里允许传入对象，内部将自动 stringify
   */
  docs: string | Record<string, any>
}

export async function updateKnowledgeBaseDocs(payload: UpdateKnowledgeBaseDocsPayload): Promise<RemoteCommonResponse> {
  const body = {
    knowledge_base_name: payload.knowledge_base_name,
    file_names: payload.file_names,
    override_custom_docs: payload.override_custom_docs ?? false,
    chunk_size: payload.chunk_size ?? 750,
    chunk_overlap: payload.chunk_overlap ?? 150,
    zh_title_enhance: payload.zh_title_enhance ?? false,
    docs: typeof payload.docs === 'string' ? payload.docs : JSON.stringify(payload.docs)
  }
  const res = await httpKb.post<RemoteCommonResponse>('/kb_chat/knowledge_base/update_docs', body, { timeout: 600000 })
  if (res.data.code !== 200) {
    throw new Error(res.data.msg || '更新文档切片失败')
  }
  return res.data
}

// 下载指定文档原文件（统一走 API_BASE_URL 转发）
export interface DownloadKnowledgeBaseDocParams {
  knowledge_base_name: string
  file_name: string
  preview?: boolean // 默认 false
}

export async function downloadKnowledgeBaseDoc(params: DownloadKnowledgeBaseDocParams): Promise<{ data: Blob | string; headers: Headers }> {
  const res = await httpKb.get<Blob | string>('/kb_chat/knowledge_base/download_doc', {
    params: {
      knowledge_base_name: params.knowledge_base_name,
      file_name: params.file_name,
      preview: String(params.preview ?? false)
    },
    timeout: 600000
  })
  return { data: res.data, headers: res.headers }
}

// 提取实体和关系示例
export async function autoNodesAndRelationships(payload: { example_text: string, allowed_nodes?: string[], allowed_relationships?: string[] }): Promise<any> {
  const res = await httpKb.post<any>('/kb_chat/knowledge_base/auto_nodes_and_relationships', payload)
  return res.data
}
