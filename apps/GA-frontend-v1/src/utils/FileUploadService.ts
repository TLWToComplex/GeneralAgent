import StorageService from './StorageService';
import { getApiBaseUrl } from './RuntimeConfig';
import { ensureAuthenticatedRequestAllowed } from './http';

export interface DocumentChunk {
  chunk_id: number;
  content: string;
  filename: string;
}

export interface UploadSummary {
  files: Array<{
    chunks: number;
    filename: string;
  }>;
  total_chunks: number;
  total_tokens: number;
}

export interface UploadResponse {
  conversation_id: string;
  document_chunks: DocumentChunk[];
  message: string;
  success: boolean;
  summary: UploadSummary;
}

export type FileProcessType = 'mineru' | 'langchain';

export class FileUploadService {
  /**
   * 上传并解析文件
   * @param file 要上传的文件
   * @param conversationId 会话ID
   * @param onProgress 上传进度回调 (0-100)
   * @param sessionThreadId 当前对话的会话线程ID
   * @param turnId 发送文档这一轮的轮次ID
   * @returns 解析结果
   */
  static async uploadFile(
    file: File, 
    conversationId: string,
    processType: FileProcessType,
    onProgress?: (percent: number) => void,
    sessionThreadId?: string,
    turnId?: string
  ): Promise<UploadResponse> {
    const baseUrl = getApiBaseUrl();
    
    // 移除末尾的斜杠（如果有）
    const cleanBaseUrl = baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl;
    const uploadUrl = `${cleanBaseUrl}/aiFileProcessor/upload`;
    ensureAuthenticatedRequestAllowed(uploadUrl);

    const formData = new FormData();
    formData.append('files', file);
    formData.append('conversation_id', conversationId);
    formData.append('process_type', processType);
    if (sessionThreadId) {
      formData.append('session_thread_id', sessionThreadId);
    }
    if (turnId) {
      formData.append('turn_id', turnId);
    }

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', uploadUrl);

      // 添加认证头
      const token = StorageService.getAccessToken();
      if (token) {
        xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      }

      if (onProgress) {
        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable) {
            const percentComplete = (event.loaded / event.total) * 100;
            onProgress(Math.round(percentComplete));
          }
        };
      }

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const response = JSON.parse(xhr.responseText);
            resolve(response as UploadResponse);
          } catch (e) {
            reject(new Error('Failed to parse response'));
          }
        } else {
          reject(new Error(`Upload failed with status: ${xhr.status}`));
        }
      };

      xhr.onerror = () => {
        reject(new Error('Network error occurred'));
      };

      xhr.send(formData);
    });
  }

  /**
   * 上传文件供DeepAgent使用
   * @param file 要上传的文件
   * @param sessionThreadId 当前对话的会话线程ID
   * @param onProgress 上传进度回调 (0-100)
   * @param classification 文件密级
   * @param turnId 发送文档这一轮的轮次ID
   * @returns 解析结果
   */
  static async uploadDeepAgentFile(
    file: File, 
    sessionThreadId: string,
    onProgress?: (percent: number) => void,
    classification?: 'public' | 'internal',
    turnId?: string
  ): Promise<any> {
    const baseUrl = getApiBaseUrl();
    
    // 移除末尾的斜杠（如果有）
    const cleanBaseUrl = baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl;
    const classificationParam = classification ? `&classification=${encodeURIComponent(classification)}` : '';
    const turnIdParam = turnId ? `&turn_id=${encodeURIComponent(turnId)}` : '';
    const uploadUrl = `${cleanBaseUrl}/skill/api/files/upload?session_thread_id=${encodeURIComponent(sessionThreadId)}${classificationParam}${turnIdParam}`;
    ensureAuthenticatedRequestAllowed(uploadUrl);

    const formData = new FormData();
    formData.append('file', file);

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', uploadUrl);

      // 添加认证头
      const token = StorageService.getAccessToken();
      if (token) {
        xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      }

      if (onProgress) {
        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable) {
            const percentComplete = (event.loaded / event.total) * 100;
            onProgress(Math.round(percentComplete));
          }
        };
      }

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const response = JSON.parse(xhr.responseText);
            resolve(response);
          } catch (e) {
            reject(new Error('Failed to parse response'));
          }
        } else {
          reject(new Error(`Upload failed with status: ${xhr.status}`));
        }
      };

      xhr.onerror = () => {
        reject(new Error('Network error occurred'));
      };

      xhr.send(formData);
    });
  }
}
