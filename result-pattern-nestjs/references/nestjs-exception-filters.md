# NestJS Exception Filters — Reference

> Source: https://docs.nestjs.com/exception-filters

## Overview

NestJS has a built-in exceptions layer that processes unhandled exceptions
across the application. When an exception is not caught by application code, the
global exception filter catches it and returns an appropriate response.

By default, unrecognized exceptions produce:

```json
{ "statusCode": 500, "message": "Internal server error" }
```

`HttpException` and its subclasses are handled automatically with the correct
status code and message.

---

## Custom Exceptions

Extend `HttpException` (or create your own hierarchy) for domain-specific errors:

```typescript
export class ForbiddenException extends HttpException {
  constructor() {
    super('Forbidden', HttpStatus.FORBIDDEN);
  }
}
```

In our architecture, we use `DomainException` (which extends `Error`, NOT
`HttpException`) so that domain logic stays decoupled from HTTP concerns.

---

## Exception Filters

Implement `ExceptionFilter` and decorate with `@Catch()`:

```typescript
@Catch(DomainException)
export class DomainExceptionFilter implements ExceptionFilter {
  catch(exception: DomainException, host: ArgumentsHost) {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse<Response>();

    response.status(exception.statusCode).json({
      statusCode: exception.statusCode,
      errorCode: exception.errorCode,
      message: exception.message,
    });
  }
}
```

---

## Binding Filters

### Method-scoped

```typescript
@Post()
@UseFilters(DomainExceptionFilter)
async create(@Body() dto: CreateDto) { ... }
```

### Controller-scoped

```typescript
@UseFilters(DomainExceptionFilter)
@Controller('cats')
export class CatsController { ... }
```

### Global-scoped (preferred for our architecture)

**Option A — in `main.ts` (no DI):**

```typescript
app.useGlobalFilters(new DomainExceptionFilter());
```

**Option B — via module provider (supports DI):**

```typescript
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

> Use Option B when the filter needs injected services (logging, i18n, etc.).

---

## Catch-All Filter

To handle ALL exceptions (not just `DomainException`), use `@Catch()` with no
arguments. Useful as a fallback safety net:

```typescript
@Catch()
export class AllExceptionsFilter implements ExceptionFilter {
  catch(exception: unknown, host: ArgumentsHost) {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse<Response>();

    const status =
      exception instanceof HttpException
        ? exception.getStatus()
        : exception instanceof DomainException
          ? exception.statusCode
          : HttpStatus.INTERNAL_SERVER_ERROR;

    response.status(status).json({
      statusCode: status,
      message: exception instanceof Error ? exception.message : 'Internal server error',
    });
  }
}
```

---

## ArgumentsHost

`ArgumentsHost` provides access to the handler's arguments. For HTTP:

```typescript
const ctx = host.switchToHttp();
const request = ctx.getRequest<Request>();
const response = ctx.getResponse<Response>();
```

Also supports WebSocket (`switchToWs()`) and RPC (`switchToRpc()`) contexts.

---

## Inheritance

Extend `BaseExceptionFilter` to reuse the default behavior and only override
specific cases:

```typescript
@Catch()
export class CustomFilter extends BaseExceptionFilter {
  catch(exception: unknown, host: ArgumentsHost) {
    // Custom logic here...
    super.catch(exception, host); // Fallback to default
  }
}
```

> When extending `BaseExceptionFilter` and registering globally, pass the
> `HttpAdapter` reference via the constructor.
