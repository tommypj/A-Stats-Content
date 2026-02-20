import axios, { AxiosError, AxiosInstance, AxiosRequestConfig } from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Create a configured Axios instance
 */
export const apiClient: AxiosInstance = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30000, // 30 seconds
});

/**
 * Request interceptor for adding auth token
 */
apiClient.interceptors.request.use(
  (config) => {
    // Get token from localStorage or cookie
    const token =
      typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

/**
 * Response interceptor for handling errors
 */
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Clear token and redirect to login
      if (typeof window !== "undefined") {
        localStorage.removeItem("auth_token");
        window.location.href = "/login";
      }
    }

    return Promise.reject(error);
  }
);

/**
 * API Error type
 */
export interface ApiError {
  message: string;
  code?: string;
  details?: Record<string, unknown>;
}

/**
 * Parse API error response
 */
export function parseApiError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data;
    return {
      message: data?.detail || data?.message || error.message,
      code: data?.code,
      details: data?.details,
    };
  }

  if (error instanceof Error) {
    return { message: error.message };
  }

  return { message: "An unexpected error occurred" };
}

/**
 * Generic API request function
 */
export async function apiRequest<T>(config: AxiosRequestConfig): Promise<T> {
  const response = await apiClient.request<T>(config);
  return response.data;
}

/**
 * API endpoints
 */
export const api = {
  // Health
  health: {
    check: () => apiRequest<{ status: string }>({ url: "/health" }),
  },

  // Auth
  auth: {
    login: (email: string, password: string) =>
      apiRequest<{ access_token: string; token_type: string }>({
        method: "POST",
        url: "/auth/login",
        data: { email, password },
      }),
    register: (data: { email: string; password: string; name: string }) =>
      apiRequest<{ id: string; email: string }>({
        method: "POST",
        url: "/auth/register",
        data,
      }),
    me: () =>
      apiRequest<{ id: string; email: string; name: string }>({
        url: "/auth/me",
      }),
  },

  // Outlines
  outlines: {
    list: (params?: { page?: number; limit?: number }) =>
      apiRequest<{ items: Outline[]; total: number }>({
        url: "/outlines",
        params,
      }),
    get: (id: string) => apiRequest<Outline>({ url: `/outlines/${id}` }),
    create: (data: CreateOutlineInput) =>
      apiRequest<Outline>({
        method: "POST",
        url: "/outlines",
        data,
      }),
    update: (id: string, data: Partial<Outline>) =>
      apiRequest<Outline>({
        method: "PATCH",
        url: `/outlines/${id}`,
        data,
      }),
    delete: (id: string) =>
      apiRequest<void>({
        method: "DELETE",
        url: `/outlines/${id}`,
      }),
    generate: (id: string) =>
      apiRequest<Outline>({
        method: "POST",
        url: `/outlines/${id}/generate`,
      }),
  },

  // Articles
  articles: {
    list: (params?: { page?: number; limit?: number }) =>
      apiRequest<{ items: Article[]; total: number }>({
        url: "/articles",
        params,
      }),
    get: (id: string) => apiRequest<Article>({ url: `/articles/${id}` }),
    create: (data: CreateArticleInput) =>
      apiRequest<Article>({
        method: "POST",
        url: "/articles",
        data,
      }),
    update: (id: string, data: Partial<Article>) =>
      apiRequest<Article>({
        method: "PATCH",
        url: `/articles/${id}`,
        data,
      }),
    delete: (id: string) =>
      apiRequest<void>({
        method: "DELETE",
        url: `/articles/${id}`,
      }),
    generate: (id: string) =>
      apiRequest<Article>({
        method: "POST",
        url: `/articles/${id}/generate`,
      }),
  },

  // Images
  images: {
    list: (params?: { page?: number; limit?: number }) =>
      apiRequest<{ items: GeneratedImage[]; total: number }>({
        url: "/images",
        params,
      }),
    get: (id: string) => apiRequest<GeneratedImage>({ url: `/images/${id}` }),
    generate: (data: GenerateImageInput) =>
      apiRequest<GeneratedImage>({
        method: "POST",
        url: "/images/generate",
        data,
      }),
    delete: (id: string) =>
      apiRequest<void>({
        method: "DELETE",
        url: `/images/${id}`,
      }),
  },
};

// Type definitions
export interface Outline {
  id: string;
  title: string;
  keyword: string;
  status: "draft" | "generating" | "completed" | "failed";
  sections: OutlineSection[];
  created_at: string;
  updated_at: string;
}

export interface OutlineSection {
  heading: string;
  subheadings?: string[];
  notes?: string;
}

export interface CreateOutlineInput {
  keyword: string;
  target_audience?: string;
  tone?: string;
}

export interface Article {
  id: string;
  title: string;
  outline_id?: string;
  content: string;
  status: "draft" | "generating" | "completed" | "published";
  seo_score?: number;
  word_count: number;
  created_at: string;
  updated_at: string;
}

export interface CreateArticleInput {
  outline_id?: string;
  title?: string;
  keyword?: string;
}

export interface GeneratedImage {
  id: string;
  prompt: string;
  url: string;
  article_id?: string;
  created_at: string;
}

export interface GenerateImageInput {
  prompt: string;
  article_id?: string;
  style?: string;
}
