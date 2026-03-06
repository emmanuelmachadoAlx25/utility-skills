# Tailwind Color Refactor — Pattern Reference

## Full Regex Pattern

```python
HEX_PATTERN = re.compile(
    r'(\[class\.)?'
    r'(text|bg|border|divide|ring|placeholder|outline|accent|caret|fill|stroke|shadow|decoration|from|via|to)'
    r'-\[#([0-9a-fA-F]{3,6})\]'
    r'(\])?',
    re.IGNORECASE
)
```

### Group breakdown

| Group | Captures                       | Example                   |
| ----- | ------------------------------ | ------------------------- |
| `\1`  | Optional `[class.` for Angular | `[class.` or empty        |
| `\2`  | Tailwind utility prefix        | `text`, `bg`, `border`    |
| `\3`  | Hex color without `#`          | `29cd7b`, `cfd`, `AABBCC` |
| `\4`  | Optional `]` closing Angular   | `]` or empty              |

---

## Pattern Examples

### Standard HTML / JSX / TSX

```
text-[#29cd7b]      → text-29cd7b
bg-[#e5ecec]        → bg-e5ecec
border-[#cfdcdb]    → border-cfdcdb
divide-[#d8e2e1]    → divide-d8e2e1
ring-[#cfdcdb]      → ring-cfdcdb
```

### Angular Template Binding

```
[class.border-[#d8e2e1]]   → [class.border-d8e2e1]
[class.text-[#29cd7b]]     → [class.text-29cd7b]
[class.bg-[#e5ecec]]       → [class.bg-e5ecec]
```

### Short Hex (3-char)

```
text-[#abc]    → (expanded to #aabbcc) → text-aabbcc
bg-[#fff]      → bg-ffffff (or matches --color-white if defined as #ffffff)
```

---

## CSS Theme Pattern

```python
THEME_BLOCK_PATTERN = re.compile(r'@theme\s*\{([^}]+)\}', re.DOTALL)
COLOR_VAR_PATTERN   = re.compile(r'--color-([a-zA-Z0-9_-]+)\s*:\s*#([0-9a-fA-F]{3,6})\s*;')
```

Parses `@theme { --color-NAME: #HEX; }` into `{ "hex" → "NAME" }`.

---

## File Types Scanned

| Extension | Notes                                                     |
| --------- | --------------------------------------------------------- |
| `.html`   | Standard HTML, Angular templates                          |
| `.jsx`    | React JSX                                                 |
| `.tsx`    | React TypeScript                                          |
| `.ts`     | Angular component inline templates, string class bindings |
| `.js`     | Vanilla JS string templates                               |

Add more via `--ext` CLI flag.
