import { http } from '@/utils/http'

export async function addMcpServer(payload: any): Promise<any> {
  const res = await http.post('/aiMCPServer/add', payload)
  return res.data
}

export async function testMcpServerConnection(payload: {
  server_name: string;
  url: string;
  type: string;
  headers?: Record<string, string>;
}): Promise<any> {
  const res = await http.post('/aiMCPServer/test', payload)
  return res.data
}

export async function listMcpServers(): Promise<{ code: number; data: any[]; message?: string; total?: number; skip?: number; take?: number }> {
  const res = await http.get('/aiMCPServer/list')
  return res.data as any
}

export async function deleteMcpServer(payload: { uuid: string }): Promise<any> {
  const res = await http.post('/aiMCPServer/delete', payload)
  return res.data
}

export async function updateMcpServer(payload: any): Promise<any> {
  const res = await http.post('/aiMCPServer/update', payload)
  return res.data
}
