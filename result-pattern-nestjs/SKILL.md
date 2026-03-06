---
name: result-pattern-nestjs
description: >
  Enforce the Result Pattern for explicit, type-safe error handling across all
  NestJS feature layers (repository, service, controller). Use whenever creating
  or refactoring a NestJS feature that performs I/O, business-logic validation,
  or any operation that can fail.
---

# Result Pattern — NestJS Features

## Purpose

This skill ensures every NestJS feature is implemented with the Result Pattern:
no raw `throw` for expected errors, no untyped `try/catch` propagation, and no
ambiguous `Promise<T>` return types that hide failure paths.

Apply this skill when the user asks to:

- Create a new NestJS feature/module
- Add a use-case or service method
- Refactor existing code that uses exceptions for control flow

---

## Core Contracts (never deviate from these)

### Imports

```typescript
import { Result, success, fail, isFail, isSuccess } from "src/shared/result";
```

### Creating results

| Situation                         | Code                                    |
| --------------------------------- | --------------------------------------- |
| Operation succeeded with data     | `return success(entity);`               |
| Operation succeeded with no data  | `return success<void>(undefined);`      |
| Operation failed (expected error) | `return fail(DomainError.SomeVariant);` |

### Consuming results (type guards)

```typescript
const result = await this.service.doSomething(dto);

if (isFail(result)) {
  // result.error is fully typed here — no cast needed
  throw mapToHttpException(result.error);
}

// result.value is fully typed here — no cast needed
return result.value;
```

> ⚠️ **Never** access `result.value` or `result.error` without first narrowing
> with `isSuccess(result)` or `isFail(result)`.

---

## Feature Structure

For every new feature, generate these files:

```
src/
└── <feature>/
    ├── <feature>.error.ts       ← Domain error enum + HTTP mapper
    ├── <feature>.entity.ts      ← TypeORM / domain entity
    ├── <feature>.dto.ts         ← class-validator DTOs
    ├── <feature>.repository.ts  ← Data access, returns Result
    ├── <feature>.service.ts     ← Business logic, returns Result
    ├── <feature>.controller.ts  ← HTTP layer, maps Result → HTTP
    └── <feature>.module.ts      ← NestJS module wiring
```

---

## Layer-by-Layer Rules

### 1. Error definitions (`<feature>.error.ts`)

- Use an `enum` for all **expected** domain errors (not found, duplicate, invalid
  business rule, DB failure).
- Export a `mapToHttpException(error: FeatureError): HttpException` switch that
  maps every enum variant to an HTTP status. Add a `default` that returns 500.

```typescript
import { HttpException, HttpStatus } from "@nestjs/common";

export enum UserError {
  NotFound = "USER_NOT_FOUND",
  AlreadyExists = "USER_ALREADY_EXISTS",
  InvalidInput = "USER_INVALID_INPUT",
  DatabaseError = "USER_DATABASE_ERROR",
}

export function mapToHttpException(error: UserError): HttpException {
  switch (error) {
    case UserError.NotFound:
      return new HttpException(error, HttpStatus.NOT_FOUND);
    case UserError.AlreadyExists:
      return new HttpException(error, HttpStatus.CONFLICT);
    case UserError.InvalidInput:
      return new HttpException(error, HttpStatus.BAD_REQUEST);
    case UserError.DatabaseError:
      return new HttpException(error, HttpStatus.INTERNAL_SERVER_ERROR);
    default:
      return new HttpException(
        "Unexpected error",
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
  }
}
```

---

### 2. Repository (`<feature>.repository.ts`)

- Return `Promise<Result<T, FeatureError>>` on every public method.
- Wrap **all** `await` calls in a single `try/catch`; map the catch to
  `DatabaseError`.
- Use `success(entity)` or `fail(FeatureError.Variant)` — never `throw`.

```typescript
@Injectable()
export class UserRepository {
  constructor(
    @InjectRepository(User)
    private readonly repo: Repository<User>,
  ) {}

  async findById(id: string): Promise<Result<User, UserError>> {
    try {
      const user = await this.repo.findOneBy({ id });
      if (!user) return fail(UserError.NotFound);
      return success(user);
    } catch {
      return fail(UserError.DatabaseError);
    }
  }

  async save(user: User): Promise<Result<User, UserError>> {
    try {
      const saved = await this.repo.save(user);
      return success(saved);
    } catch {
      return fail(UserError.DatabaseError);
    }
  }
}
```

---

### 3. Service (`<feature>.service.ts`)

- Return `Promise<Result<T, FeatureError>>` on every public method.
- Perform business-logic validation **before** calling the repository; return
  `fail(FeatureError.InvalidInput)` immediately on violation.
- **Propagate** repository failures without wrapping them again:

```typescript
@Injectable()
export class UserService {
  constructor(private readonly userRepository: UserRepository) {}

  async getUserById(id: string): Promise<Result<User, UserError>> {
    return this.userRepository.findById(id);
  }

  async createUser(dto: CreateUserDto): Promise<Result<User, UserError>> {
    // Business rule validation
    if (!dto.email.includes("@")) {
      return fail(UserError.InvalidInput);
    }

    const user = new User(dto.email, dto.name);
    return this.userRepository.save(user);
  }
}
```

---

### 4. Controller (`<feature>.controller.ts`)

- Always check with `isFail(result)` first; throw the mapped exception.
- Return `result.value` directly after the guard — no further unwrapping needed.
- Do **not** add try/catch here; the Result pattern already handles expected
  failures. NestJS global filters handle unexpected ones.

```typescript
@Controller("users")
export class UserController {
  constructor(private readonly userService: UserService) {}

  @Get(":id")
  async getUser(@Param("id") id: string) {
    const result = await this.userService.getUserById(id);
    if (isFail(result)) throw mapToHttpException(result.error);
    return result.value;
  }

  @Post()
  @HttpCode(HttpStatus.CREATED)
  async createUser(@Body() dto: CreateUserDto) {
    const result = await this.userService.createUser(dto);
    if (isFail(result)) throw mapToHttpException(result.error);
    return result.value;
  }
}
```

---

## Anti-Patterns — Never Do These

| Anti-pattern                                              | Why it's wrong                                                                                        |
| --------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `throw new Error(...)` inside service/repository          | Breaks explicit flow; hides failures from callers                                                     |
| `try/catch` in the controller to handle domain errors     | Defeats the purpose; use `isFail` instead                                                             |
| `result.value!` without a type-guard                      | Unsafe; value is `undefined` on failure                                                               |
| Nesting `Result` inside `Result`                          | Redundant; propagate directly                                                                         |
| Returning a raw `Promise<T>` when failure is possible     | Hides error paths from TypeScript and from the caller                                                 |
| Using `result.isSuccess()` / `result.isFailure()` methods | Use the `isSuccess()` / `isFail()` **helper functions** (not methods), they act as proper type guards |

---

## Checklist Before Finishing a Feature

Before declaring the feature done, verify:

- [ ] Every repository method returns `Promise<Result<T, FeatureError>>`
- [ ] Every service method returns `Promise<Result<T, FeatureError>>`
- [ ] No `throw` inside service or repository for expected errors
- [ ] All enum variants are covered in `mapToHttpException`
- [ ] Controller uses `isFail(result)` guard before accessing `.value`
- [ ] DTOs use `class-validator` decorators
- [ ] Module wires all providers and exports correctly

---

## Refactoring Existing Code

When the user hands you existing code that throws exceptions:

1. Identify every `throw` and every `try/catch` in services and repositories.
2. Create (or extend) the domain error enum with appropriate variants.
3. Replace `throw` statements with `return fail(DomainError.Variant)`.
4. Replace catch blocks with `return fail(DomainError.DatabaseError)`.
5. Update method signatures to `Promise<Result<T, DomainError>>`.
6. Update the controller to use `isFail` guards instead of try/catch.
7. Add the missing `mapToHttpException` entry for each new variant.
