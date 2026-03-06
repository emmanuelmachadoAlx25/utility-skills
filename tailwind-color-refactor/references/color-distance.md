# Color Distance Algorithm

## Formula Used

Simple Euclidean distance in RGB space:

```
distance = sqrt( (R1-R2)² + (G1-G2)² + (B1-B2)² )
```

- **Min distance**: 0 (identical colors)
- **Max distance**: ~441 (black #000000 vs white #ffffff)

## Threshold

| Distance | Decision                               |
| -------- | -------------------------------------- |
| 0        | Exact match                            |
| 1–19     | Fuzzy match — substitute and warn user |
| 20+      | No match — create new CSS variable     |

The threshold of **20** was chosen to catch:

- Minor hex typos (`#cfdcdb` vs `#cfdcdc`)
- Nearly identical shades used inconsistently across the codebase

## When to review fuzzy matches

A fuzzy substitution means the original color was close but **not identical** to a theme variable.
Always review these because:

1. The designer may have intentionally used a slightly different tone
2. Accessibility contrast ratios can shift with small color changes
3. Brand colors may have been typo'd — worth unifying anyway

## Example

```
#d8e3e1 vs #d8e2e1

R: 216 vs 216 → diff 0
G: 227 vs 226 → diff 1
B: 225 vs 225 → diff 0

distance = sqrt(0 + 1 + 0) = 1.0  ← FUZZY MATCH (well within threshold 20)
```

This would substitute `d8e3e1` with variable `d8e2e1` and warn the user.
