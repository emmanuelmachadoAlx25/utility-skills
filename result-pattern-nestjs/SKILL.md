---
name: result-pattern-nestjs
description: >
  Enforce the Result Pattern with Domain Exceptions for explicit, type-safe
  error handling across all NestJS feature layers. The Result Pattern lives in
  repositories for data-access safety; services consume Results, apply business
  logic, and throw typed DomainExceptions on failure; a global ExceptionFilter
  catches them and maps to HTTP responses — keeping controllers ultra-clean.
  Use whenever creating or refactoring a NestJS feature that performs I/O,
  business-logic validation, or any operation that can fail.
---

# Result Pattern + Domain Exceptions — NestJS Features

## Purpose

This skill ensures every NestJS feature is implemented with a **hybrid
architecture** inspired by Clean Architecture and Spring Boot:

| Layer           | Error Strategy                                               |
| --------------- | ------------------------------------------------------------ |
| Repository      | Returns `Result<T, Error>` — no `throw`, explicit failures   |
| Service         | Consumes `Result`, throws typed `DomainException` on fail    |
| Controller      | **Zero error handling** — delegates to service, returns data |
| ExceptionFilter | Catches `DomainException` globally, maps to HTTP response    |

This produces controllers as clean as Spring Boot:

```typescript
@Post()
@HttpCode(HttpStatus.CREATED)
async createFolder(@Body() dto: CreateFolderDto, @CurrentClientUser() user: ClientJwtPayload): Promise<FolderResponseDto> {
  return this.foldersService.createFolder(dto, user.sub);
}
```

Apply this skill when the user asks to:

- Create a new NestJS feature/module
- Add a use-case or service method
- Refactor existing code that uses exceptions for control flow
- Clean up controllers that repeat `isFail` / `mapToHttpException` boilerplate

---

## Shared Infrastructure (create once, reuse everywhere)

### 1. Result type (`src/shared/result`)

> Keep this exactly as-is — it's the foundation for repository safety.

```typescript
// src/shared/result/result.type.ts
export type Result<T, E> =
  | { success: true; value: T }
  | { success: false; error: E };

export function success<T>(value: T): Result<T, never> {
  return { success: true, value };
}

export function fail<E>(error: E): Result<never, E> {
  return { success: false, error };
}

export function isFail<T, E>(
  result: Result<T, E>,
): result is { success: false; error: E } {
  return !result.success;
}

export function isSuccess<T, E>(
  result: Result<T, E>,
): result is { success: true; value: T } {
  return result.success;
}
```

### 2. DomainException base class (`src/shared/exceptions/domain.exception.ts`)

```typescript
import { HttpStatus } from "@nestjs/common";

export class DomainException extends Error {
  constructor(
    public readonly errorCode: string,
    public readonly statusCode: HttpStatus,
    message?: string,
  ) {
    super(message ?? errorCode);
    this.name = "DomainException";
  }
}
```

### 3. Global DomainExceptionFilter (`src/shared/exceptions/domain-exception.filter.ts`)

Based on NestJS Exception Filters (see `references/nestjs-exception-filters.md`):

```typescript
import { ExceptionFilter, Catch, ArgumentsHost, Logger } from "@nestjs/common";
import { Response } from "express";
import { DomainException } from "./domain.exception";

@Catch(DomainException)
export class DomainExceptionFilter implements ExceptionFilter {
  private readonly logger = new Logger(DomainExceptionFilter.name);

  catch(exception: DomainException, host: ArgumentsHost): void {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse<Response>();

    this.logger.warn(`[${exception.errorCode}] ${exception.message}`);

    response.status(exception.statusCode).json({
      statusCode: exception.statusCode,
      errorCode: exception.errorCode,
      message: exception.message,
    });
  }
}
```

### 4. Register globally (`main.ts` or `AppModule`)

**Option A — in `main.ts`:**

```typescript
import { DomainExceptionFilter } from "./shared/exceptions/domain-exception.filter";

const app = await NestFactory.create(AppModule);
app.useGlobalFilters(new DomainExceptionFilter());
```

**Option B — via `APP_FILTER` provider (preferred, supports DI):**

```typescript
import { Module } from "@nestjs/common";
import { APP_FILTER } from "@nestjs/core";
import { DomainExceptionFilter } from "./shared/exceptions/domain-exception.filter";

@Module({
  providers: [
    {
      provide: APP_FILTER,
      useClass: DomainExceptionFilter,
    },
  ],
})
export class AppModule {}
```

> **Prefer Option B** when the filter needs injected dependencies (e.g., a
> logging service, i18n, etc.). See `references/nestjs-exception-filters.md`
> for more details on binding filters.

---

## Feature Structure

For every new feature, generate these files:

```
src/
└── <feature>/
    ├── exceptions/
    │   └── <feature>.exception.ts   ← Typed DomainException subclasses
    ├── entity/
    │   └── <feature>.entity.ts      ← TypeORM / domain entity
    ├── dto/
    │   ├── create-<feature>.dto.ts  ← class-validator DTOs
    │   └── <feature>-response.dto.ts
    ├── repository/
    │   └── <feature>.repository.ts  ← Data access, returns Result
    ├── service/
    │   └── <feature>.service.ts     ← Business logic, throws DomainException
    ├── controller/
    │   └── <feature>.controller.ts  ← HTTP layer, CLEAN — no error handling
    └── <feature>.module.ts          ← NestJS module wiring
```

---

## Layer-by-Layer Rules

### 1. Feature exceptions (`exceptions/<feature>.exception.ts`)

Create specific `DomainException` subclasses per feature. Each one carries its
own `errorCode` and `HttpStatus`:

```typescript
import { HttpStatus } from "@nestjs/common";
import { DomainException } from "src/shared/exceptions/domain.exception";

export class FolderNotFoundException extends DomainException {
  constructor() {
    super("FOLDER_NOT_FOUND", HttpStatus.NOT_FOUND, "Folder not found");
  }
}

export class FolderNameConflictException extends DomainException {
  constructor() {
    super(
      "FOLDER_NAME_CONFLICT",
      HttpStatus.CONFLICT,
      "A folder with this name already exists",
    );
  }
}

export class FolderDatabaseException extends DomainException {
  constructor() {
    super(
      "FOLDER_DATABASE_ERROR",
      HttpStatus.INTERNAL_SERVER_ERROR,
      "An unexpected database error occurred",
    );
  }
}
```

> **Why subclasses instead of an enum + mapper?** Each exception is
> self-contained — it knows its HTTP status, error code, and message. No
> external `mapToHttpException` switch needed. The global filter handles them
> all uniformly.

---

### 2. Repository (`repository/<feature>.repository.ts`)

- Return `Promise<Result<T, DomainException>>` on every public method.
- Wrap **all** `await` calls in a single `try/catch`; map the catch to the
  appropriate `DomainException`.
- Use `success(entity)` or `fail(new XxxException())` — **never `throw`**.

```typescript
import { Injectable } from "@nestjs/common";
import { InjectRepository } from "@nestjs/typeorm";
import { Repository } from "typeorm";
import { Result, success, fail } from "src/shared/result";
import { Folder } from "../entity/folder.entity";
import { DomainException } from "src/shared/exceptions/domain.exception";
import {
  FolderNotFoundException,
  FolderDatabaseException,
} from "../exceptions/folder.exception";

@Injectable()
export class FoldersRepository {
  constructor(
    @InjectRepository(Folder)
    private readonly repo: Repository<Folder>,
  ) {}

  async findById(
    id: string,
    clientId: string,
  ): Promise<Result<Folder | null, DomainException>> {
    try {
      const folder = await this.repo.findOneBy({ id, clientId });
      return success(folder);
    } catch {
      return fail(new FolderDatabaseException());
    }
  }

  async findByNameAndParent(
    name: string,
    parentId: string | null,
    clientId: string,
  ): Promise<Result<Folder | null, DomainException>> {
    try {
      const folder = await this.repo.findOneBy({ name, parentId, clientId });
      return success(folder);
    } catch {
      return fail(new FolderDatabaseException());
    }
  }

  async create(
    data: Partial<Folder>,
  ): Promise<Result<Folder, DomainException>> {
    try {
      const folder = this.repo.create(data);
      const saved = await this.repo.save(folder);
      return success(saved);
    } catch {
      return fail(new FolderDatabaseException());
    }
  }

  async rename(
    id: string,
    name: string,
  ): Promise<Result<Folder, DomainException>> {
    try {
      await this.repo.update(id, { name });
      const updated = await this.repo.findOneByOrFail({ id });
      return success(updated);
    } catch {
      return fail(new FolderDatabaseException());
    }
  }
}
```

---

### 3. Service (`service/<feature>.service.ts`)

- Return type is **plain `Promise<T>`** — no `Result` wrapper.
- Consume repository `Result` using `isFail()` → **`throw result.error`**.
- Apply business-logic validation → **`throw new XxxException()`**.
- This is the "translation layer" between the safe `Result` world and the
  exception-based HTTP world.

```typescript
import { Injectable, Logger } from "@nestjs/common";
import { plainToInstance } from "class-transformer";
import { isFail } from "src/shared/result";
import { FoldersRepository } from "../repository/folders.repository";
import { CreateFolderDto } from "../dto/create-folder.dto";
import { RenameFolderDto } from "../dto/rename-folder.dto";
import { FolderResponseDto } from "../dto/folder-response.dto";
import {
  FolderNotFoundException,
  FolderNameConflictException,
} from "../exceptions/folder.exception";

@Injectable()
export class FoldersService {
  private readonly logger = new Logger(FoldersService.name);

  constructor(private readonly foldersRepository: FoldersRepository) {}

  async createFolder(
    dto: CreateFolderDto,
    clientId: string,
  ): Promise<FolderResponseDto> {
    const parentId = dto.parentId ?? null;

    const existingResult = await this.foldersRepository.findByNameAndParent(
      dto.name,
      parentId,
      clientId,
    );
    if (isFail(existingResult)) throw existingResult.error;
    if (existingResult.value !== null) throw new FolderNameConflictException();

    const createResult = await this.foldersRepository.create({
      name: dto.name,
      parentId,
      clientId,
    });
    if (isFail(createResult)) throw createResult.error;

    return plainToInstance(FolderResponseDto, createResult.value, {
      excludeExtraneousValues: true,
    });
  }

  async renameFolder(
    id: string,
    dto: RenameFolderDto,
    clientId: string,
  ): Promise<FolderResponseDto> {
    const folderResult = await this.foldersRepository.findById(id, clientId);
    if (isFail(folderResult)) throw folderResult.error;
    if (!folderResult.value) throw new FolderNotFoundException();

    const folder = folderResult.value;

    const conflictResult = await this.foldersRepository.findByNameAndParent(
      dto.name,
      folder.parentId,
      clientId,
    );
    if (isFail(conflictResult)) throw conflictResult.error;
    const conflict = conflictResult.value;
    if (conflict !== null && conflict !== undefined && conflict.id !== id) {
      throw new FolderNameConflictException();
    }

    const updatedResult = await this.foldersRepository.rename(id, dto.name);
    if (isFail(updatedResult)) throw updatedResult.error;

    return plainToInstance(FolderResponseDto, updatedResult.value, {
      excludeExtraneousValues: true,
    });
  }

  async deleteFolder(id: string, clientId: string): Promise<void> {
    const folderResult = await this.foldersRepository.findById(id, clientId);
    if (isFail(folderResult)) throw folderResult.error;
    if (!folderResult.value) throw new FolderNotFoundException();

    // ... transaction logic, S3 cleanup, etc.
  }
}
```

> **Key insight**: `throw result.error` works because `result.error` is already
> a `DomainException` instance. No mapping needed.

---

### 4. Controller (`controller/<feature>.controller.ts`)

- **ZERO error handling** — no `isFail`, no `try/catch`, no `mapToHttpException`.
- Just call the service and return the value.
- The global `DomainExceptionFilter` handles all `DomainException` throws.

```typescript
import {
  Body,
  Controller,
  Delete,
  Get,
  HttpCode,
  HttpStatus,
  Param,
  Patch,
  Post,
  Query,
  UseGuards,
} from "@nestjs/common";
import {
  ClientAuthGuard,
  ClientJwtPayload,
  CurrentClientUser,
} from "@app/shared-auth";
import { FoldersService } from "../service/folders.service";
import { CreateFolderDto } from "../dto/create-folder.dto";
import { RenameFolderDto } from "../dto/rename-folder.dto";
import {
  FolderResponseDto,
  PaginatedFoldersResponseDto,
} from "../dto/folder-response.dto";
import { QueryFoldersDto } from "../dto/query-folders.dto";

@UseGuards(ClientAuthGuard)
@Controller("folders")
export class FoldersController {
  constructor(private readonly foldersService: FoldersService) {}

  @Post()
  @HttpCode(HttpStatus.CREATED)
  async createFolder(
    @Body() dto: CreateFolderDto,
    @CurrentClientUser() user: ClientJwtPayload,
  ): Promise<FolderResponseDto> {
    return this.foldersService.createFolder(dto, user.sub);
  }

  @Get()
  async listFolders(
    @Query() query: QueryFoldersDto,
    @CurrentClientUser() user: ClientJwtPayload,
  ): Promise<PaginatedFoldersResponseDto> {
    return this.foldersService.listFolders(user.sub, query);
  }

  @Patch(":id")
  async renameFolder(
    @Param("id") id: string,
    @Body() dto: RenameFolderDto,
    @CurrentClientUser() user: ClientJwtPayload,
  ): Promise<FolderResponseDto> {
    return this.foldersService.renameFolder(id, dto, user.sub);
  }

  @Delete(":id")
  @HttpCode(HttpStatus.NO_CONTENT)
  async deleteFolder(
    @Param("id") id: string,
    @CurrentClientUser() user: ClientJwtPayload,
  ): Promise<void> {
    return this.foldersService.deleteFolder(id, user.sub);
  }
}
```

---

## Anti-Patterns — Never Do These

| Anti-pattern                                          | Why it's wrong                                                 |
| ----------------------------------------------------- | -------------------------------------------------------------- |
| `throw new Error(...)` inside repository              | Breaks explicit Result flow; hides failures from the service   |
| `try/catch` in the controller to handle domain errors | Defeats the purpose; the ExceptionFilter handles this globally |
| `isFail` + `mapToHttpException` in the controller     | Boilerplate; move to service + filter instead                  |
| `result.value!` without a type-guard                  | Unsafe; value is `undefined` on failure                        |
| Nesting `Result` inside `Result`                      | Redundant; propagate directly                                  |
| Returning raw `Promise<T>` from repository            | Hides error paths from the service layer                       |
| Catching `DomainException` in the service             | Let them bubble up to the filter                               |
| Using `HttpException` directly in service             | Couples business logic to HTTP; use `DomainException` instead  |

---

## Helper: `unwrapOrThrow` (optional utility)

If you find `if (isFail(result)) throw result.error;` repetitive in services,
you can create a small helper:

```typescript
// src/shared/result/unwrap.ts
import { Result, isFail } from "./result.type";

export function unwrapOrThrow<T, E extends Error>(result: Result<T, E>): T {
  if (isFail(result)) throw result.error;
  return result.value;
}
```

Usage in services:

```typescript
async createFolder(dto: CreateFolderDto, clientId: string): Promise<FolderResponseDto> {
  const existing = unwrapOrThrow(
    await this.foldersRepository.findByNameAndParent(dto.name, dto.parentId ?? null, clientId),
  );
  if (existing !== null) throw new FolderNameConflictException();

  const folder = unwrapOrThrow(
    await this.foldersRepository.create({ name: dto.name, parentId: dto.parentId ?? null, clientId }),
  );

  return plainToInstance(FolderResponseDto, folder, { excludeExtraneousValues: true });
}
```

---

## Checklist Before Finishing a Feature

- [ ] Every repository method returns `Promise<Result<T, DomainException>>`
- [ ] Every service method returns plain `Promise<T>` (no Result wrapper)
- [ ] Service uses `isFail` + `throw result.error` or `unwrapOrThrow` to consume Results
- [ ] Service throws `DomainException` subclasses for business rule violations
- [ ] No `throw` inside repository for expected errors (use `fail()`)
- [ ] Controller has **zero** error-handling code
- [ ] Feature exceptions extend `DomainException` with proper `errorCode` + `HttpStatus`
- [ ] `DomainExceptionFilter` is registered globally
- [ ] DTOs use `class-validator` decorators
- [ ] Module wires all providers and exports correctly

---

## Refactoring Existing Code

When the user hands you existing code with `isFail` + `mapToHttpException` in controllers:

1. Create `DomainException` subclasses for each error variant in the feature.
2. Update the repository to return `Result<T, DomainException>` using the new exception classes in `fail()`.
3. Update the service to consume Results with `isFail` → `throw result.error`, and throw `DomainException` subclasses for business rules.
4. Change service return types from `Promise<Result<T, Error>>` to plain `Promise<T>`.
5. **Strip all error handling from the controller** — just call the service and return.
6. Remove the old `mapToHttpException` function and error enum if no longer used.
7. Ensure `DomainExceptionFilter` is registered globally.

---

## References

For deeper understanding of the NestJS mechanisms used in this skill, consult:

- `references/nestjs-exception-filters.md` — How NestJS Exception Filters work,
  binding strategies (method, controller, global), `ArgumentsHost`, catch-all
  filters, and inheritance patterns.
