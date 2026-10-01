## Summary

`spring.technology` already declared a service aspect for every annotation Spring
marks a REST operation with, and a `rest` protocol for the paths. The
reconstruction now reports both.

```diff
 interfaces
+  Endpoint {address: /customers}            from @RequestMapping("/customers")
 operations
   GetMapping
+  Endpoint {address: /{customerId}}         from @GetMapping(value = "/{customerId}")
+  PreAuthorize {value: isAuthenticated()}
 parameters
+  PathVariable | RequestBody | Valid | RequestParam{value, required, defaultValue}
```

Every shape Java writes an annotation element in is covered: a marker, the
shorthand `@RequestMapping("/x")`, `value =`, `path =`, and several named
elements. Only literal values are read — `@RequestMapping(method =
RequestMethod.GET)` states no literal, and the text of the expression would be a
value the source does not give.

A path is reported under the reserved name `Endpoint`, not on the mapping,
because the mapping aspects declare no properties while a path is an endpoint
address. Addresses stay relative to the element above them, as Spring and LEMMA
both read them.

## Evidence

Lakeside Mutual's nineteen `@RestController` classes, matched one for one:

```text
37 mapping aspects   21 Get, 7 Post, 5 Put, 3 Patch, 1 Delete
 8 PreAuthorize
68 parameter aspects  22 PathVariable, 17 RequestParam, 15 RequestBody, 14 Valid
39 endpoints         15 of 15 interfaces, 24 of 37 operations
```

The 13 operations without an endpoint are the bare `@GetMapping`/`@PostMapping`
ones, addressed by their interface alone. `@Operation`/`@Parameter` (36/52
occurrences) are OpenAPI annotations the technology model declares nothing for
and are deliberately not carried over.

```text
ruff    All checks passed!
mypy    Success: no issues found in 34 source files
pytest  57 passed          # 49 before
```

New fixture `rest-technology` covers all ten annotation shapes and fails on its
first row without the recovery. Six unit tests pin `get_annotation_values`.

## Merge Danger

**Door:** two-way. Additive meta-data only.

**Blast Radius:** every service model

Nine existing expectations gained an `Endpoint` entry — 54 insertions, no
deletions, each verified against its fixture source. Results reconstructed
before this should be regenerated rather than compared.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
