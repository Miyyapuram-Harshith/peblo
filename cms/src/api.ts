const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface ApiError {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
    request_id?: string;
  };
}

class ApiClient {
  private baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
    this.token = localStorage.getItem('peblo_token');
  }

  setToken(token: string | null) {
    this.token = token;
    if (token) {
      localStorage.setItem('peblo_token', token);
    } else {
      localStorage.removeItem('peblo_token');
    }
  }

  getToken(): string | null {
    return this.token;
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string> || {}),
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    if (!(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }

    const response = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let errorData: ApiError;
      try {
        errorData = await response.json();
      } catch {
        throw new Error(`Request failed with status ${response.status}`);
      }
      const err = new Error(errorData?.error?.message || `Request failed with status ${response.status}`) as Error & { code?: string; details?: Record<string, unknown>; status?: number };
      err.code = errorData?.error?.code;
      err.details = errorData?.error?.details;
      err.status = response.status;
      throw err;
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return response.json();
  }

  // Auth
  async login(email: string, password: string) {
    const data = await this.request<{ access_token: string; token_type: string }>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    this.setToken(data.access_token);
    return data;
  }

  async getMe() {
    return this.request<{ id: string; email: string; role: string; created_at: string }>('/api/v1/auth/me');
  }

  logout() {
    this.setToken(null);
  }

  // Shows
  async listShows(params: { page?: number; page_size?: number; search?: string; section?: string; status?: string } = {}) {
    const qs = new URLSearchParams();
    if (params.page) qs.set('page', String(params.page));
    if (params.page_size) qs.set('page_size', String(params.page_size));
    if (params.search) qs.set('search', params.search);
    if (params.section) qs.set('section', params.section);
    if (params.status) qs.set('status', params.status);
    return this.request<{ items: any[]; total: number; page: number; page_size: number }>(`/api/v1/admin/shows?${qs}`);
  }

  async getShow(id: string) {
    return this.request<any>(`/api/v1/admin/shows/${id}`);
  }

  async createShow(data: any) {
    return this.request<any>('/api/v1/admin/shows', { method: 'POST', body: JSON.stringify(data) });
  }

  async updateShow(id: string, data: any) {
    return this.request<any>(`/api/v1/admin/shows/${id}`, { method: 'PATCH', body: JSON.stringify(data) });
  }

  async deleteShow(id: string) {
    return this.request<void>(`/api/v1/admin/shows/${id}`, { method: 'DELETE' });
  }

  // Seasons
  async listSeasons(showId: string) {
    return this.request<any[]>(`/api/v1/admin/shows/${showId}/seasons`);
  }

  async createSeason(showId: string, data: any) {
    return this.request<any>(`/api/v1/admin/shows/${showId}/seasons`, { method: 'POST', body: JSON.stringify(data) });
  }

  async updateSeason(seasonId: string, data: any) {
    return this.request<any>(`/api/v1/admin/seasons/${seasonId}`, { method: 'PATCH', body: JSON.stringify(data) });
  }

  async deleteSeason(seasonId: string) {
    return this.request<void>(`/api/v1/admin/seasons/${seasonId}`, { method: 'DELETE' });
  }

  // Episodes
  async listEpisodes(params: { page?: number; page_size?: number; search?: string; language?: string; status?: string; show_id?: string; season_id?: string } = {}) {
    const qs = new URLSearchParams();
    if (params.page) qs.set('page', String(params.page));
    if (params.page_size) qs.set('page_size', String(params.page_size));
    if (params.search) qs.set('search', params.search);
    if (params.language) qs.set('language', params.language);
    if (params.status) qs.set('status', params.status);
    if (params.show_id) qs.set('show_id', params.show_id);
    if (params.season_id) qs.set('season_id', params.season_id);
    return this.request<{ items: any[]; total: number; page: number; page_size: number }>(`/api/v1/admin/episodes?${qs}`);
  }

  async getEpisode(id: string) {
    return this.request<any>(`/api/v1/admin/episodes/${id}`);
  }

  async createEpisode(data: any) {
    return this.request<any>('/api/v1/admin/episodes', { method: 'POST', body: JSON.stringify(data) });
  }

  async updateEpisode(id: string, data: any) {
    return this.request<any>(`/api/v1/admin/episodes/${id}`, { method: 'PATCH', body: JSON.stringify(data) });
  }

  async deleteEpisode(id: string) {
    return this.request<void>(`/api/v1/admin/episodes/${id}`, { method: 'DELETE' });
  }

  // Artwork
  async uploadArtwork(file: File, ownerType: string, ownerId: string, artworkType: string) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('owner_type', ownerType);
    formData.append('owner_id', ownerId);
    formData.append('artwork_type', artworkType);
    return this.request<any>('/api/v1/admin/artwork', { method: 'POST', body: formData });
  }

  async deleteArtwork(id: string) {
    return this.request<void>(`/api/v1/admin/artwork/${id}`, { method: 'DELETE' });
  }

  // Validation
  async getValidationReport() {
    return this.request<{ ready: boolean; total_issues: number; blocking_count: number; warning_count: number; issues: any[] }>('/api/v1/admin/validation-report');
  }

  // Publishing
  async publish(idempotencyKey?: string) {
    return this.request<any>('/api/v1/admin/catalog/publish', {
      method: 'POST',
      body: JSON.stringify({ idempotency_key: idempotencyKey || undefined }),
    });
  }

  async listPublishRuns(limit = 20) {
    return this.request<{ items: any[]; total: number }>(`/api/v1/admin/catalog/publish-runs?limit=${limit}`);
  }

  async getPublishRun(id: string) {
    return this.request<any>(`/api/v1/admin/catalog/publish-runs/${id}`);
  }

  // Health
  async healthLive() {
    return this.request<{ status: string }>('/health/live');
  }

  async healthReady() {
    return this.request<{ status: string; checks: Record<string, string> }>('/health/ready');
  }
}

export const api = new ApiClient(API_BASE);
export type { ApiError };
