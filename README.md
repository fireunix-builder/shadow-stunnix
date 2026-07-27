# STunnix Builder

Public multi-platform build and release automation for the private
`fireunix-app/shadow-stunnix` repository.

The private source is checked out only on ephemeral GitHub-hosted runners with
a repository-scoped, read-only PAT. Private source and project build output are
excluded from repository content, workflow artifacts, and caches. Release
archives contain compiled binaries and explicitly published runtime templates
only.

