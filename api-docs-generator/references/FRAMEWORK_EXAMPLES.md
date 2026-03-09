# Framework-Specific Examples

Reference implementations for Angular, React, and Vue. Use the section matching the user's target framework when generating the documentation.

---

## Angular (14+ Standalone)

### Service Pattern

```typescript
import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '@environments/environment';
// Import interfaces from the models file

@Injectable({ providedIn: 'root' })
export class [Module]Service {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/[prefix]`;

  // --- GET with query params ---

  list(params: QueryParams = {}): Observable<PaginatedResponse> {
    let httpParams = new HttpParams();
    if (params.search) httpParams = httpParams.set('search', params.search);
    if (params.page != null) httpParams = httpParams.set('page', params.page.toString());
    if (params.limit != null) httpParams = httpParams.set('limit', params.limit.toString());
    // Arrays: use append() to repeat the param key
    if (params.categoryIds?.length) {
      params.categoryIds.forEach(id => httpParams = httpParams.append('categoryIds', id));
    }
    return this.http.get<PaginatedResponse>(this.base, { params: httpParams });
  }

  // --- GET with path param ---

  getById(id: string): Observable<EntityDetail> {
    return this.http.get<EntityDetail>(`${this.base}/${id}`);
  }

  // --- POST with JSON body ---

  create(body: CreateRequest): Observable<EntityResponse> {
    return this.http.post<EntityResponse>(this.base, body);
  }

  // --- PATCH with JSON body ---

  update(id: string, body: UpdateRequest): Observable<EntityResponse> {
    return this.http.patch<EntityResponse>(`${this.base}/${id}`, body);
  }

  // --- DELETE ---

  delete(id: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/${id}`);
  }

  // --- File upload (multipart/form-data) ---

  upload(file: File, folderId: string): Observable<FileResponse> {
    const form = new FormData();
    form.append('file', file);
    form.append('folderId', folderId);
    // No set Content-Type header — HttpClient sets it automatically with boundary
    return this.http.post<FileResponse>(`${this.base}/upload`, form);
  }

  // --- Presigned URL download ---

  getDownloadUrl(id: string): Observable<PresignedUrlResponse> {
    return this.http.get<PresignedUrlResponse>(`${this.base}/${id}/download`);
  }
}
```

### Error Interceptor

```typescript
import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { catchError, throwError } from 'rxjs';

export const apiErrorInterceptor: HttpInterceptorFn = (req, next) => {
  return next(req).pipe(
    catchError((err: HttpErrorResponse) => {
      const message: string = err.error?.message ?? 'Unknown error';
      const status: number = err.status;
      // message comes from the backend in the API's language.
      // Map against ApiErrorMessage enum for i18n.
      return throwError(() => ({ status, message }));
    })
  );
};

// Register in app.config.ts:
// provideHttpClient(withInterceptors([apiErrorInterceptor]))
```

### Auth Interceptor

```typescript
import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const token = inject(AuthService).getToken();
  if (token) {
    req = req.clone({ setHeaders: { Authorization: `Bearer ${token}` } });
  }
  return next(req);
};
```

### Presigned URL Handling

```typescript
// Download: open in new tab
window.open(response.url, '_blank');

// Preview PDF in iframe: sanitize the URL
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';

@Component({...})
export class PreviewComponent {
  private sanitizer = inject(DomSanitizer);
  safeUrl: SafeResourceUrl | null = null;

  loadPreview(url: string): void {
    this.safeUrl = this.sanitizer.bypassSecurityTrustResourceUrl(url);
  }
}

// Preview DOCX: use Office Online viewer
const viewerUrl = `https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(url)}`;
```

### Pagination with HttpParams

```typescript
// Arrays as repeated query params (NestJS-compatible):
// ?categoryIds=uuid1&categoryIds=uuid2
params.categoryIds.forEach(id => {
  httpParams = httpParams.append('categoryIds', id);
});

// Date range:
if (params.startDate) httpParams = httpParams.set('startDate', params.startDate);
if (params.endDate) httpParams = httpParams.set('endDate', params.endDate);

// Always reset to page 1 when filters change
```

---

## React (with TypeScript)

### Service Pattern (async functions)

```typescript
const API_URL = process.env.REACT_APP_API_URL || import.meta.env.VITE_API_URL;

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getAuthToken(); // from your auth context/store
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ message: 'Unknown error' }));
    throw { status: res.status, message: error.message };
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// --- Usage ---

export const [module]Api = {
  list: (params: QueryParams = {}) => {
    const searchParams = new URLSearchParams();
    if (params.search) searchParams.set('search', params.search);
    if (params.page) searchParams.set('page', String(params.page));
    if (params.limit) searchParams.set('limit', String(params.limit));
    params.categoryIds?.forEach(id => searchParams.append('categoryIds', id));
    const qs = searchParams.toString();
    return fetchApi<PaginatedResponse>(`/[prefix]${qs ? `?${qs}` : ''}`);
  },

  getById: (id: string) =>
    fetchApi<EntityDetail>(`/[prefix]/${id}`),

  create: (body: CreateRequest) =>
    fetchApi<EntityResponse>('/[prefix]', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  update: (id: string, body: UpdateRequest) =>
    fetchApi<EntityResponse>(`/[prefix]/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),

  delete: (id: string) =>
    fetchApi<void>(`/[prefix]/${id}`, { method: 'DELETE' }),

  upload: async (file: File, folderId: string) => {
    const form = new FormData();
    form.append('file', file);
    form.append('folderId', folderId);
    const token = getAuthToken();
    const res = await fetch(`${API_URL}/[prefix]/upload`, {
      method: 'POST',
      headers: { ...(token && { Authorization: `Bearer ${token}` }) },
      // Do NOT set Content-Type for FormData — browser sets it with boundary
      body: form,
    });
    if (!res.ok) throw await res.json();
    return res.json() as Promise<FileResponse>;
  },
};
```

### TanStack Query Hook Pattern

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

export function use[Entity]List(params: QueryParams) {
  return useQuery({
    queryKey: ['[entities]', params],
    queryFn: () => [module]Api.list(params),
  });
}

export function useCreate[Entity]() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateRequest) => [module]Api.create(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['[entities]'] });
    },
  });
}
```

### Error Handling

```typescript
try {
  const data = await [module]Api.getById(id);
} catch (err) {
  const { status, message } = err as { status: number; message: string };
  if (status === 404) {
    // Show "not found" UI
  } else if (status === 401) {
    // Redirect to login
  } else {
    // Show generic error toast
  }
}
```

---

## Vue 3 (Composition API + TypeScript)

### Service Pattern (composable)

```typescript
import { ref } from 'vue';

const API_URL = import.meta.env.VITE_API_URL;

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const token = useAuthStore().token; // from Pinia or your auth store
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ message: 'Unknown error' }));
    throw { status: res.status, message: error.message };
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export function use[Module]Api() {
  const loading = ref(false);
  const error = ref<{ status: number; message: string } | null>(null);

  async function list(params: QueryParams = {}): Promise<PaginatedResponse> {
    loading.value = true;
    error.value = null;
    try {
      const searchParams = new URLSearchParams();
      if (params.search) searchParams.set('search', params.search);
      if (params.page) searchParams.set('page', String(params.page));
      const qs = searchParams.toString();
      return await fetchApi<PaginatedResponse>(`/[prefix]${qs ? `?${qs}` : ''}`);
    } catch (err) {
      error.value = err as { status: number; message: string };
      throw err;
    } finally {
      loading.value = false;
    }
  }

  async function create(body: CreateRequest): Promise<EntityResponse> {
    return fetchApi<EntityResponse>('/[prefix]', {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  // ... other methods follow same pattern

  return { list, create, loading, error };
}
```

### With Axios

```typescript
import axios, { type AxiosInstance } from 'axios';

const api: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
});

api.interceptors.request.use(config => {
  const token = useAuthStore().token;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  res => res,
  err => {
    const message = err.response?.data?.message ?? 'Unknown error';
    const status = err.response?.status ?? 500;
    return Promise.reject({ status, message });
  }
);

export const [module]Api = {
  list: (params?: QueryParams) =>
    api.get<PaginatedResponse>('/[prefix]', { params }).then(r => r.data),
  create: (body: CreateRequest) =>
    api.post<EntityResponse>('/[prefix]', body).then(r => r.data),
  // ...
};
```

---

## Common Patterns (All Frameworks)

### File Download via Presigned URL

```
1. Call GET /resource/:id/download
2. Receive { url, expiresIn }
3. Open url in new tab or create a temporary <a> element
4. NEVER cache the URL — request a fresh one each time
```

### File Upload Checklist

```
1. Validate file size on client BEFORE uploading (avoid wasted bandwidth)
2. Validate file extension/MIME type on client
3. Construct FormData — do NOT set Content-Type header manually
4. Show upload progress if framework supports it (Angular: reportProgress, Axios: onUploadProgress)
5. Handle 413 (file too large) separately from other errors
```

### Debounced Search

```
- Debounce user input by 300-500ms before hitting the search endpoint
- Reset pagination to page 1 when search text changes
- Show loading indicator during the debounce + request period
- Clear results and show empty state when search returns 0 results
```

### Pagination Reset Rules

```
Reset to page 1 when:
- Search text changes
- Filters change (category, date range, status)
- Sort order changes

Do NOT reset when:
- User clicks next/previous page
- User changes page size (optional — depends on UX preference)
```
