const getAPIBaseURL = () => {
  if (typeof window === 'undefined') {
    return 'http://localhost:8000' // SSR fallback
  }
  const isLocal = window.location.hostname === 'localhost' || 
                 window.location.hostname === '127.0.0.1'
  return isLocal 
    ? 'http://localhost:8000' 
    : `http://${window.location.hostname}:8000`
}

const API_BASE_URL = getAPIBaseURL()

function getAuthHeaders(): HeadersInit {
  const apiKey = typeof window !== 'undefined' ? localStorage.getItem('apiKey') : null
  if (!apiKey) {
    throw new Error('Not authenticated')
  }
  return {
    'Authorization': `Bearer ${apiKey}`,
    'Content-Type': 'application/json',
  }
}

export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`
  const headers = { ...getAuthHeaders(), ...options.headers }
  
  const response = await fetch(url, {
    ...options,
    headers,
  })
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(error.detail || `API error: ${response.status}`)
  }
  
  return response.json()
}

export async function uploadFile(
  file: File,
  leadId: number
): Promise<{ upload_id: number; filename: string; size_bytes: number; created_at: string }> {
  const apiKey = localStorage.getItem('apiKey')
  if (!apiKey) {
    throw new Error('Not authenticated')
  }
  
  const formData = new FormData()
  formData.append('file', file)
  formData.append('lead_id', leadId.toString())
  
  const response = await fetch(`${API_BASE_URL}/api/uploads`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${apiKey}`,
    },
    body: formData,
  })
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Upload failed' }))
    throw new Error(error.detail || `Upload error: ${response.status}`)
  }
  
  return response.json()
}

// API functions
export const api = {
  // Health
  health: () => apiRequest<{ status: string; timestamp: string }>('/health'),
  
  // Leads
  getLeads: (query?: string, page: number = 1, pageSize: number = 50, pipelineId?: number, responsibleUserId?: number) => {
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
    })
    if (query) params.append('query', query)
    if (pipelineId) params.append('pipeline_id', pipelineId.toString())
    if (responsibleUserId) params.append('responsible_user_id', responsibleUserId.toString())
    return apiRequest<{
      leads: any[]
      total: number
      page: number
      page_size: number
    }>(`/api/leads?${params}`)
  },
  
  getLead: (leadId: number) => apiRequest<any>(`/api/leads/${leadId}`),
  
  getPipelines: () => apiRequest<{ pipelines: any[] }>('/api/leads/filters/pipelines'),
  
  getUsers: () => apiRequest<{ users: any[] }>('/api/leads/filters/users'),
  
  // Uploads
  uploadFile,
  
  // Jobs
  createJob: (leadId: number, uploadId: number) =>
    apiRequest<{ job_id: number; status: string }>('/api/jobs', {
      method: 'POST',
      body: JSON.stringify({ lead_id: leadId, upload_id: uploadId }),
    }),
  
  getJob: (jobId: number) => apiRequest<any>(`/api/jobs/${jobId}`),
  
  getLeadJobs: (leadId: number) => 
    apiRequest<{ jobs: any[] }>(`/api/leads/${leadId}/jobs`),
  
  pushToKommo: (jobId: number) =>
    apiRequest<{ message: string }>(`/api/jobs/${jobId}/push`, {
      method: 'POST',
    }),
  
  askQuestion: (jobId: number, question: string) =>
    apiRequest<{ question: string; answer: string; timestamp: string }>(`/api/jobs/${jobId}/ask`, {
      method: 'POST',
      body: JSON.stringify({ question }),
    }),
  
  // Settings
  getKommoInfo: () => apiRequest<any>('/api/settings/kommo/info'),
  
  pasteKommoTokens: (tokens: {
    access_token: string
    refresh_token: string
    expires_at: string
  }) =>
    apiRequest<{ message: string }>('/api/settings/kommo/paste', {
      method: 'POST',
      body: JSON.stringify(tokens),
    }),
  
  getFieldMapping: () => apiRequest<{ mapping: any }>('/api/settings/mapping'),
  
  updateFieldMapping: (mapping: any) =>
    apiRequest<{ message: string }>('/api/settings/mapping', {
      method: 'PUT',
      body: JSON.stringify({ mapping }),
    }),
}


