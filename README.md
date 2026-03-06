# utility-skills

Colección de skills reutilizables para agentes de IA (Claude, Cursor, Codex) que automatizan patrones de código y refactorización en proyectos reales.

## Skills disponibles

### 1. Result Pattern — NestJS

> `result-pattern-nestjs/`

Aplica el **Result Pattern** en features de NestJS para manejo de errores explícito y type-safe. Elimina el uso de `throw` para errores esperados y reemplaza `try/catch` con type guards (`isFail`, `isSuccess`).

**Qué genera:**

- Enum de errores de dominio con mapper a excepciones HTTP
- Repository, Service y Controller que retornan `Promise<Result<T, Error>>`
- Guardias de tipo en el controller en lugar de `try/catch`

**Cuándo usarlo:**

- Al crear un nuevo módulo/feature en NestJS
- Al refactorizar código existente que usa excepciones para control de flujo
- Al agregar un caso de uso o método de servicio

**Estructura generada:**

```
src/<feature>/
├── <feature>.error.ts        # Enum de errores + mapper HTTP
├── <feature>.entity.ts       # Entidad de dominio
├── <feature>.dto.ts          # DTOs con class-validator
├── <feature>.repository.ts   # Acceso a datos → Result
├── <feature>.service.ts      # Lógica de negocio → Result
├── <feature>.controller.ts   # Capa HTTP → mapea Result a respuesta
└── <feature>.module.ts       # Wiring del módulo
```

---

### 2. Tailwind Color Refactor

> `tailwind-color-refactor/`

Script de Python que reemplaza colores hex hardcodeados en clases de Tailwind CSS (`bg-[#abc123]`, `text-[#ff0000]`) con variables CSS definidas en un bloque `@theme`.

**Qué hace:**

- Parsea el bloque `@theme { --color-name: #hex; }` de tu archivo CSS
- Escanea archivos `.html`, `.jsx`, `.tsx`, `.ts`, `.js` buscando clases Tailwind con hex inline
- Reemplaza con el nombre de la variable CSS (match exacto o fuzzy con distancia euclidiana en RGB)
- Agrega automáticamente nuevas variables al `@theme` cuando no hay match

**Soporta:**

- Clases estándar: `text-[#29cd7b]` → `text-primary`
- Bindings de Angular: `[class.border-[#d8e2e1]]` → `[class.border-border-light]`
- Hex corto de 3 caracteres: `bg-[#fff]` → `bg-white`

**Uso:**

```bash
python tailwind-color-refactor/scripts/refactor_colors.py \
  --css src/styles.css \
  --src src/ \
  --dry-run
```

| Flag        | Descripción                                  |
| ----------- | -------------------------------------------- |
| `--css`     | Ruta al archivo CSS con el bloque `@theme`   |
| `--src`     | Directorio fuente a escanear                 |
| `--ext`     | Extensiones (default: `html,jsx,tsx,ts,js`)  |
| `--dry-run` | Previsualiza cambios sin modificar archivos   |

**Documentación adicional:**

- [`references/patterns.md`](tailwind-color-refactor/references/patterns.md) — Regex utilizado y ejemplos de patrones soportados
- [`references/color-distance.md`](tailwind-color-refactor/references/color-distance.md) — Algoritmo de distancia de color y umbral de fuzzy matching

---

## Cómo usar estas skills en tu proyecto

### Opción A — Como skill de agente (Cursor / Claude / Codex)

1. Clona o copia la carpeta de la skill que necesitas dentro de tu directorio de skills:

   ```bash
   # Ejemplo para Cursor
   cp -r result-pattern-nestjs ~/.cursor/skills/result-pattern-nestjs

   # Ejemplo para Claude
   cp -r result-pattern-nestjs ~/.claude/skills/result-pattern-nestjs
   ```

2. El agente detectará el `SKILL.md` automáticamente y aplicará las reglas al generar o refactorizar código.

### Opción B — Como script independiente (Tailwind Color Refactor)

1. Ejecuta el script directamente desde este repositorio:

   ```bash
   python tailwind-color-refactor/scripts/refactor_colors.py \
     --css tu-proyecto/src/styles.css \
     --src tu-proyecto/src/ \
     --dry-run
   ```

2. Revisa el reporte de cambios y, si todo se ve bien, ejecuta sin `--dry-run` para aplicar.

### Opción C — Como referencia

Lee los archivos de cada skill para entender los patrones y aplicarlos manualmente en tu código.
