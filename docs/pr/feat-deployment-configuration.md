## Summary

The Docker plugin reads each container's `application.properties` and reports the
deployment configuration, so a container can carry `default values` in LEMMA.

```diff
 operation nodes
   CustomerCoreContainer
     ComposeService      {Name: customer-core}
+    ServiceProperties   {springApplicationName: customer-core, serverPort: 8110}
```

The keys are the names a technology model declares (`springApplicationName`,
`serverPort`), not the Spring property names, so the LEMMA side carries them over
unchanged.

## Evidence

Lakeside Mutual, `-p Java Spring Docker -t <root> --replace`:

| container | springApplicationName | serverPort |
|---|---|---|
| CustomerCoreContainer | customer-core | 8110 |
| CustomerManagementBackendContainer | customer-management-backend | 8100 |
| CustomerSelfServiceBackendContainer | customer-self-service-backend | 8080 |
| PolicyManagementBackendContainer | policy-management-backend | 8090 |
| AppContainer | customer-core | 8110 |

The four containers without properties (three frontends, RiskManagementServer)
are exactly the four that deploy no microservice and are left out of the model
anyway.

```text
ruff    All checks passed!
mypy    Success: no issues found in 34 source files
pytest  49 passed
```

## Merge Danger

**Door:** two-way. Additive meta-data; no schema change, no existing field moves.

**Blast Radius:** operation documents

A consumer that does not know `ServiceProperties` ignores it. Needs the matching
LEMMA branch to become visible; without it the documents simply carry a key
nothing reads.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
