# Release convention

When the user asks to push, also create a versioned GitHub release and build its installers. A source push alone does not fulfill the request.

Run appropriate tests, update the app and installer version, commit, push main and a new version tag. Inspect the Actions run and release assets. Report queued or failed builds accurately; only call the update available when the installer assets have been published.
