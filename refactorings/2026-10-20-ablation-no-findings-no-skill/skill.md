No skill was loaded for this proposal, and none was available: the CLI was
invoked without --plugin-dir.

This is the ablation. It isolates what the reconstructed models and the
smell-specific skill contribute, by removing both and leaving everything else
as it was: the same system and commit, the same model, the same throwaway
worktree, the same allowlist, and the same invariant constraints.

The constraints are deliberately kept. They are enforced by the harness rather
than known by the model, and removing them would change what the gates measure
- a proposal free to edit a .services file or disable a test is not a weaker
refactoring, it is a different experiment.

What was removed:
  - the findings, and with them the channel inventory and the root cause
  - the facts quoted from the models, and the names of the affected services
  - the skill: the recipes for Spring REST, ActiveMQ and certificate
    provisioning, and the clean-checkout criterion
