# Archived Unit Tests (Legacy)

This directory stores the pre-phase-7 unit tests that depended on deprecated
APIs (e.g., direct UtilityAgent parsing helpers, legacy ballot parsing flows,
manual language fixtures). They no longer reflect the current harness-driven
architecture, but we keep them for historical context when porting scenarios
into modern component or contract suites.

When migrating a scenario back into the active suite, rebuild it on top of the
prompt harness (`tests/support/`) and remove the archived copy as part of the
change.
