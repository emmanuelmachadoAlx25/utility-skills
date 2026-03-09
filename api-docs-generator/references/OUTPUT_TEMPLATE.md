# Output Template

This is the canonical Markdown structure for generated API documentation. Follow it strictly. Adapt section names to the specific module being documented, but preserve the order and depth.

---

## Document Header

```markdown
# API Documentation: [Module Name]

> Integration guide for [Target Framework]. Covers all endpoints of the **[Module]** module
> with typed requests, responses, and error mapping.
> **Backend framework:** [NestJS / Express / Spring Boot / etc.]
> **Date:** [YYYY-MM-DD]

---
```

## Section 1: Base Configuration

```markdown
## Base Configuration

- **Base URL prefix:** `/[module-prefix]`
- **Authentication:** [Describe auth method — JWT Bearer, API Key, etc.]
- **Default Content-Type:** `application/json`
- **Exceptions:** [List any endpoints that use different content types, e.g., multipart/form-data for uploads]
- **Error format:** [Describe the standard error response shape]
```

Include environment configuration example for the target framework:

```markdown
### Environment Setup

\`\`\`typescript
// Angular: environment.ts
export const environment = {
  apiUrl: 'https://<domain>',
};

// React: .env
REACT_APP_API_URL=https://<domain>

// Vue: .env
VITE_API_URL=https://<domain>
\`\`\`
```

Only include the example for the user's target framework, not all three.

## Section 2: TypeScript Interfaces

Group interfaces logically. Use this order:

1. **Enums** — Status enums, type enums, role enums
2. **Core response interfaces** — The main data shapes returned by endpoints
3. **Pagination** — Generic pagination wrapper if used
4. **Request/Query interfaces** — Shapes for request bodies and query parameters
5. **Error types** — Error response structure and error message enum

```markdown
## TypeScript Interfaces

### Enums

\`\`\`typescript
export enum [EntityStatus] {
  VALUE_A = 'VALUE_A',
  VALUE_B = 'VALUE_B',
}
\`\`\`

### Response Interfaces

\`\`\`typescript
// Used in: GET /endpoint, POST /endpoint
export interface [EntityResponse] {
  id: string;              // UUID v4
  name: string;
  status: [EntityStatus];
  createdAt: string;       // ISO 8601
  updatedAt: string;       // ISO 8601
}
\`\`\`

### Pagination

\`\`\`typescript
export interface PaginationMeta {
  total: number;
  page: number;
  limit: number;
  totalPages: number;
}

export interface Paginated[Entity]Response {
  data: [EntityResponse][];
  meta: PaginationMeta;
}
\`\`\`

### Request Types

\`\`\`typescript
export interface Create[Entity]Request {
  name: string;       // Required. Max [N] chars.
  parentId?: string;  // Optional. UUID v4.
}

export interface Query[Entity]Params {
  search?: string;    // Max 100 chars
  page?: number;      // Default: 1
  limit?: number;     // Default: 10
}
\`\`\`

### Error Types

\`\`\`typescript
export interface ApiError {
  statusCode: number;
  message: string;
}

export enum ApiErrorMessage {
  [ENTITY]_NOT_FOUND = '[Entity description] no encontrado',
  // ... all error messages exactly as the backend returns them
}
\`\`\`
```

Rules for interfaces:
- Add a `// comment` on fields that need context (format, constraints, usage)
- Mark optional fields with `?`
- Reference where each interface is used: `// Used in: GET /path, POST /path`
- For Java backends, apply the type mapping table from the SKILL.md

## Section 3: Domain-Specific Sections (conditional)

Include these ONLY when relevant to the module:

### State Machine / Status Flow

When entities have status fields with transition rules:

```markdown
## Valid Status Transitions

The backend enforces the following flow. Invalid transitions return `422`.

\`\`\`
STATUS_A ──────► STATUS_B
                    │
         ┌─────────┴─────────┐
         ▼                   ▼
     STATUS_C            STATUS_D
         │
         ▼
     STATUS_E  ◄── (system-only)
\`\`\`

> **Important:** [Note any blocked/locked states and their implications]
```

### Accepted MIME Types

When file upload endpoints exist:

```markdown
## Accepted MIME Types

| Extension | MIME type                          | Backend value |
|-----------|------------------------------------|---------------|
| `.pdf`    | `application/pdf`                  | `PDF`         |
| `.docx`   | `application/vnd.openxml...`       | `DOCX`        |
```

## Section 4: Endpoints

Group endpoints by resource (e.g., Folders, Files, Users). Number them sequentially across the entire document.

Each endpoint follows this template:

```markdown
## Endpoints: [Resource Name]

### [N]. [Action description]

**`[METHOD] /path`**

**Description:** [What this endpoint does]

**Authentication:** [Required / Optional / None]

**Path parameters:**

| Parameter | Type              | Description              |
|-----------|-------------------|--------------------------|
| `id`      | `string` (UUID v4)| ID of the [entity]       |

**Query parameters** (all optional):

\`\`\`typescript
{
  search?: string;      // Max 100 chars, filters by name
  page?: number;        // Default: 1
  limit?: number;       // Default: 10, min: 1
}
\`\`\`

**Body** (`application/json`):

\`\`\`typescript
{
  name: string;         // Required. Max 50 chars. Cannot contain: . / \ : * ? " < > |
  parentId?: string;    // Optional. UUID v4 of parent folder
}
\`\`\`

**Response** `[STATUS CODE] [Status Text]` → `[InterfaceName]`

\`\`\`json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Example",
  "createdAt": "2025-01-01T10:00:00.000Z"
}
\`\`\`

**Errors:**

| HTTP  | Message                                         |
|-------|-------------------------------------------------|
| `400` | Validation errors (required field, invalid chars)|
| `404` | `[Entity] not found`                            |
| `409` | `A [entity] with that name already exists`      |
| `500` | `Internal server error`                         |

**[Framework] example:**

\`\`\`typescript
// Only include when the call has non-trivial setup (FormData, special params, etc.)
uploadFile(file: File, folderId: string): Observable<FileListItem> {
  const form = new FormData();
  form.append('file', file);
  form.append('folderId', folderId);
  return this.http.post<FileListItem>(`${this.base}/files/upload`, form);
}
\`\`\`
```

Rules for endpoints:
- Include path params table ONLY when there are path parameters
- Include query params ONLY for GET endpoints that accept them
- Include body ONLY for POST/PUT/PATCH endpoints with a body
- Include JSON response example for the first endpoint of each resource, then reference the interface for subsequent ones
- Include framework example ONLY for non-trivial calls (file uploads, complex params, special headers)
- Error tables must list ALL possible errors, not just common ones

## Section 5: Framework Service

A complete, copy-pasteable service class for the target framework.

```markdown
## [Framework] Service (reference)

Suggested file: `src/app/features/[module]/services/[module].service.ts`

\`\`\`typescript
// Complete service implementation with all methods
// Include JSDoc comments on non-obvious methods
// Reference the interfaces defined in Section 2
\`\`\`
```

For Angular services:
- Use `inject()` function (Angular 14+) instead of constructor injection
- Use `HttpClient`, `HttpParams`
- Return `Observable<T>` types
- Include comments about interceptor assumptions (auth token, error handling)

For React:
- Export async functions or custom hooks
- Use `fetch` or `axios` with typed generics
- Include error handling pattern

For Vue:
- Use composables pattern
- Use `useFetch` or Axios with typed generics

## Section 6: Error Handling

```markdown
## Error Handling

### Standard error structure

\`\`\`json
{
  "statusCode": 404,
  "message": "Entity not found"
}
\`\`\`

### Error catalog

| Scenario                  | HTTP Status             | Message                          |
|---------------------------|-------------------------|----------------------------------|
| Entity not found          | `404 Not Found`         | `"Entity not found"`             |
| Duplicate name            | `409 Conflict`          | `"Name already exists"`          |
| ...                       | ...                     | ...                              |

### Error handling example

\`\`\`typescript
// Framework-specific interceptor or middleware example
\`\`\`
```

## Section 7: Integration Flows

Map each user-facing use case to a sequence of API calls:

```markdown
## Integration Flows by Use Case

### UC-01: [Use case name]

\`\`\`
[UI trigger]
  → [API call]
  → [Handle response]
  → [Update UI]
  → If error: [fallback behavior]
\`\`\`

### UC-02: [Use case with multiple calls]

\`\`\`
ngOnInit() / useEffect() / onMounted()
  → GET /categories    (populate filter)
  → GET /items?page=1  (load initial grid)
  → Render grid + pagination
\`\`\`
```

## Section 8: Implementation Notes

```markdown
## Implementation Notes

### [Topic: Presigned URLs / File Uploads / Pagination / etc.]

[Practical guidance for the frontend developer. Include:]
- Do's and don'ts
- Quirks and gotchas
- Framework-specific patterns (DomSanitizer, FormData, etc.)
- Performance considerations (debounce, caching policies)
```

## Section 9: Backend Models (optional)

Only include if the user wants full traceability or the project uses an ORM:

```markdown
## Backend Models (Reference)

For full traceability, these are the [Prisma/TypeORM/JPA] entities that produce the data:

\`\`\`
[EntityName] {
  id          String     (UUID)
  name        String
  ...
}
\`\`\`
```
