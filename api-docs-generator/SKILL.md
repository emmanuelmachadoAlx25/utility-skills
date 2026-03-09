---
name: api-docs-generator
description: >
  Analyze backend projects (TypeScript/JavaScript with NestJS/Express/Fastify, Java with Spring Boot, or any REST API framework) to auto-generate comprehensive API endpoint documentation in Markdown. Scans controllers, routes, DTOs, entities, and error handlers to produce frontend-ready integration guides with TypeScript interfaces, request/response types, error catalogs, state machines, and framework-specific service examples (Angular, React, Vue). Use this skill whenever the user says "document my API", "generate API docs", "create integration guide", "document endpoints", "scan controllers", mentions API documentation for frontend consumption, or wants to bridge backend and frontend with typed contracts. Also trigger when the user uploads or references backend source code and asks for documentation, endpoint listing, or integration help.
---

# API Docs Generator

Generate complete, frontend-ready API documentation by scanning backend source code. The output follows a structured Markdown format that serves as a contract between backend and frontend teams.

## When to Use

- User wants to document REST API endpoints from a backend project
- User uploads backend source files (controllers, routes, DTOs, entities)
- User asks for an "integration guide" for a frontend framework
- User wants TypeScript interfaces generated from backend models
- User wants error catalogs, state machines, or flow diagrams extracted from code

## Workflow Overview

```
1. DISCOVER  → Scan project structure, identify framework & language
2. EXTRACT   → Parse controllers, DTOs, entities, validators, error handlers
3. ANALYZE   → Map routes, infer request/response shapes, detect patterns
4. GENERATE  → Produce structured Markdown following the output template
5. ENRICH    → Add frontend service examples, integration flows, notes
```

## Step 1: Discover the Project

Scan the project root to identify:

- **Language**: TypeScript/JavaScript or Java
- **Framework**: NestJS, Express, Fastify, Spring Boot, or other
- **Structure pattern**: Feature modules, layered architecture, clean architecture
- **Key directories**: controllers, routes, handlers, dto, entities, models, exceptions

Run these commands to get an initial understanding:

```bash
# General structure
find . -type f \( -name "*.ts" -o -name "*.js" -o -name "*.java" \) | head -80

# For Node.js/TS projects
cat package.json 2>/dev/null | grep -E '"(express|fastify|@nestjs|hapi)"'

# For Java/Spring Boot
find . -name "pom.xml" -o -name "build.gradle" | head -5
grep -r "spring-boot-starter-web" pom.xml build.gradle 2>/dev/null
```

Identify the entry points:

| Framework    | Controller pattern                                              |
|--------------|-----------------------------------------------------------------|
| NestJS       | `@Controller()` decorator on classes                            |
| Express      | `router.get/post/put/patch/delete()` or `app.get()` calls      |
| Fastify      | `fastify.get()` or route schema objects                         |
| Spring Boot  | `@RestController` + `@RequestMapping` annotations               |

## Step 2: Extract Endpoint Information

For each controller/route file, extract:

1. **Route path** — base path + method path
2. **HTTP method** — GET, POST, PUT, PATCH, DELETE
3. **Request shape** — body DTOs, query params, path params, headers
4. **Response shape** — return type, status codes
5. **Validation rules** — decorators, annotations, validators
6. **Auth requirements** — guards, middleware, annotations
7. **Error scenarios** — thrown exceptions, error responses

### NestJS Extraction Patterns

```
@Controller('prefix')        → base path
@Get('path')                 → GET /prefix/path
@Post()                      → POST /prefix
@Body() dto: CreateDto       → request body shape → look for CreateDto class
@Query() query: QueryDto     → query params shape
@Param('id') id: string      → path parameter
@UseGuards(AuthGuard)        → requires authentication
@HttpCode(201)               → custom status code
```

Look for DTOs in files named `*.dto.ts`, `*.request.ts`, `*.input.ts`. Extract:
- Properties and their TypeScript types
- Validation decorators: `@IsString()`, `@IsOptional()`, `@MaxLength(50)`, `@IsUUID()`
- Transform decorators: `@Transform()`, `@Type()`

Look for entities/models in `*.entity.ts`, `*.model.ts`, `*.schema.ts`.

Look for error handling in:
- Exception filters (`*.filter.ts`)
- Custom exceptions (`*.exception.ts`)
- Service methods that throw `HttpException`, `NotFoundException`, etc.

### Express Extraction Patterns

```
router.get('/path', middleware, handler)     → GET /path with middleware
router.post('/path', validate(schema), fn)  → POST /path with validation
req.body                                    → request body
req.query                                   → query parameters
req.params                                  → path parameters
```

Look for validation schemas (Joi, Zod, express-validator). Extract shapes from schema definitions.

### Spring Boot Extraction Patterns

```
@RestController
@RequestMapping("/api/v1/users")           → base path
@GetMapping("/{id}")                       → GET /api/v1/users/{id}
@PostMapping                               → POST /api/v1/users
@RequestBody CreateUserDto dto             → request body
@RequestParam String name                  → query parameter
@PathVariable String id                    → path parameter
@Valid                                     → triggers bean validation
@PreAuthorize("hasRole('ADMIN')")          → authorization requirement
```

Look for DTOs in `*Dto.java`, `*Request.java`, `*Response.java`. Extract:
- Fields and their Java types (map to TypeScript equivalents)
- Bean validation: `@NotNull`, `@Size(max=50)`, `@Email`, `@Pattern`
- Jackson annotations: `@JsonProperty`, `@JsonIgnore`

Look for exceptions in `*Exception.java` and `@ControllerAdvice` classes.

### Java to TypeScript Type Mapping

| Java type                  | TypeScript equivalent     |
|---------------------------|---------------------------|
| `String`                  | `string`                  |
| `Integer`, `Long`, `int`  | `number`                  |
| `Double`, `Float`         | `number`                  |
| `Boolean`, `boolean`      | `boolean`                 |
| `UUID`                    | `string`                  |
| `LocalDateTime`, `Date`   | `string` (ISO 8601)       |
| `List<T>`, `Set<T>`       | `T[]`                     |
| `Map<K,V>`                | `Record<K, V>`            |
| `Optional<T>`             | `T \| null`               |
| `BigDecimal`              | `number` (note precision) |
| enum                      | TypeScript `enum` or union |

## Step 3: Analyze Patterns

After extraction, identify cross-cutting patterns:

- **Pagination**: Look for `page`, `limit`, `offset`, `PaginatedResponse` types
- **Error structure**: Common error response format (`{ statusCode, message }`, `{ error, details }`)
- **Auth flow**: JWT, sessions, API keys
- **State machines**: Enum fields with transition logic (look for status fields and validation of transitions)
- **File uploads**: Multipart endpoints, size limits, accepted MIME types
- **Presigned URLs**: S3/cloud storage patterns

## Step 4: Generate the Documentation

Read the output template from `references/OUTPUT_TEMPLATE.md` before generating.

The output Markdown MUST follow this structure. Read the full template for details, but here is the skeleton:

```markdown
# API Documentation: [Module Name]

> Integration guide for [Framework]. Covers all endpoints with typed requests,
> responses, and error mapping.

## Configuration
## TypeScript Interfaces
## [Domain-specific sections: state machines, MIME types, etc.]
## Endpoints (grouped by resource)
## [Framework] Service (reference implementation)
## Error Handling
## Integration Flows by Use Case
## Implementation Notes
```

Key rules for generating documentation:

1. **Every endpoint gets its own subsection** with: method + path, description, auth requirement, request shape (body/query/params), response shape with status code, error table, and optionally a code example.

2. **TypeScript interfaces** must be complete and copy-pasteable. Include JSDoc or inline comments for fields that need explanation. Group them logically (enums first, then response types, then request/query types).

3. **Error tables** list every possible HTTP status + message combination per endpoint. Extract these from exception throws in services, guards, and filters.

4. **The frontend service** must be a complete, working class with all methods typed. Use `inject()` for Angular 14+, constructor injection for older. Include helper comments.

5. **Integration flows** describe step-by-step sequences for each use case from the user's perspective (UI action → API call → handle response → update UI).

## Step 5: Enrich with Framework-Specific Guidance

After generating the core documentation, add framework-specific sections based on what the user needs.

Read `references/FRAMEWORK_EXAMPLES.md` for templates of:
- Angular services with `HttpClient`, `HttpParams`, signals, and interceptors
- React hooks with `fetch`/`axios` and TanStack Query patterns
- Vue composables with `useFetch` or Axios

Also add implementation notes covering:
- Presigned URL handling (no caching, request fresh each time)
- File upload patterns (FormData construction)
- Pagination integration with UI components
- Query param serialization quirks (arrays, dates)
- Auth token management (interceptors, middleware)

## Output Format

The final deliverable is a single `.md` file saved to the user's output directory. Name it based on the module: `{module-name}-api-{framework}.md`.

Example filenames:
- `files-folders-api-angular.md`
- `users-api-react.md`
- `payments-api-vue.md`

## Handling Edge Cases

- **No DTOs found**: Infer request/response shapes from controller method signatures and service return types. Flag as "inferred" in the docs.
- **Complex nested types**: Flatten into separate interfaces with clear references.
- **Multiple error formats**: Document each variation and note which endpoints use which format.
- **Undocumented endpoints**: Include them with a warning note. Better to document with caveats than to omit.
- **Internal/admin endpoints**: Include them in a separate section clearly marked as internal.

## Reference Files

Read these files for detailed templates and examples:

- `references/OUTPUT_TEMPLATE.md` — The complete Markdown template to follow for the output document. **Read this before generating any documentation.**
- `references/FRAMEWORK_EXAMPLES.md` — Framework-specific code examples (Angular, React, Vue) for services, hooks, composables, interceptors, and error handling patterns.
