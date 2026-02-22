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

function forceLogout() {
  localStorage.removeItem("auth_token");
  localStorage.removeItem("refresh_token");
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
        return new Promise((resolve, reject) => {
          failedQueue.push({
            resolve: (token: string) => {
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
    me: () =>
      apiRequest<UserResponse>({
        url: "/auth/me",
      }),
    refresh: (refreshToken: string) =>
      apiRequest<{ access_token: string; refresh_token: string; token_type: string; expires_in: number }>({
        method: "POST",
        url: "/auth/refresh",
        data: { refresh_token: refreshToken },
      }),
    logout: async (): Promise<void> => {
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
    updateProfile: (data: { name?: string; language?: string; timezone?: string }) =>
      apiRequest<UserResponse>({
        method: "PUT",
        url: "/auth/me",
        data,
      }),
    changePassword: (currentPassword: string, newPassword: string) =>
      apiRequest<{ message: string }>({
        method: "POST",
        url: "/auth/password/change",
        data: { current_password: currentPassword, new_password: newPassword },
      }),
  },

  // Outlines
  outlines: {
    list: (params?: { page?: number; page_size?: number; status?: string; keyword?: string; team_id?: string }) =>
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
    regenerate: (id: string) =>
      apiRequest<Outline>({
        method: "POST",
        url: `/outlines/${id}/regenerate`,
        timeout: AI_TIMEOUT,
      }),
  },

  // Articles
  articles: {
    list: (params?: { page?: number; page_size?: number; status?: string; keyword?: string; team_id?: string }) =>
      apiRequest<ArticleListResponse>({
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
    generate: (data: GenerateArticleInput) =>
      apiRequest<Article>({
        method: "POST",
        url: "/articles/generate",
        data,
        timeout: AI_TIMEOUT,
      }),
    update: (id: string, data: UpdateArticleInput) =>
      apiRequest<Article>({
        method: "PUT",
        url: `/articles/${id}`,
        data,
      }),
    delete: (id: string) =>
      apiRequest<void>({
        method: "DELETE",
        url: `/articles/${id}`,
      }),
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
  },

  // Images
  images: {
    list: (params?: { page?: number; page_size?: number; team_id?: string }) =>
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
        timeout: AI_TIMEOUT,
      }),
    delete: (id: string) =>
      apiRequest<void>({
        method: "DELETE",
        url: `/images/${id}`,
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
        url: "/analytics/gsc/callback",
        params: { code, state },
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
  },

  // Billing / LemonSqueezy
  billing: {
    pricing: () =>
      apiRequest<PricingResponse>({
        url: "/billing/pricing",
      }),
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
      apiRequest<void>({
        method: "POST",
        url: "/billing/cancel",
      }),
  },

  // Knowledge Vault
  knowledge: {
    upload: (file: File, title?: string, description?: string, tags?: string, teamId?: string) => {
      const formData = new FormData();
      formData.append("file", file);
      if (title) formData.append("title", title);
      if (description) formData.append("description", description);
      if (tags) formData.append("tags", tags);
      if (teamId) formData.append("team_id", teamId);

      return apiClient.post<KnowledgeSource>("/knowledge/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      }).then(res => res.data);
    },
    sources: (params?: { page?: number; page_size?: number; status?: string; search?: string; team_id?: string }) =>
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
    posts: (params?: SocialPostQueryParams & { team_id?: string }) =>
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
        url: `/social/posts/${id}/publish`,
      }),
    reschedule: (id: string, newDate: string) =>
      apiRequest<SocialPost>({
        method: "POST",
        url: `/social/posts/${id}/reschedule`,
        data: { scheduled_at: newDate },
      }),
    retryFailed: (id: string, targetIds?: string[]) =>
      apiRequest<SocialPost>({
        method: "POST",
        url: `/social/posts/${id}/retry`,
        data: { target_ids: targetIds },
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
        url: "/admin/dashboard",
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
      resetPassword: (id: string) =>
        apiRequest<{ temporary_password: string }>({
          method: "POST",
          url: `/admin/users/${id}/reset-password`,
        }),
      bulkSuspend: (userIds: string[], reason: string) =>
        apiRequest<{ suspended: number }>({
          method: "POST",
          url: "/admin/users/bulk-suspend",
          data: { user_ids: userIds, reason },
        }),
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
  },

  // Teams (Multi-tenancy)
  teams: {
    list: () =>
      apiRequest<Team[]>({
        url: "/teams",
      }),
    get: (id: string) =>
      apiRequest<Team>({
        url: `/teams/${id}`,
      }),
    create: (data: TeamCreateRequest) =>
      apiRequest<Team>({
        method: "POST",
        url: "/teams",
        data,
      }),
    update: (id: string, data: TeamUpdateRequest) =>
      apiRequest<Team>({
        method: "PUT",
        url: `/teams/${id}`,
        data,
      }),
    delete: (id: string) =>
      apiRequest<void>({
        method: "DELETE",
        url: `/teams/${id}`,
      }),
    switch: (id: string | null) =>
      apiRequest<void>({
        method: "POST",
        url: "/teams/switch",
        data: { team_id: id },
      }),
    getCurrent: () =>
      apiRequest<Team | null>({
        url: "/teams/current",
      }),
    uploadLogo: (teamId: string, file: File) => {
      const formData = new FormData();
      formData.append("logo", file);
      return apiClient.post<Team>(`/teams/${teamId}/logo`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      }).then(res => res.data);
    },
    transferOwnership: (teamId: string, newOwnerId: string) =>
      apiRequest<void>({
        method: "POST",
        url: `/teams/${teamId}/transfer-ownership`,
        data: { new_owner_id: newOwnerId },
      }),
    leave: (teamId: string) =>
      apiRequest<void>({
        method: "POST",
        url: `/teams/${teamId}/leave`,
      }),

    members: {
      list: (teamId: string) =>
        apiRequest<TeamMember[]>({
          url: `/teams/${teamId}/members`,
        }),
      add: (teamId: string, data: TeamMemberAddRequest) =>
        apiRequest<TeamMember>({
          method: "POST",
          url: `/teams/${teamId}/members`,
          data,
        }),
      update: (teamId: string, userId: string, data: TeamMemberUpdateRequest) =>
        apiRequest<TeamMember>({
          method: "PUT",
          url: `/teams/${teamId}/members/${userId}`,
          data,
        }),
      remove: (teamId: string, userId: string) =>
        apiRequest<void>({
          method: "DELETE",
          url: `/teams/${teamId}/members/${userId}`,
        }),
    },

    invitations: {
      list: (teamId: string) =>
        apiRequest<TeamInvitation[]>({
          url: `/teams/${teamId}/invitations`,
        }),
      create: (teamId: string, data: TeamInvitationCreateRequest) =>
        apiRequest<TeamInvitation>({
          method: "POST",
          url: `/teams/${teamId}/invitations`,
          data,
        }),
      revoke: (teamId: string, invitationId: string) =>
        apiRequest<void>({
          method: "DELETE",
          url: `/teams/${teamId}/invitations/${invitationId}`,
        }),
      resend: (teamId: string, invitationId: string) =>
        apiRequest<TeamInvitation>({
          method: "POST",
          url: `/teams/${teamId}/invitations/${invitationId}/resend`,
        }),
      getByToken: (token: string) =>
        apiRequest<TeamInvitation>({
          url: `/invitations/${token}`,
        }),
      accept: (token: string) =>
        apiRequest<void>({
          method: "POST",
          url: `/invitations/${token}/accept`,
        }),
    },

    billing: {
      subscription: (teamId: string) =>
        apiRequest<TeamSubscription>({
          url: `/teams/${teamId}/billing/subscription`,
        }),
      checkout: (teamId: string, variantId: string) =>
        apiRequest<{ checkout_url: string }>({
          method: "POST",
          url: `/teams/${teamId}/billing/checkout`,
          data: { variant_id: variantId },
        }),
      portal: (teamId: string) =>
        apiRequest<{ portal_url: string }>({
          url: `/teams/${teamId}/billing/portal`,
        }),
      cancel: (teamId: string) =>
        apiRequest<void>({
          method: "POST",
          url: `/teams/${teamId}/billing/cancel`,
        }),
      usage: (teamId: string) =>
        apiRequest<TeamUsage>({
          url: `/teams/${teamId}/billing/usage`,
        }),
    },
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
  team_id?: string;
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
  team_id?: string;
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
  team_id?: string;
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
  team_id?: string;
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

export interface GeneratedImage {
  id: string;
  user_id: string;
  team_id?: string;
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
  team_id?: string;
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
  team_id?: string;
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
  team_id?: string;
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
  team_id?: string;
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

// Admin types
export interface AdminDashboardStats {
  total_users: number;
  users_trend: TrendData;
  total_articles: number;
  articles_trend: TrendData;
  total_revenue: number;
  revenue_trend: TrendData;
  active_subscriptions: number;
  subscriptions_trend: TrendData;
  new_users_7d: Array<{ date: string; count: number }>;
  subscription_distribution: Array<{ tier: string; count: number; percentage: number }>;
  recent_activity: AdminAuditLog[];
}

export interface AdminUserQueryParams {
  page?: number;
  page_size?: number;
  search?: string;
  tier?: string;
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

// Teams (Multi-tenancy) types
export type TeamRole = "owner" | "admin" | "member" | "viewer";
export type TeamSubscriptionTier = "free" | "starter" | "professional" | "enterprise";

export interface Team {
  id: string;
  name: string;
  slug: string;
  description?: string;
  logo_url?: string;
  subscription_tier: TeamSubscriptionTier;
  my_role: TeamRole;
  member_count: number;
  created_at: string;
  updated_at: string;
}

export interface TeamMember {
  id: string;
  user_id: string;
  email: string;
  name: string;
  avatar_url?: string;
  role: TeamRole;
  joined_at: string;
}

export interface TeamInvitation {
  id: string;
  email: string;
  role: TeamRole;
  status: "pending" | "accepted" | "expired" | "revoked";
  expires_at: string;
  invited_by: string;
  invited_by_name: string;
  created_at: string;
}

export interface TeamCreateRequest {
  name: string;
  slug?: string;
  description?: string;
}

export interface TeamUpdateRequest {
  name?: string;
  slug?: string;
  description?: string;
  logo_url?: string;
}

export interface TeamMemberAddRequest {
  user_id: string;
  role: TeamRole;
}

export interface TeamMemberUpdateRequest {
  role: TeamRole;
}

export interface TeamInvitationCreateRequest {
  email: string;
  role: TeamRole;
}

export interface TeamSubscription {
  subscription_tier: TeamSubscriptionTier;
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

export interface TeamUsage {
  period_start: string;
  period_end: string;
  articles_used: number;
  outlines_used: number;
  images_used: number;
  articles_limit: number;
  outlines_limit: number;
  images_limit: number;
}
