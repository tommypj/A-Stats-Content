import axios, { AxiosError, AxiosInstance, AxiosRequestConfig } from "axios";
import { toast } from "sonner";
import { useAuthStore } from "@/stores/auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ---------------------------------------------------------------------------
// Simple in-memory SWR-like cache for GET requests
// The cache is keyed by URL + serialised params and stores the response data
// alongside the timestamp at which it was stored.  Entries are considered
// fresh as long as they are younger than the TTL passed to getCached().
// The cache lives only in the browser's JS heap — it clears on page reload,
// which is the desired behaviour (no stale cross-session data).
// ---------------------------------------------------------------------------

const apiCache = new Map<string, { data: unknown; timestamp: number }>();
const MAX_CACHE_SIZE = 100;

function getCached<T>(key: string, ttlMs: number): T | null {
  const entry = apiCache.get(key);
  if (entry && Date.now() - entry.timestamp < ttlMs) {
    return entry.data as T;
  }
  return null;
}

function setCache(key: string, data: unknown): void {
  apiCache.set(key, { data, timestamp: Date.now() });
  if (apiCache.size > MAX_CACHE_SIZE) {
    const firstKey = Array.from(apiCache.keys())[0];
    apiCache.delete(firstKey);
  }
}

export function invalidateCache(prefix?: string): void {
  if (!prefix) {
    apiCache.clear();
    return;
  }
  Array.from(apiCache.keys()).forEach((key) => {
    if (key.startsWith(prefix)) {
      apiCache.delete(key);
    }
  });
}

async function cachedGet<T>(url: string, ttlMs: number, params?: Record<string, unknown>): Promise<T> {
  const cacheKey = url + (params ? JSON.stringify(params) : "");
  const cached = getCached<T>(cacheKey, ttlMs);
  if (cached) return cached;
  const { data } = await apiClient.get<T>(url, { params });
  setCache(cacheKey, data);
  return data;
}

/**
 * Create a configured Axios instance
 */
export const apiClient: AxiosInstance = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30000, // 30 seconds default
});

/**
 * Construct full image URL from a relative or absolute path.
 * Backend stores image URLs as relative paths like /uploads/images/...
 */
export function getImageUrl(url: string | null | undefined): string {
  if (!url) return "";
  // Already a full URL
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  // Relative path — prepend API base URL
  const base = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/api\/v1\/?$/, "");
  return `${base}${url.startsWith("/") ? "" : "/"}${url}`;
}

/**
 * Extended timeout for AI generation requests (articles, outlines, images)
 */
const AI_TIMEOUT = 180000; // 3 minutes

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
 * Silent token refresh logic.
 * When a 401 is received, attempts to refresh the access token using
 * the stored refresh token before redirecting to login.
 * Queues concurrent requests so only one refresh call is made at a time.
 */
let isRefreshing = false;
const MAX_QUEUE_SIZE = 50;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (error: unknown) => void;
}> = [];

function processQueue(error: unknown, token: string | null) {
  failedQueue.forEach((promise) => {
    if (token) {
      promise.resolve(token);
    } else {
      promise.reject(error);
    }
  });
  failedQueue = [];
}

let isLoggingOut = false;
function forceLogout() {
  if (isLoggingOut) return;
  isLoggingOut = true;
  useAuthStore.getState().logout();
  window.location.href = "/login";
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };

    // Only attempt refresh on 401 errors, not on auth endpoints themselves
    if (
      error.response?.status === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      !originalRequest.url?.includes("/auth/login") &&
      !originalRequest.url?.includes("/auth/refresh") &&
      typeof window !== "undefined"
    ) {
      const refreshToken = localStorage.getItem("refresh_token");

      if (!refreshToken) {
        forceLogout();
        return Promise.reject(error);
      }

      if (isRefreshing) {
        // Another refresh is in progress — queue this request
        if (failedQueue.length >= MAX_QUEUE_SIZE) {
          // Queue is full; reject immediately to avoid unbounded growth
          forceLogout();
          return Promise.reject(new Error("Auth refresh queue overflow"));
        }
        return new Promise((resolve, reject) => {
          failedQueue.push({
            resolve: (token: string) => {
              originalRequest._retry = true;
              if (originalRequest.headers) {
                originalRequest.headers.Authorization = `Bearer ${token}`;
              }
              resolve(apiClient(originalRequest));
            },
            reject,
          });
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const { data } = await axios.post(`${API_URL}/api/v1/auth/refresh`, {
          refresh_token: refreshToken,
        });

        const newAccessToken = data.access_token;
        const newRefreshToken = data.refresh_token;

        localStorage.setItem("auth_token", newAccessToken);
        if (newRefreshToken) {
          localStorage.setItem("refresh_token", newRefreshToken);
        }

        processQueue(null, newAccessToken);

        // Retry the original request with new token
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        }
        return apiClient(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        forceLogout();
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

/**
 * Response interceptor: show retry toast on network errors and 5xx responses.
 * Runs after the 401/refresh interceptor above.
 */
apiClient.interceptors.response.use(undefined, (error: AxiosError) => {
  const status = error.response?.status;
  const isNetworkError = !error.response && error.code !== "ERR_CANCELED";
  const isServerError = status !== undefined && status >= 500;

  if ((isNetworkError || isServerError) && error.config && typeof window !== "undefined") {
    const cfg = error.config as AxiosRequestConfig & { _retry?: boolean };
    const message = isNetworkError
      ? "Network error — check your connection"
      : `Server error (${status})`;

    // FE-CONTENT-26: Note — retry only works for idempotent requests; POST retries may create duplicates
    toast.error(message, {
      action: {
        label: "Retry",
        onClick: () => {
          apiClient(cfg).catch(() => {
            // retry failed — the interceptor will fire again
          });
        },
      },
    });
  }

  return Promise.reject(error);
});

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
      apiRequest<{ access_token: string; refresh_token: string; token_type: string; expires_in: number }>({
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
    me: () => cachedGet<UserResponse>("/auth/me", 60_000),
    refresh: (refreshToken: string) =>
      apiRequest<{ access_token: string; refresh_token: string; token_type: string; expires_in: number }>({
        method: "POST",
        url: "/auth/refresh",
        data: { refresh_token: refreshToken },
      }),
    logout: async (): Promise<void> => {
      try {
        await apiRequest<void>({ method: "POST", url: "/auth/logout" });
      } catch {
        // Best-effort server-side logout; clear local state regardless
      }
      localStorage.removeItem("auth_token");
      localStorage.removeItem("refresh_token");
    },
    forgotPassword: (email: string) =>
      apiRequest<{ message: string }>({
        method: "POST",
        url: "/auth/password/reset-request",
        data: { email },
      }),
    resetPassword: (token: string, password: string) =>
      apiRequest<{ message: string }>({
        method: "POST",
        url: "/auth/password/reset",
        data: { token, new_password: password },
      }),
    verifyEmail: (token: string) =>
      apiRequest<{ message: string }>({
        method: "POST",
        url: "/auth/verify-email",
        data: { token },
      }),
    updateProfile: async (data: { name?: string; language?: string; timezone?: string }) => {
      const result = await apiRequest<UserResponse>({
        method: "PUT",
        url: "/auth/me",
        data,
      });
      invalidateCache("/auth/me");
      return result;
    },
    changePassword: (currentPassword: string, newPassword: string) =>
      apiRequest<{ message: string }>({
        method: "POST",
        url: "/auth/password/change",
        data: { current_password: currentPassword, new_password: newPassword },
      }),
    deleteAccount: () =>
      apiRequest<{ message: string }>({
        method: "DELETE",
        url: "/auth/account",
        data: { confirmation: "DELETE MY ACCOUNT" },
      }),
    uploadAvatar: async (file: File) => {
      const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"];
      const MAX_SIZE_BYTES = 5 * 1024 * 1024; // 5MB
      if (!ALLOWED_TYPES.includes(file.type)) {
        throw new Error("Invalid file type. Only JPEG, PNG, GIF, and WebP images are allowed.");
      }
      if (file.size > MAX_SIZE_BYTES) {
        throw new Error("File too large. Maximum avatar size is 5MB.");
      }
      const formData = new FormData();
      formData.append("file", file);
      const { data } = await apiClient.post<UserResponse>("/auth/me/avatar", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      invalidateCache("/auth/me");
      return data;
    },
    exportData: async () => {
      const response = await apiClient.get("/auth/me/export", {
        responseType: "blob",
      });
      const blob = new Blob([response.data], { type: "application/json" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "my_data_export.json";
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    },
  },

  // Outlines
  outlines: {
    list: (params?: { page?: number; page_size?: number; status?: string; keyword?: string; project_id?: string }) =>
      apiRequest<OutlineListResponse>({
        url: "/outlines",
        params,
      }),
    get: (id: string) => apiRequest<Outline>({ url: `/outlines/${id}` }),
    create: (data: CreateOutlineInput) =>
      apiRequest<Outline>({
        method: "POST",
        url: "/outlines",
        data,
        timeout: AI_TIMEOUT,
      }),
    update: (id: string, data: UpdateOutlineInput) =>
      apiRequest<Outline>({
        method: "PUT",
        url: `/outlines/${id}`,
        data,
      }),
    delete: (id: string) =>
      apiRequest<void>({
        method: "DELETE",
        url: `/outlines/${id}`,
      }),
    bulkDelete: (ids: string[]) =>
      apiRequest<{ deleted: number }>({
        method: "POST",
        url: "/outlines/bulk-delete",
        data: { ids },
      }),
    regenerate: (id: string) =>
      apiRequest<Outline>({
        method: "POST",
        url: `/outlines/${id}/regenerate`,
        timeout: AI_TIMEOUT,
      }),
    exportAll: (format: "csv" = "csv") =>
      apiClient.get("/outlines/export", {
        params: { format },
        responseType: "blob",
      }),
    exportOne: (id: string, format: "markdown" | "html" | "csv") =>
      apiClient.get(`/outlines/${id}/export`, {
        params: { format },
        responseType: "blob",
      }),
  },

  // Articles
  articles: {
    list: (params?: { page?: number; page_size?: number; status?: string; keyword?: string; project_id?: string }) =>
      apiRequest<ArticleListResponse>({
        url: "/articles",
        params,
      }),
    get: (id: string) => apiRequest<Article>({ url: `/articles/${id}` }),
    create: async (data: CreateArticleInput) => {
      const result = await apiRequest<Article>({
        method: "POST",
        url: "/articles",
        data,
      });
      invalidateCache("/articles");
      return result;
    },
    generate: (data: GenerateArticleInput) =>
      apiRequest<Article>({
        method: "POST",
        url: "/articles/generate",
        data,
        timeout: AI_TIMEOUT,
      }),
    update: async (id: string, data: UpdateArticleInput) => {
      const result = await apiRequest<Article>({
        method: "PUT",
        url: `/articles/${id}`,
        data,
      });
      invalidateCache("/articles");
      return result;
    },
    delete: async (id: string) => {
      await apiRequest<void>({
        method: "DELETE",
        url: `/articles/${id}`,
      });
      invalidateCache("/articles");
    },
    bulkDelete: async (ids: string[]) => {
      const result = await apiRequest<{ deleted: number }>({
        method: "POST",
        url: "/articles/bulk-delete",
        data: { ids },
      });
      invalidateCache("/articles");
      return result;
    },
    improve: (id: string, improvement_type: string) =>
      apiRequest<Article>({
        method: "POST",
        url: `/articles/${id}/improve`,
        data: { improvement_type },
        timeout: AI_TIMEOUT,
      }),
    analyzeSeo: (id: string) =>
      apiRequest<Article>({
        method: "POST",
        url: `/articles/${id}/analyze-seo`,
      }),
    generateImagePrompt: (id: string) =>
      apiRequest<Article>({
        method: "POST",
        url: `/articles/${id}/generate-image-prompt`,
        timeout: AI_TIMEOUT,
      }),
    getSocialPosts: (id: string) =>
      apiRequest<SocialPostsData>({
        url: `/articles/${id}/social-posts`,
      }),
    generateSocialPosts: (id: string) =>
      apiRequest<SocialPostsData>({
        method: "POST",
        url: `/articles/${id}/generate-social-posts`,
        timeout: AI_TIMEOUT,
      }),
    updateSocialPost: (id: string, platform: string, text: string) =>
      apiRequest<SocialPostsData>({
        method: "PUT",
        url: `/articles/${id}/social-posts`,
        data: { platform, text },
      }),
    listRevisions: (articleId: string, params?: { page?: number; page_size?: number }) =>
      apiRequest<ArticleRevisionListResponse>({
        url: `/articles/${articleId}/revisions`,
        params,
      }),
    getRevision: (articleId: string, revisionId: string) =>
      apiRequest<ArticleRevisionDetail>({
        url: `/articles/${articleId}/revisions/${revisionId}`,
      }),
    restoreRevision: (articleId: string, revisionId: string) =>
      apiRequest<Article>({
        method: "POST",
        url: `/articles/${articleId}/revisions/${revisionId}/restore`,
      }),
    linkSuggestions: (articleId: string) =>
      apiRequest<LinkSuggestionsResponse>({
        url: `/articles/${articleId}/link-suggestions`,
      }),
    healthSummary: () =>
      apiRequest<ContentHealthSummary>({
        url: "/articles/health-summary",
      }),
    keywordSuggestions: (seedKeyword: string, count: number = 10) =>
      apiRequest<KeywordSuggestionsResponse>({
        method: "POST",
        url: "/articles/keyword-suggestions",
        data: { seed_keyword: seedKeyword, count },
        timeout: AI_TIMEOUT,
      }),
    exportAll: (format: "csv" = "csv") =>
      apiClient.get("/articles/export", {
        params: { format },
        responseType: "blob",
      }),
    exportOne: (id: string, format: "markdown" | "html" | "csv") =>
      apiClient.get(`/articles/${id}/export`, {
        params: { format },
        responseType: "blob",
      }),
    // AEO
    getAeoScore: (articleId: string) =>
      apiRequest<AEOScore>({
        url: `/articles/${articleId}/aeo-score`,
      }),
    refreshAeoScore: (articleId: string) =>
      apiRequest<AEOScore>({
        method: "POST",
        url: `/articles/${articleId}/aeo-score`,
      }),
    aeoOptimize: (articleId: string) =>
      apiRequest<AEOSuggestionsResponse>({
        method: "POST",
        url: `/articles/${articleId}/aeo-optimize`,
        timeout: 60000,
      }),
  },

  // Images
  images: {
    list: (params?: { page?: number; page_size?: number; project_id?: string }) =>
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
        // Generation now returns 202 immediately; no long timeout needed.
        timeout: 15000,
      }),
    delete: (id: string) =>
      apiRequest<void>({
        method: "DELETE",
        url: `/images/${id}`,
      }),
    bulkDelete: (ids: string[]) =>
      apiRequest<{ deleted: number }>({
        method: "POST",
        url: "/images/bulk-delete",
        data: { ids },
      }),
  },

  // WordPress
  wordpress: {
    connect: (data: WordPressConnectInput) =>
      apiRequest<WordPressConnection>({
        method: "POST",
        url: "/wordpress/connect",
        data,
      }),
    disconnect: () =>
      apiRequest<void>({
        method: "POST",
        url: "/wordpress/disconnect",
      }),
    status: () =>
      apiRequest<WordPressConnectionStatus>({
        url: "/wordpress/status",
      }),
    categories: () =>
      apiRequest<WordPressCategory[]>({
        url: "/wordpress/categories",
      }),
    tags: () =>
      apiRequest<WordPressTag[]>({
        url: "/wordpress/tags",
      }),
    publish: (data: WordPressPublishInput) =>
      apiRequest<WordPressPublishResponse>({
        method: "POST",
        url: "/wordpress/publish",
        data,
      }),
    uploadMedia: (data: WordPressMediaUploadInput) =>
      apiRequest<WordPressMediaUploadResponse>({
        method: "POST",
        url: "/wordpress/upload-media",
        data,
        timeout: 60000,
      }),
  },

  // Analytics / Google Search Console
  analytics: {
    getAuthUrl: () =>
      apiRequest<GSCAuthUrlResponse>({
        url: "/analytics/gsc/auth-url",
      }),
    handleCallback: (code: string, state: string) =>
      apiRequest<void>({
        method: "POST",
        url: "/analytics/gsc/callback",
        data: { code, state },
      }),
    status: () =>
      apiRequest<GSCStatus>({
        url: "/analytics/gsc/status",
      }),
    sites: () =>
      apiRequest<GSCSiteListResponse>({
        url: "/analytics/gsc/sites",
      }),
    selectSite: (site_url: string) =>
      apiRequest<GSCStatus>({
        method: "POST",
        url: "/analytics/gsc/select-site",
        data: { site_url },
      }),
    disconnect: () =>
      apiRequest<GSCDisconnectResponse>({
        method: "POST",
        url: "/analytics/gsc/disconnect",
      }),
    sync: () =>
      apiRequest<GSCSyncResponse>({
        method: "POST",
        url: "/analytics/gsc/sync",
      }),
    keywords: (params?: AnalyticsQueryParams) =>
      apiRequest<KeywordRankingListResponse>({
        url: "/analytics/keywords",
        params,
      }),
    pages: (params?: AnalyticsQueryParams) =>
      apiRequest<PagePerformanceListResponse>({
        url: "/analytics/pages",
        params,
      }),
    daily: (params?: AnalyticsQueryParams) =>
      apiRequest<DailyAnalyticsListResponse>({
        url: "/analytics/daily",
        params,
      }),
    summary: (params?: { start_date?: string; end_date?: string }) =>
      apiRequest<AnalyticsSummary>({
        url: "/analytics/summary",
        params,
      }),
    articlePerformance: (params?: ArticlePerformanceParams) =>
      apiRequest<ArticlePerformanceListResponse>({
        url: "/analytics/article-performance",
        params,
      }),
    articlePerformanceDetail: (articleId: string, params?: { start_date?: string; end_date?: string }) =>
      apiRequest<ArticlePerformanceDetailResponse>({
        url: `/analytics/article-performance/${articleId}`,
        params,
      }),
    opportunities: (params?: { start_date?: string; end_date?: string }) =>
      apiRequest<ContentOpportunitiesResponse>({
        url: "/analytics/opportunities",
        params,
      }),
    suggestContent: (keywords: string[], maxSuggestions: number = 5) =>
      apiRequest<ContentSuggestionsResponse>({
        method: "POST",
        url: "/analytics/opportunities/suggest",
        data: { keywords, max_suggestions: maxSuggestions },
        timeout: 60000,
      }),
    // Content Decay / Health
    contentHealth: () =>
      apiRequest<ContentHealthSummary2>({
        url: "/analytics/decay/health",
      }),
    decayAlerts: (params?: DecayAlertsParams) =>
      apiRequest<ContentDecayAlertListResponse>({
        url: "/analytics/decay/alerts",
        params,
      }),
    detectDecay: () =>
      apiRequest<DecayDetectionResponse>({
        method: "POST",
        url: "/analytics/decay/detect",
      }),
    markAlertRead: (alertId: string) =>
      apiRequest<{ message: string }>({
        method: "POST",
        url: `/analytics/decay/alerts/${alertId}/read`,
      }),
    resolveAlert: (alertId: string) =>
      apiRequest<{ message: string }>({
        method: "POST",
        url: `/analytics/decay/alerts/${alertId}/resolve`,
      }),
    suggestRecovery: (alertId: string) =>
      apiRequest<DecayRecoverySuggestions>({
        method: "POST",
        url: `/analytics/decay/alerts/${alertId}/suggest`,
        timeout: 60000,
      }),
    markAllAlertsRead: () =>
      apiRequest<{ message: string }>({
        method: "POST",
        url: "/analytics/decay/alerts/mark-all-read",
      }),
    // AEO
    aeoOverview: () =>
      apiRequest<AEOOverviewResponse>({
        url: "/analytics/aeo/overview",
      }),
    // Revenue
    revenueOverview: (params?: { start_date?: string; end_date?: string }) =>
      apiRequest<RevenueOverview>({
        url: "/analytics/revenue/overview",
        params,
      }),
    revenueByArticle: (params?: { start_date?: string; end_date?: string; page?: number; page_size?: number }) =>
      apiRequest<RevenueByArticleListResponse>({
        url: "/analytics/revenue/by-article",
        params,
      }),
    revenueByKeyword: (params?: { start_date?: string; end_date?: string; page?: number; page_size?: number }) =>
      apiRequest<RevenueByKeywordListResponse>({
        url: "/analytics/revenue/by-keyword",
        params,
      }),
    revenueGoals: () =>
      apiRequest<ConversionGoalListResponse>({
        url: "/analytics/revenue/goals",
      }),
    createRevenueGoal: (data: { name: string; goal_type: string; goal_config?: Record<string, unknown> }) =>
      apiRequest<ConversionGoal>({
        method: "POST",
        url: "/analytics/revenue/goals",
        data,
      }),
    updateRevenueGoal: (goalId: string, data: { name?: string; goal_type?: string; goal_config?: Record<string, unknown>; is_active?: boolean }) =>
      apiRequest<ConversionGoal>({
        method: "PUT",
        url: `/analytics/revenue/goals/${goalId}`,
        data,
      }),
    deleteRevenueGoal: (goalId: string) =>
      apiRequest<{ message: string }>({
        method: "DELETE",
        url: `/analytics/revenue/goals/${goalId}`,
      }),
    importConversions: (data: { goal_id: string; conversions: Array<{ page_url: string; date: string; visits: number; conversions: number; revenue: number }> }) =>
      apiRequest<ImportConversionsResponse>({
        method: "POST",
        url: "/analytics/revenue/import",
        data,
      }),
    generateRevenueReport: (reportType: string = "monthly") =>
      apiRequest<RevenueReport>({
        method: "POST",
        url: "/analytics/revenue/report",
        params: { report_type: reportType },
      }),
    // Device / Country Breakdown
    deviceBreakdown: (days?: number) =>
      apiRequest<{ items: DeviceBreakdownItem[] }>({
        url: "/analytics/device-breakdown",
        params: { days },
      }),
    countryBreakdown: (days?: number, top_n?: number) =>
      apiRequest<{ items: CountryBreakdownItem[]; total: number }>({
        url: "/analytics/country-breakdown",
        params: { days, top_n },
      }),
  },

  // Bulk Content
  bulk: {
    // Templates
    templates: () =>
      apiRequest<TemplateListResponse>({
        url: "/bulk/templates",
      }),
    createTemplate: (data: { name: string; description?: string; template_config: TemplateConfig }) =>
      apiRequest<ContentTemplate>({
        method: "POST",
        url: "/bulk/templates",
        data,
      }),
    updateTemplate: (id: string, data: { name?: string; description?: string; template_config?: TemplateConfig }) =>
      apiRequest<ContentTemplate>({
        method: "PUT",
        url: `/bulk/templates/${id}`,
        data,
      }),
    deleteTemplate: (id: string) =>
      apiRequest<{ message: string }>({
        method: "DELETE",
        url: `/bulk/templates/${id}`,
      }),
    // Jobs
    jobs: (params?: { page?: number; page_size?: number; status?: string }) =>
      apiRequest<BulkJobListResponse>({
        url: "/bulk/jobs",
        params,
      }),
    getJob: (jobId: string) =>
      apiRequest<BulkJobDetail>({
        url: `/bulk/jobs/${jobId}`,
      }),
    createOutlineJob: (data: { keywords: BulkKeywordInput[]; template_id?: string }) =>
      apiRequest<BulkJob>({
        method: "POST",
        url: "/bulk/jobs/outlines",
        data,
      }),
    cancelJob: (jobId: string) =>
      apiRequest<{ message: string }>({
        method: "POST",
        url: `/bulk/jobs/${jobId}/cancel`,
      }),
    retryFailed: (jobId: string) =>
      apiRequest<{ message: string }>({
        method: "POST",
        url: `/bulk/jobs/${jobId}/retry-failed`,
      }),
  },

  // Billing / LemonSqueezy
  billing: {
    pricing: () => cachedGet<PricingResponse>("/billing/pricing", 300_000),
    subscription: () =>
      apiRequest<SubscriptionStatus>({
        url: "/billing/subscription",
      }),
    checkout: (plan: string, billingCycle: string) =>
      apiRequest<CheckoutResponse>({
        method: "POST",
        url: "/billing/checkout",
        data: { plan, billing_cycle: billingCycle },
      }),
    portal: () =>
      apiRequest<CustomerPortalResponse>({
        url: "/billing/portal",
      }),
    cancel: () =>
      apiRequest<{ success: boolean; message: string }>({
        method: "POST",
        url: "/billing/cancel",
      }),
  },

  // Knowledge Vault
  knowledge: {
    upload: (file: File, title?: string, description?: string, tags?: string, projectId?: string) => {
      const formData = new FormData();
      formData.append("file", file);
      if (title) formData.append("title", title);
      if (description) formData.append("description", description);
      if (tags) formData.append("tags", tags);
      if (projectId) formData.append("project_id", projectId);

      return apiClient.post<KnowledgeSource>("/knowledge/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      }).then(res => res.data);
    },
    sources: (params?: { page?: number; page_size?: number; status?: string; search?: string; project_id?: string }) =>
      apiRequest<KnowledgeSourceList>({
        url: "/knowledge/sources",
        params,
      }),
    getSource: (id: string) =>
      apiRequest<KnowledgeSource>({
        url: `/knowledge/sources/${id}`,
      }),
    deleteSource: (id: string) =>
      apiRequest<void>({
        method: "DELETE",
        url: `/knowledge/sources/${id}`,
      }),
    query: (query: string, sourceIds?: string[], maxResults?: number) =>
      apiRequest<QueryResponse>({
        method: "POST",
        url: "/knowledge/query",
        data: { query, source_ids: sourceIds, max_results: maxResults },
      }),
    stats: () =>
      apiRequest<KnowledgeStats>({
        url: "/knowledge/stats",
      }),
    reprocess: (id: string) =>
      apiRequest<KnowledgeSource>({
        method: "POST",
        url: `/knowledge/sources/${id}/reprocess`,
      }),
  },

  // Social Media
  social: {
    posts: (params?: SocialPostQueryParams & { project_id?: string }) =>
      apiRequest<SocialPostListResponse>({
        url: "/social/posts",
        params,
      }),
    getPost: (id: string) =>
      apiRequest<SocialPost>({
        url: `/social/posts/${id}`,
      }),
    createPost: (data: CreateSocialPostInput) =>
      apiRequest<SocialPost>({
        method: "POST",
        url: "/social/posts",
        data,
      }),
    updatePost: (id: string, data: UpdateSocialPostInput) =>
      apiRequest<SocialPost>({
        method: "PUT",
        url: `/social/posts/${id}`,
        data,
      }),
    deletePost: (id: string) =>
      apiRequest<void>({
        method: "DELETE",
        url: `/social/posts/${id}`,
      }),
    publishNow: (id: string) =>
      apiRequest<SocialPost>({
        method: "POST",
        url: `/social/posts/${id}/publish-now`,
      }),
    reschedule: (id: string, newDate: string) =>
      apiRequest<SocialPost>({
        method: "PUT",
        url: `/social/posts/${id}`,
        data: { scheduled_at: newDate },
      }),
    retryFailed: (id: string, targetIds?: string[]) =>
      apiRequest<SocialPost>({
        method: "PUT",
        url: `/social/posts/${id}`,
        data: { status: "pending", target_ids: targetIds },
      }),
    accounts: () =>
      apiRequest<SocialAccountListResponse>({
        url: "/social/accounts",
      }),
    getConnectUrl: (platform: SocialPlatform) =>
      apiRequest<{ authorization_url: string; state: string }>({
        url: `/social/${platform}/connect`,
      }),
    disconnectAccount: (id: string) =>
      apiRequest<void>({
        method: "DELETE",
        url: `/social/accounts/${id}`,
      }),
    verify: (accountId: string) =>
      apiRequest<SocialAccount>({
        method: "POST",
        url: `/social/accounts/${accountId}/verify`,
      }),
    analytics: (postId: string) =>
      apiRequest<SocialAnalytics>({
        url: `/social/posts/${postId}/analytics`,
      }),
  },

  // Admin
  admin: {
    dashboard: () =>
      apiRequest<AdminDashboardStats>({
        url: "/admin/analytics/dashboard",
      }),
    users: {
      list: (params?: AdminUserQueryParams) =>
        apiRequest<AdminUserListResponse>({
          url: "/admin/users",
          params,
        }),
      get: (id: string) =>
        apiRequest<AdminUserDetail>({
          url: `/admin/users/${id}`,
        }),
      update: (id: string, data: AdminUpdateUserInput) =>
        apiRequest<AdminUserDetail>({
          method: "PUT",
          url: `/admin/users/${id}`,
          data,
        }),
      suspend: (id: string, reason: string) =>
        apiRequest<AdminUserDetail>({
          method: "POST",
          url: `/admin/users/${id}/suspend`,
          data: { reason },
        }),
      unsuspend: (id: string) =>
        apiRequest<AdminUserDetail>({
          method: "POST",
          url: `/admin/users/${id}/unsuspend`,
        }),
      delete: (id: string) =>
        apiRequest<void>({
          method: "DELETE",
          url: `/admin/users/${id}`,
        }),
      resetPassword: (id: string, sendEmail: boolean = true) =>
        apiRequest<{ success: boolean; message: string }>({
          method: "POST",
          url: `/admin/users/${id}/reset-password`,
          data: { send_email: sendEmail },
        }),
      // bulkSuspend: backend endpoint not yet implemented
      // Use individual suspend calls instead
      bulkSuspend: async (userIds: string[], reason: string) => {
        const results = await Promise.all(
          userIds.map((id) =>
            apiRequest<AdminUserDetail>({
              method: "POST",
              url: `/admin/users/${id}/suspend`,
              data: { reason },
            }).then(() => 1).catch(() => 0)
          )
        );
        return { suspended: results.reduce((a, b) => a + b, 0) };
      },
    },
    analytics: {
      users: (params?: AdminAnalyticsParams) =>
        apiRequest<AdminUserAnalytics>({
          url: "/admin/analytics/users",
          params,
        }),
      content: (params?: AdminAnalyticsParams) =>
        apiRequest<AdminContentAnalytics>({
          url: "/admin/analytics/content",
          params,
        }),
      revenue: (params?: AdminAnalyticsParams) =>
        apiRequest<AdminRevenueAnalytics>({
          url: "/admin/analytics/revenue",
          params,
        }),
      system: () =>
        apiRequest<AdminSystemAnalytics>({
          url: "/admin/analytics/system",
        }),
    },
    content: {
      articles: (params?: AdminContentQueryParams) =>
        apiRequest<AdminArticleListResponse>({
          url: "/admin/content/articles",
          params,
        }),
      deleteArticle: (id: string) =>
        apiRequest<void>({
          method: "DELETE",
          url: `/admin/content/articles/${id}`,
        }),
      outlines: (params?: AdminContentQueryParams) =>
        apiRequest<AdminOutlineListResponse>({
          url: "/admin/content/outlines",
          params,
        }),
      deleteOutline: (id: string) =>
        apiRequest<void>({
          method: "DELETE",
          url: `/admin/content/outlines/${id}`,
        }),
      images: (params?: AdminContentQueryParams) =>
        apiRequest<AdminImageListResponse>({
          url: "/admin/content/images",
          params,
        }),
      deleteImage: (id: string) =>
        apiRequest<void>({
          method: "DELETE",
          url: `/admin/content/images/${id}`,
        }),
    },
    auditLogs: (params?: AdminAuditQueryParams) =>
      apiRequest<AdminAuditLogListResponse>({
        url: "/admin/audit-logs",
        params,
      }),
    generations: {
      list: (params?: AdminGenerationQueryParams) =>
        apiRequest<AdminGenerationListResponse>({
          url: "/admin/generations",
          params,
        }),
      stats: () =>
        apiRequest<AdminGenerationStats>({
          url: "/admin/generations/stats",
        }),
    },
    alerts: {
      list: (params?: AdminAlertQueryParams) =>
        apiRequest<AdminAlertListResponse>({
          url: "/admin/alerts",
          params,
        }),
      count: () =>
        apiRequest<AdminAlertCount>({
          url: "/admin/alerts/count",
        }),
      update: (id: string, data: { is_read?: boolean; is_resolved?: boolean }) =>
        apiRequest<AdminAlert>({
          method: "PUT",
          url: `/admin/alerts/${id}`,
          data,
        }),
      markAllRead: () =>
        apiRequest<{ message: string }>({
          method: "POST",
          url: "/admin/alerts/mark-all-read",
          data: {},
        }),
    },
  },

  // Projects (Multi-tenancy)
  projects: {
    list: async () => {
      const response = await cachedGet<{ projects: Project[]; total: number }>("/projects", 30_000);
      return response.projects;
    },
    get: (id: string) =>
      apiRequest<Project>({
        url: `/projects/${id}`,
      }),
    create: async (data: ProjectCreateRequest) => {
      const result = await apiRequest<Project>({
        method: "POST",
        url: "/projects",
        data,
      });
      invalidateCache("/projects");
      return result;
    },
    update: (id: string, data: ProjectUpdateRequest) =>
      apiRequest<Project>({
        method: "PUT",
        url: `/projects/${id}`,
        data,
      }),
    delete: (id: string) =>
      apiRequest<void>({
        method: "DELETE",
        url: `/projects/${id}`,
      }),
    switch: async (id: string | null) => {
      await apiRequest<void>({
        method: "POST",
        url: "/projects/switch",
        data: { project_id: id },
      });
      invalidateCache("/projects");
    },
    getCurrent: async (): Promise<Project | null> => {
      const response = await cachedGet<{ project: Project | null; is_personal_workspace: boolean }>("/projects/current", 30_000);
      if (response.project) {
        response.project.is_personal = response.is_personal_workspace || response.project.is_personal;
      }
      return response.project;
    },
    uploadLogo: (projectId: string, file: File) => {
      const formData = new FormData();
      formData.append("logo", file);
      return apiClient.post<Project>(`/projects/${projectId}/logo`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      }).then(res => res.data);
    },
    transferOwnership: (projectId: string, newOwnerId: string) =>
      apiRequest<void>({
        method: "POST",
        url: `/projects/${projectId}/transfer-ownership`,
        data: { new_owner_id: newOwnerId },
      }),
    leave: (projectId: string) =>
      apiRequest<void>({
        method: "POST",
        url: `/projects/${projectId}/leave`,
      }),

    getBrandVoice: () =>
      apiRequest<BrandVoiceSettings>({
        url: "/projects/current/brand-voice",
      }),
    updateBrandVoice: (data: BrandVoiceSettings) =>
      apiRequest<BrandVoiceSettings>({
        method: "PUT",
        url: "/projects/current/brand-voice",
        data,
      }),

    members: {
      list: (projectId: string) =>
        apiRequest<ProjectMember[]>({
          url: `/projects/${projectId}/members`,
        }),
      add: (projectId: string, data: ProjectMemberAddRequest) =>
        apiRequest<ProjectMember>({
          method: "POST",
          url: `/projects/${projectId}/members`,
          data,
        }),
      update: (projectId: string, userId: string, data: ProjectMemberUpdateRequest) =>
        apiRequest<ProjectMember>({
          method: "PUT",
          url: `/projects/${projectId}/members/${userId}`,
          data,
        }),
      remove: (projectId: string, userId: string) =>
        apiRequest<void>({
          method: "DELETE",
          url: `/projects/${projectId}/members/${userId}`,
        }),
    },

    invitations: {
      list: (projectId: string) =>
        apiRequest<ProjectInvitation[]>({
          url: `/projects/${projectId}/invitations`,
        }),
      create: (projectId: string, data: ProjectInvitationCreateRequest) =>
        apiRequest<ProjectInvitation>({
          method: "POST",
          url: `/projects/${projectId}/invitations`,
          data,
        }),
      revoke: (projectId: string, invitationId: string) =>
        apiRequest<void>({
          method: "DELETE",
          url: `/projects/${projectId}/invitations/${invitationId}`,
        }),
      resend: (projectId: string, invitationId: string) =>
        apiRequest<ProjectInvitation>({
          method: "POST",
          url: `/projects/${projectId}/invitations/${invitationId}/resend`,
        }),
      getByToken: (token: string) =>
        apiRequest<ProjectInvitationPublic>({
          url: `/projects/invitations/${token}`,
        }),
      accept: (token: string) =>
        apiRequest<void>({
          method: "POST",
          url: `/projects/invitations/${token}/accept`,
        }),
    },

    billing: {
      subscription: (projectId: string) =>
        apiRequest<ProjectSubscription>({
          url: `/projects/${projectId}/billing/subscription`,
        }),
      checkout: (projectId: string, variantId: string) =>
        apiRequest<{ checkout_url: string }>({
          method: "POST",
          url: `/projects/${projectId}/billing/checkout`,
          data: { variant_id: variantId },
        }),
      portal: (projectId: string) =>
        apiRequest<{ portal_url: string }>({
          url: `/projects/${projectId}/billing/portal`,
        }),
      cancel: (projectId: string) =>
        apiRequest<void>({
          method: "POST",
          url: `/projects/${projectId}/billing/cancel`,
        }),
      usage: (projectId: string) =>
        apiRequest<ProjectUsage>({
          url: `/projects/${projectId}/billing/usage`,
        }),
    },
  },

  // Notifications
  notifications: {
    generationStatus: () =>
      apiRequest<GenerationStatusResponse>({
        url: "/notifications/generation-status",
      }),
  },

  // Background task status polling
  tasks: {
    getStatus: (taskId: string) =>
      apiRequest<TaskStatus>({
        url: `/notifications/tasks/${taskId}/status`,
      }),
  },

  // Agency / White-Label
  agency: {
    // Profile
    getProfile: () =>
      apiRequest<AgencyProfile>({
        url: "/agency/profile",
      }),
    createProfile: (data: { agency_name: string; logo_url?: string; brand_colors?: Record<string, string>; contact_email?: string; footer_text?: string }) =>
      apiRequest<AgencyProfile>({
        method: "POST",
        url: "/agency/profile",
        data,
      }),
    updateProfile: (data: { agency_name?: string; logo_url?: string; brand_colors?: Record<string, string>; contact_email?: string; footer_text?: string }) =>
      apiRequest<AgencyProfile>({
        method: "PUT",
        url: "/agency/profile",
        data,
      }),
    deleteProfile: () =>
      apiRequest<{ message: string }>({
        method: "DELETE",
        url: "/agency/profile",
      }),
    // Clients
    clients: () =>
      apiRequest<{ items: ClientWorkspace[]; total: number }>({
        url: "/agency/clients",
      }),
    createClient: (data: { project_id: string; client_name: string; client_email?: string; client_logo_url?: string; allowed_features?: Record<string, boolean> }) =>
      apiRequest<ClientWorkspace>({
        method: "POST",
        url: "/agency/clients",
        data,
      }),
    getClient: (id: string) =>
      apiRequest<ClientWorkspace>({
        url: `/agency/clients/${id}`,
      }),
    updateClient: (id: string, data: { client_name?: string; client_email?: string; client_logo_url?: string; is_portal_enabled?: boolean; allowed_features?: Record<string, boolean> }) =>
      apiRequest<ClientWorkspace>({
        method: "PUT",
        url: `/agency/clients/${id}`,
        data,
      }),
    deleteClient: (id: string) =>
      apiRequest<{ message: string }>({
        method: "DELETE",
        url: `/agency/clients/${id}`,
      }),
    enablePortal: (id: string) =>
      apiRequest<ClientWorkspace>({
        method: "POST",
        url: `/agency/clients/${id}/enable-portal`,
      }),
    disablePortal: (id: string) =>
      apiRequest<ClientWorkspace>({
        method: "POST",
        url: `/agency/clients/${id}/disable-portal`,
      }),
    // Templates
    reportTemplates: () =>
      apiRequest<{ items: AgencyReportTemplate[]; total: number }>({
        url: "/agency/templates",
      }),
    createReportTemplate: (data: { name: string; template_config: Record<string, unknown> }) =>
      apiRequest<AgencyReportTemplate>({
        method: "POST",
        url: "/agency/templates",
        data,
      }),
    updateReportTemplate: (id: string, data: { name?: string; template_config?: Record<string, unknown> }) =>
      apiRequest<AgencyReportTemplate>({
        method: "PUT",
        url: `/agency/templates/${id}`,
        data,
      }),
    deleteReportTemplate: (id: string) =>
      apiRequest<{ message: string }>({
        method: "DELETE",
        url: `/agency/templates/${id}`,
      }),
    // Reports
    generateReport: (data: { client_workspace_id: string; report_template_id?: string; report_type?: string; period_start: string; period_end: string }) =>
      apiRequest<GeneratedReport>({
        method: "POST",
        url: "/agency/reports/generate",
        data,
        timeout: 60000,
      }),
    reports: (params?: { page?: number; page_size?: number }) =>
      apiRequest<{ items: GeneratedReport[]; total: number; page: number; page_size: number; pages: number }>({
        url: "/agency/reports",
        params,
      }),
    getReport: (id: string) =>
      apiRequest<GeneratedReport>({
        url: `/agency/reports/${id}`,
      }),
    // Portal (public)
    portal: (token: string) =>
      apiRequest<PortalData>({
        url: `/agency/portal/${token}`,
      }),
  },
};

// Type definitions

// Auth types
export interface UserResponse {
  id: string;
  email: string;
  name: string;
  avatar_url?: string;
  role: string;
  email_verified: boolean;
  subscription_tier: string;
  subscription_status: string;
  language: string;
  timezone: string;
  created_at: string;
  last_login?: string;
  articles_generated_this_month: number;
  outlines_generated_this_month: number;
  images_generated_this_month: number;
}

export interface Outline {
  id: string;
  user_id: string;
  project_id?: string;
  title: string;
  keyword: string;
  target_audience?: string;
  tone: string;
  status: "draft" | "generating" | "completed" | "failed";
  sections: OutlineSection[];
  word_count_target: number;
  estimated_read_time?: number;
  ai_model?: string;
  created_at: string;
  updated_at: string;
}

export interface OutlineSection {
  heading: string;
  subheadings: string[];
  notes: string;
  word_count_target: number;
}

export interface CreateOutlineInput {
  keyword: string;
  target_audience?: string;
  tone?: string;
  word_count_target?: number;
  language?: string;
  auto_generate?: boolean;
  project_id?: string;
}

export interface UpdateOutlineInput {
  title?: string;
  keyword?: string;
  target_audience?: string;
  tone?: string;
  sections?: OutlineSection[];
  word_count_target?: number;
}

export interface OutlineListResponse {
  items: Outline[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface SEOAnalysis {
  score: number;
  keyword_density: number;
  title_has_keyword: boolean;
  meta_description_length: number;
  headings_structure: string;
  h2_count: number;
  h3_count: number;
  internal_links: number;
  external_links: number;
  image_alt_texts: boolean;
  readability_score: number;
  suggestions: string[];
}

export interface Article {
  id: string;
  user_id: string;
  project_id?: string;
  outline_id?: string;
  title: string;
  slug?: string;
  keyword: string;
  meta_description?: string;
  content?: string;
  content_html?: string;
  status: "draft" | "generating" | "completed" | "published" | "failed";
  word_count: number;
  read_time?: number;
  seo_score?: number;
  seo_analysis?: SEOAnalysis;
  ai_model?: string;
  published_at?: string;
  published_url?: string;
  featured_image_id?: string;
  image_prompt?: string;
  wordpress_post_id?: number;
  wordpress_post_url?: string;
  social_posts?: SocialPostsData;
  created_at: string;
  updated_at: string;
}

// -------------------------------------------------------------------------
// Article revision types
// -------------------------------------------------------------------------

export interface ArticleRevision {
  id: string;
  article_id: string;
  revision_type: string;
  word_count: number;
  created_at: string;
}

export interface ArticleRevisionDetail extends ArticleRevision {
  content?: string;
  content_html?: string;
  title: string;
  meta_description?: string;
}

export interface ArticleRevisionListResponse {
  items: ArticleRevision[];
  total: number;
}

// -------------------------------------------------------------------------
// Internal linking suggestion types
// -------------------------------------------------------------------------

export interface LinkSuggestion {
  id: string;
  title: string;
  keyword: string;
  slug: string | null;
  relevance_score: number;
}

export interface LinkSuggestionsResponse {
  suggestions: LinkSuggestion[];
}

// -------------------------------------------------------------------------

export interface SocialPostContent {
  text: string;
  generated_at?: string;
}

export interface SocialPostsData {
  twitter?: SocialPostContent;
  linkedin?: SocialPostContent;
  facebook?: SocialPostContent;
  instagram?: SocialPostContent;
}

export interface CreateArticleInput {
  title: string;
  keyword: string;
  content?: string;
  meta_description?: string;
  outline_id?: string;
  project_id?: string;
}

export interface GenerateArticleInput {
  outline_id: string;
  tone?: string;
  target_audience?: string;
  writing_style?: string;
  voice?: string;
  list_usage?: string;
  custom_instructions?: string;
  language?: string;
}

export interface UpdateArticleInput {
  title?: string;
  keyword?: string;
  meta_description?: string;
  content?: string;
  status?: string;
}

export interface ArticleListResponse {
  items: Article[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ContentHealthArticle {
  id: string;
  title: string;
  seo_score?: number;
  keyword: string;
}

export interface ContentHealthSummary {
  total_articles: number;
  avg_seo_score: number | null;
  excellent_count: number;
  good_count: number;
  needs_work_count: number;
  no_score_count: number;
  needs_work: ContentHealthArticle[];
  no_score: ContentHealthArticle[];
}

export interface KeywordSuggestion {
  keyword: string;
  intent: "informational" | "commercial" | "transactional" | "navigational";
  difficulty: "low" | "medium" | "high";
  content_angle: string;
}

export interface KeywordSuggestionsResponse {
  seed_keyword: string;
  suggestions: KeywordSuggestion[];
}

export interface GeneratedImage {
  id: string;
  user_id: string;
  project_id?: string;
  article_id?: string;
  prompt: string;
  url: string;
  local_path?: string;
  alt_text?: string;
  style?: string;
  model?: string;
  width?: number;
  height?: number;
  status: string;
  created_at: string;
}

export interface GenerateImageInput {
  prompt: string;
  article_id?: string;
  style?: string;
  width?: number;
  height?: number;
  project_id?: string;
}

// WordPress types
export interface WordPressConnectInput {
  site_url: string;
  username: string;
  app_password: string;
}

export interface WordPressConnection {
  id: string;
  user_id: string;
  site_url: string;
  username: string;
  site_name?: string;
  connected_at: string;
}

export interface WordPressConnectionStatus {
  is_connected: boolean;
  site_url?: string;
  username?: string;
  site_name?: string;
  connected_at?: string;
  last_tested_at?: string;
  connection_valid?: boolean;
  error_message?: string;
}

export interface WordPressCategory {
  id: number;
  name: string;
  slug: string;
  count: number;
}

export interface WordPressTag {
  id: number;
  name: string;
  slug: string;
  count: number;
}

export interface WordPressPublishInput {
  article_id: string;
  status: "draft" | "publish";
  categories?: number[];
  tags?: number[];
}

export interface WordPressPublishResponse {
  success: boolean;
  post_id: number;
  post_url: string;
  message?: string;
}

export interface WordPressMediaUploadInput {
  image_id: string;
  title?: string;
  alt_text?: string;
}

export interface WordPressMediaUploadResponse {
  wordpress_media_id: number;
  wordpress_url: string;
  source_url: string;
  message: string;
}

// Analytics / GSC types
export interface GSCAuthUrlResponse {
  auth_url: string;
  state: string;
}

export interface GSCStatus {
  connected: boolean;
  site_url?: string;
  last_sync?: string;
  connected_at?: string;
}

export interface GSCSite {
  site_url: string;
  permission_level: string;
}

export interface GSCSiteListResponse {
  sites: GSCSite[];
}

export interface GSCDisconnectResponse {
  message: string;
  disconnected_at: string;
}

export interface GSCSyncResponse {
  message: string;
  site_url: string;
  sync_started_at: string;
}

export interface AnalyticsQueryParams {
  start_date?: string;
  end_date?: string;
  page?: number;
  page_size?: number;
  keyword?: string;
  page_url?: string;
}

export interface KeywordRanking {
  id: string;
  keyword: string;
  date: string;
  clicks: number;
  impressions: number;
  ctr: number;
  position: number;
  position_change?: number;
  created_at: string;
}

export interface KeywordRankingListResponse {
  items: KeywordRanking[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface PagePerformance {
  id: string;
  page_url: string;
  date: string;
  clicks: number;
  impressions: number;
  ctr: number;
  position: number;
  position_change?: number;
  created_at: string;
}

export interface PagePerformanceListResponse {
  items: PagePerformance[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface DailyAnalyticsData {
  id: string;
  date: string;
  total_clicks: number;
  total_impressions: number;
  avg_ctr: number;
  avg_position: number;
  created_at: string;
}

export interface DailyAnalyticsListResponse {
  items: DailyAnalyticsData[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface TrendData {
  current: number;
  previous: number;
  change_percent: number;
  trend: "up" | "down" | "stable";
}

export interface AnalyticsSummary {
  total_clicks: number;
  total_impressions: number;
  avg_ctr: number;
  avg_position: number;
  clicks_trend?: TrendData;
  impressions_trend?: TrendData;
  ctr_trend?: TrendData;
  position_trend?: TrendData;
  top_keywords: KeywordRanking[];
  top_pages: PagePerformance[];
  start_date: string;
  end_date: string;
  site_url: string;
}

// Article Performance types
export interface ArticlePerformanceParams {
  page?: number;
  page_size?: number;
  start_date?: string;
  end_date?: string;
  sort_by?: "total_clicks" | "total_impressions" | "avg_position" | "avg_ctr" | "published_at";
  sort_order?: "asc" | "desc";
}

export interface ArticlePerformanceItem {
  article_id: string;
  title: string;
  keyword: string;
  published_url: string;
  published_at?: string;
  seo_score?: number;
  total_clicks: number;
  total_impressions: number;
  avg_ctr: number;
  avg_position: number;
  clicks_trend?: TrendData;
  position_trend?: TrendData;
  performance_status: "improving" | "declining" | "neutral" | "new";
}

export interface ArticlePerformanceListResponse {
  items: ArticlePerformanceItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
  total_published_articles: number;
  articles_with_data: number;
}

export interface ArticleDailyPerformance {
  date: string;
  clicks: number;
  impressions: number;
  ctr: number;
  position: number;
}

export interface ArticlePerformanceDetailResponse {
  article_id: string;
  title: string;
  keyword: string;
  published_url: string;
  published_at?: string;
  seo_score?: number;
  total_clicks: number;
  total_impressions: number;
  avg_ctr: number;
  avg_position: number;
  clicks_trend?: TrendData;
  impressions_trend?: TrendData;
  ctr_trend?: TrendData;
  position_trend?: TrendData;
  daily_data: ArticleDailyPerformance[];
  start_date: string;
  end_date: string;
}

// Content Opportunities types
export interface KeywordOpportunity {
  keyword: string;
  clicks: number;
  impressions: number;
  ctr: number;
  position: number;
  opportunity_type: "quick_win" | "content_gap" | "rising";
  position_change: number;
  has_existing_article: boolean;
  existing_article_id?: string;
}

export interface ContentOpportunitiesResponse {
  quick_wins: KeywordOpportunity[];
  content_gaps: KeywordOpportunity[];
  rising_keywords: KeywordOpportunity[];
  total_opportunities: number;
  start_date: string;
  end_date: string;
}

export interface ContentSuggestion {
  suggested_title: string;
  target_keyword: string;
  content_angle: string;
  rationale: string;
  estimated_difficulty: "easy" | "medium" | "hard";
  estimated_word_count: number;
}

export interface ContentSuggestionsResponse {
  suggestions: ContentSuggestion[];
  based_on_keywords: string[];
}

// Content Decay / Content Health types
export interface ContentDecayAlert {
  id: string;
  user_id: string;
  project_id?: string;
  article_id?: string;
  alert_type: "position_drop" | "traffic_drop" | "ctr_drop" | "impressions_drop";
  severity: "warning" | "critical";
  keyword?: string;
  page_url?: string;
  metric_name: string;
  metric_before: number;
  metric_after: number;
  period_days: number;
  percentage_change: number;
  suggested_actions?: {
    suggestions: Array<{
      action: string;
      description: string;
      priority: "high" | "medium" | "low";
      estimated_impact: "high" | "medium" | "low";
    }>;
  };
  is_read: boolean;
  is_resolved: boolean;
  resolved_at?: string;
  created_at: string;
  article_title?: string;
}

export interface ContentDecayAlertListResponse {
  items: ContentDecayAlert[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ContentHealthSummary2 {
  health_score: number;
  total_published_articles: number;
  declining_articles: number;
  active_warnings: number;
  active_criticals: number;
  total_active_alerts: number;
  recent_alerts: ContentDecayAlert[];
}

export interface DecayRecoverySuggestions {
  suggestions: Array<{
    action: string;
    description: string;
    priority: "high" | "medium" | "low";
    estimated_impact: "high" | "medium" | "low";
  }>;
}

export interface DecayDetectionResponse {
  message: string;
  new_alerts: number;
}

export interface DecayAlertsParams {
  page?: number;
  page_size?: number;
  alert_type?: string;
  severity?: string;
  is_resolved?: boolean;
  sort_by?: string;
  sort_order?: "asc" | "desc";
}

// AEO (Answer Engine Optimization) types
export interface AEOScoreBreakdown {
  structure_score: number;
  faq_score: number;
  entity_score: number;
  conciseness_score: number;
  schema_score: number;
  citation_readiness: number;
}

export interface AEOScore {
  id: string;
  article_id: string;
  aeo_score: number;
  score_breakdown?: AEOScoreBreakdown;
  suggestions?: Array<{
    action: string;
    description: string;
    category?: string;
    estimated_impact?: "high" | "medium" | "low";
  }>;
  previous_score?: number;
  scored_at: string;
}

export interface AEOArticleSummary {
  article_id: string;
  title: string;
  keyword: string;
  aeo_score: number;
  score_breakdown?: Record<string, number>;
}

export interface AEOOverviewResponse {
  total_scored: number;
  average_score: number;
  excellent_count: number;
  good_count: number;
  needs_work_count: number;
  score_distribution: Record<string, number>;
  top_articles: AEOArticleSummary[];
  bottom_articles: AEOArticleSummary[];
}

export interface AEOSuggestionsResponse {
  suggestions: Array<{
    action: string;
    description: string;
    category?: string;
    estimated_impact?: "high" | "medium" | "low";
  }>;
}

// Revenue Attribution types
export interface ConversionGoal {
  id: string;
  user_id: string;
  project_id: string | null;
  name: string;
  goal_type: string;
  goal_config: Record<string, unknown> | null;
  is_active: boolean;
  created_at: string;
}

export interface ConversionGoalListResponse {
  items: ConversionGoal[];
  total: number;
}

export interface RevenueOverview {
  total_organic_visits: number;
  total_conversions: number;
  total_revenue: number;
  conversion_rate: number;
  active_goals: number;
  top_articles: Array<{ article_id: string; title: string; revenue: number; visits: number }>;
  top_keywords: Array<{ keyword: string; revenue: number; visits: number }>;
  visits_trend: TrendData | null;
  conversions_trend: TrendData | null;
  revenue_trend: TrendData | null;
  start_date: string;
  end_date: string;
}

export interface RevenueByArticleItem {
  article_id: string;
  title: string;
  keyword: string;
  published_url: string | null;
  visits: number;
  conversions: number;
  revenue: number;
  conversion_rate: number;
}

export interface RevenueByArticleListResponse {
  items: RevenueByArticleItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface RevenueByKeywordItem {
  keyword: string;
  visits: number;
  conversions: number;
  revenue: number;
  conversion_rate: number;
}

export interface RevenueByKeywordListResponse {
  items: RevenueByKeywordItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ImportConversionsResponse {
  imported_count: number;
  matched_articles: number;
  message: string;
}

export interface RevenueReport {
  id: string;
  report_type: string;
  period_start: string;
  period_end: string;
  total_organic_visits: number;
  total_conversions: number;
  total_revenue: number;
  top_articles: unknown[] | null;
  top_keywords: unknown[] | null;
  generated_at: string;
}

// Device / Country Breakdown types
export interface DeviceBreakdownItem {
  device: string;
  clicks: number;
  impressions: number;
  ctr: number;
  position: number;
}

export interface CountryBreakdownItem {
  country: string;
  clicks: number;
  impressions: number;
  ctr: number;
  position: number;
}

// Bulk Content types
export interface BulkKeywordInput {
  keyword: string;
  title?: string;
  target_audience?: string;
}

export interface TemplateConfig {
  tone: string;
  writing_style: string;
  word_count_target: number;
  target_audience: string;
  custom_instructions: string;
  include_faq: boolean;
  include_conclusion: boolean;
  language: string;
}

export interface ContentTemplate {
  id: string;
  name: string;
  description?: string;
  template_config: TemplateConfig;
  created_at: string;
  updated_at: string;
}

export interface TemplateListResponse {
  items: ContentTemplate[];
  total: number;
}

export interface BulkJobItem {
  id: string;
  keyword?: string;
  title?: string;
  status: "pending" | "processing" | "completed" | "failed" | "cancelled";
  resource_type?: string;
  resource_id?: string;
  error_message?: string;
  processing_started_at?: string;
  processing_completed_at?: string;
}

export interface BulkJob {
  id: string;
  job_type: string;
  status: "pending" | "processing" | "completed" | "partially_failed" | "failed" | "cancelled";
  total_items: number;
  completed_items: number;
  failed_items: number;
  template_id?: string;
  started_at?: string;
  completed_at?: string;
  error_summary?: string;
  created_at: string;
}

export interface BulkJobDetail extends BulkJob {
  items: BulkJobItem[];
}

export interface BulkJobListResponse {
  items: BulkJob[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

// Billing / LemonSqueezy types
export interface PlanLimits {
  articles_per_month: number;
  outlines_per_month: number;
  images_per_month: number;
}

export interface PlanInfo {
  id: string;
  name: string;
  price_monthly: number;
  price_yearly: number;
  features: string[];
  limits: PlanLimits;
}

export interface PricingResponse {
  plans: PlanInfo[];
}

export interface SubscriptionStatus {
  subscription_tier: string;
  subscription_status: string;
  subscription_expires: string | null;
  customer_id: string | null;
  can_manage: boolean;
  articles_generated_this_month: number;
  outlines_generated_this_month: number;
  images_generated_this_month: number;
  usage_reset_date: string | null;
}

export interface CheckoutResponse {
  checkout_url: string;
}

export interface CustomerPortalResponse {
  portal_url: string;
}

// Knowledge Vault types
export interface KnowledgeSource {
  id: string;
  user_id?: string;
  project_id?: string;
  title: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: "pending" | "processing" | "completed" | "failed";
  chunk_count: number;
  char_count: number;
  description: string | null;
  tags: string[];
  created_at: string;
  error_message?: string;
}

export interface KnowledgeSourceList {
  items: KnowledgeSource[];
  total: number;
  page: number;
  page_size: number;
}

export interface SourceSnippet {
  source_id: string;
  source_title: string;
  content: string;
  relevance_score: number;
}

export interface QueryResponse {
  query: string;
  answer: string;
  sources: SourceSnippet[];
  query_time_ms: number;
}

export interface KnowledgeStats {
  total_sources: number;
  total_chunks: number;
  total_characters: number;
  total_queries: number;
  storage_used_mb: number;
}

// Social Media types
export type SocialPlatform = "twitter" | "linkedin" | "facebook" | "instagram";
export type SocialPostStatus = "pending" | "queued" | "posting" | "posted" | "failed" | "cancelled";

export interface SocialAccount {
  id: string;
  platform: SocialPlatform;
  username: string;
  display_name: string;
  profile_image_url?: string;
  is_connected: boolean;
  connected_at: string;
  last_error?: string;
}

export interface SocialAccountListResponse {
  accounts: SocialAccount[];
}

export interface ConnectSocialAccountInput {
  platform: SocialPlatform;
  access_token: string;
  refresh_token?: string;
  username: string;
  display_name?: string;
}

export interface SocialPostTarget {
  id: string;
  account_id: string;
  platform: SocialPlatform;
  status: SocialPostStatus;
  posted_url?: string;
  posted_at?: string;
  error_message?: string;
}

export interface SocialPost {
  id: string;
  user_id: string;
  project_id?: string;
  content: string;
  media_urls?: string[];
  scheduled_at: string;
  status: SocialPostStatus;
  platforms: SocialPlatform[];
  targets: SocialPostTarget[];
  created_at: string;
  updated_at: string;
  published_at?: string;
}

export interface SocialPostListResponse {
  items: SocialPost[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface SocialPostQueryParams {
  page?: number;
  page_size?: number;
  status?: SocialPostStatus;
  platform?: SocialPlatform;
  start_date?: string;
  end_date?: string;
  search?: string;
}

export interface CreateSocialPostInput {
  content: string;
  media_urls?: string[];
  scheduled_at: string;
  platforms: SocialPlatform[];
  account_ids?: string[];
  project_id?: string;
}

export interface UpdateSocialPostInput {
  content?: string;
  media_urls?: string[];
  scheduled_at?: string;
  platforms?: SocialPlatform[];
}

export interface SocialAnalytics {
  post_id: string;
  platform: SocialPlatform;
  likes: number;
  comments: number;
  shares: number;
  impressions: number;
  engagement_rate: number;
  click_through_rate?: number;
  fetched_at: string;
}

// Agency / White-Label types
export interface AgencyProfile {
  id: string;
  user_id: string;
  agency_name: string;
  logo_url: string | null;
  brand_colors: Record<string, string> | null;
  custom_domain: string | null;
  contact_email: string | null;
  footer_text: string | null;
  max_clients: number;
  is_active: boolean;
  created_at: string;
}

export interface ClientWorkspace {
  id: string;
  agency_id: string;
  project_id: string;
  client_name: string;
  client_email: string | null;
  client_logo_url: string | null;
  is_portal_enabled: boolean;
  portal_access_token: string | null;
  allowed_features: Record<string, boolean> | null;
  created_at: string;
}

export interface AgencyReportTemplate {
  id: string;
  agency_id: string;
  name: string;
  template_config: Record<string, unknown>;
  created_at: string;
}

export interface GeneratedReport {
  id: string;
  agency_id: string;
  client_workspace_id: string;
  report_template_id: string | null;
  report_type: string;
  period_start: string;
  period_end: string;
  report_data: Record<string, unknown> | null;
  pdf_url: string | null;
  generated_at: string;
}

export interface PortalData {
  client_name: string;
  client_logo_url: string | null;
  agency_name: string;
  agency_logo_url: string | null;
  brand_colors: Record<string, string> | null;
  contact_email: string | null;
  footer_text: string | null;
  allowed_features: Record<string, boolean> | null;
  analytics_summary: Record<string, unknown> | null;
}

// Admin types
export interface AdminDashboardStats {
  users: {
    total_users: number;
    new_users_this_week: number;
    new_users_this_month: number;
    active_users_this_week: number;
    verified_users: number;
    pending_users: number;
  };
  content: {
    total_articles: number;
    total_outlines: number;
    total_images: number;
    articles_this_month: number;
    outlines_this_month: number;
    images_this_month: number;
  };
  subscriptions: {
    free_tier: number;
    starter_tier: number;
    professional_tier: number;
    enterprise_tier: number;
    active_subscriptions: number;
    cancelled_subscriptions: number;
  };
  revenue: {
    monthly_recurring_revenue: number;
    annual_recurring_revenue: number;
    revenue_this_month: number;
  };
  platform_usage_7d: Array<{ date: string; value: number }>;
  platform_usage_30d: Array<{ date: string; value: number }>;
}

export interface AdminUserQueryParams {
  page?: number;
  page_size?: number;
  search?: string;
  role?: string;
  subscription_tier?: string;
  status?: string;
  sort_by?: string;
  sort_order?: "asc" | "desc";
}

export interface AdminUserDetail {
  id: string;
  email: string;
  name: string;
  role: string;
  subscription_tier: string;
  subscription_status: string;
  subscription_expires: string | null;
  created_at: string;
  updated_at: string;
  last_login?: string;
  is_suspended: boolean;
  suspension_reason?: string;
  total_articles: number;
  total_outlines: number;
  total_images: number;
  storage_used_mb: number;
  lemonsqueezy_customer_id?: string;
}

export interface AdminUserListResponse {
  users: AdminUserDetail[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AdminUpdateUserInput {
  email?: string;
  name?: string;
  role?: string;
  subscription_tier?: string;
}

export interface AdminAnalyticsParams {
  start_date?: string;
  end_date?: string;
}

export interface AdminUserAnalytics {
  total_users: number;
  new_users: number;
  active_users: number;
  churned_users: number;
  users_by_tier: Array<{ tier: string; count: number }>;
  users_by_month: Array<{ month: string; count: number }>;
  retention_rate: number;
}

export interface AdminContentAnalytics {
  total_articles: number;
  total_outlines: number;
  total_images: number;
  content_by_month: Array<{ month: string; articles: number; outlines: number; images: number }>;
  top_creators: Array<{ user_id: string; user_name: string; article_count: number }>;
  avg_articles_per_user: number;
}

export interface AdminRevenueAnalytics {
  total_revenue: number;
  monthly_recurring_revenue: number;
  average_revenue_per_user: number;
  revenue_by_month: Array<{ month: string; revenue: number }>;
  revenue_by_tier: Array<{ tier: string; revenue: number; count: number }>;
  lifetime_value: number;
}

export interface AdminSystemAnalytics {
  database_size_mb: number;
  storage_used_gb: number;
  api_requests_today: number;
  error_rate: number;
  avg_response_time_ms: number;
  uptime_percentage: number;
}

export interface AdminContentQueryParams {
  page?: number;
  page_size?: number;
  search?: string;
  user_id?: string;
  status?: string;
  start_date?: string;
  end_date?: string;
}

export interface AdminArticleListResponse {
  items: Article[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AdminOutlineListResponse {
  items: Outline[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AdminImageListResponse {
  items: GeneratedImage[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AdminAuditQueryParams {
  page?: number;
  page_size?: number;
  user_id?: string;
  action?: string;
  resource_type?: string;
  start_date?: string;
  end_date?: string;
}

export interface AdminAuditLog {
  id: string;
  user_id: string;
  user_email: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  ip_address?: string;
  user_agent?: string;
  details?: Record<string, unknown>;
  created_at: string;
}

export interface AdminAuditLogListResponse {
  logs: AdminAuditLog[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AdminGenerationQueryParams {
  page?: number;
  page_size?: number;
  resource_type?: string;
  status?: string;
  user_id?: string;
}

export interface AdminGenerationLog {
  id: string;
  user_id: string;
  user_email?: string;
  resource_type: string;
  resource_id?: string;
  status: string;
  duration_ms?: number;
  cost_credits?: number;
  error_message?: string;
  created_at: string;
}

export interface AdminGenerationListResponse {
  items: AdminGenerationLog[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AdminGenerationStats {
  total_generations: number;
  successful: number;
  failed: number;
  success_rate: number;
  articles_generated: number;
  outlines_generated: number;
  images_generated: number;
  articles_failed: number;
  outlines_failed: number;
  images_failed: number;
  avg_duration_ms: number | null;
  total_credits: number;
}

export interface AdminAlertQueryParams {
  page?: number;
  page_size?: number;
  is_read?: boolean;
  severity?: string;
  alert_type?: string;
}

export interface AdminAlert {
  id: string;
  title: string;
  message: string | null;
  severity: string;
  alert_type?: string;
  resource_type?: string;
  resource_id?: string;
  user_id?: string;
  user_email?: string;
  is_read: boolean;
  is_resolved: boolean;
  created_at: string;

}

export interface AdminAlertListResponse {
  items: AdminAlert[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AdminAlertCount {
  unread_count: number;
  critical_count: number;
}

// Projects (Multi-tenancy) types
export type ProjectRole = "owner" | "admin" | "member" | "viewer";
export type ProjectSubscriptionTier = "free" | "starter" | "professional" | "enterprise";

export interface Project {
  id: string;
  name: string;
  slug: string;
  description?: string;
  logo_url?: string;
  is_personal?: boolean;
  subscription_tier: ProjectSubscriptionTier;
  my_role: ProjectRole;
  member_count: number;
  created_at: string;
  updated_at: string;
}

export interface BrandVoiceSettings {
  tone?: string;
  writing_style?: string;
  target_audience?: string;
  custom_instructions?: string;
  language?: string;
}

export interface ProjectMember {
  id: string;
  user_id: string;
  email: string;
  name: string;
  avatar_url?: string;
  role: ProjectRole;
  joined_at: string;
}

export interface ProjectInvitation {
  id: string;
  email: string;
  role: ProjectRole;
  status: "pending" | "accepted" | "expired" | "revoked";
  expires_at: string;
  invited_by: string;
  invited_by_name: string;
  created_at: string;
}

export interface ProjectInvitationPublic {
  project_name: string;
  project_slug: string;
  project_logo_url?: string;
  inviter_name: string;
  role: ProjectRole;
  expires_at: string;
  is_expired: boolean;
  is_already_member: boolean;
}

export interface ProjectCreateRequest {
  name: string;
  slug?: string;
  description?: string;
}

export interface ProjectUpdateRequest {
  name?: string;
  slug?: string;
  description?: string;
  logo_url?: string;
}

export interface ProjectMemberAddRequest {
  user_id: string;
  role: ProjectRole;
}

export interface ProjectMemberUpdateRequest {
  role: ProjectRole;
}

export interface ProjectInvitationCreateRequest {
  email: string;
  role: ProjectRole;
}

export interface ProjectSubscription {
  subscription_tier: ProjectSubscriptionTier;
  subscription_status: string;
  subscription_expires: string | null;
  can_manage: boolean;
  usage: {
    articles_used: number;
    outlines_used: number;
    images_used: number;
  };
  limits: {
    articles_per_month: number;
    outlines_per_month: number;
    images_per_month: number;
  };
}

export interface ProjectUsage {
  period_start: string;
  period_end: string;
  articles_used: number;
  outlines_used: number;
  images_used: number;
  articles_limit: number;
  outlines_limit: number;
  images_limit: number;
}

// Notification types
export interface GenerationNotification {
  id: string;
  type: "article" | "outline" | "image";
  resource_id: string;
  title: string;
  status: "completed" | "failed";
  timestamp: string;
}

export interface GenerationStatusResponse {
  notifications: GenerationNotification[];
}

/**
 * Status snapshot returned by GET /notifications/tasks/{task_id}/status
 * Reflects the in-memory TaskQueue record (not the DB row).
 */
export interface TaskStatus {
  task_id: string;
  /** "running" | "completed" | "failed" */
  status: "running" | "completed" | "failed";
  result: unknown | null;
  error: string | null;
  created_at: string;
  completed_at: string | null;
}
