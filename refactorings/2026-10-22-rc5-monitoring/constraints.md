You are resolving a security smell in a microservice system, inside a
throwaway git worktree. Hard constraints, which override anything else:

- Change application-level configuration and code only. Never Kubernetes
  manifests, never a service mesh: the verifying toolchain does not read
  manifests, so a mesh change cannot be shown to work.
- Change BOTH ends of every channel. A server with TLS and clients still on
  plaintext is a broken system, not a refactored one.
- Never edit a .services, .data or .operation file. They are reconstructed
  output, not input.
- Never weaken verification to make a connection succeed. No TrustAllStrategy,
  no NoopHostnameVerifier, no InsecureTrustManagerFactory, no
  rejectUnauthorized:false.
- Never disable a test or weaken an assertion. Updating a test's configuration
  so it addresses the new transport is allowed and expected.
- Commit no generated key material. Commit the script that generates it and
  add the output to .gitignore.
- Stay inside this worktree.

Work autonomously. Do not ask questions; make the reasonable choice and record
it in a file called REFACTORING-NOTES.md at the repository root, listing what
you changed, what you assumed, and anything you could not verify.
