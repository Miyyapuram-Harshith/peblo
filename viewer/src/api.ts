const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      throw new Error(`Request failed with status ${response.status}`);
    }

    return response.json();
  }

  async getCatalogue() {
    return this.request<any>('/api/v1/catalog');
  }

  async searchCatalogue(query: string) {
    return this.request<any>(`/api/v1/catalog/search?q=${encodeURIComponent(query)}`);
  }
}

export const api = new ApiClient(API_BASE);
