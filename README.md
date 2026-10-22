# STunnix Builder

Public multi-platform build and release automation for the private
`fireunix-app/shadow-stunnix` repository.

The private source is checked out only on ephemeral GitHub-hosted runners with
a repository-scoped, read-only deploy key. Private source and project build output are
excluded from repository content, workflow artifacts, and caches. Release
archives contain compiled binaries and explicitly published runtime templates
only.

GitHub Releases are written back to the private STunnix repository with a short-lived installation token of the
`fireunix-publisher` GitHub App (`RELEASE_APP_CLIENT_ID` /
`RELEASE_APP_PRIVATE_KEY` secrets), scoped to that one repository. This public repository never hosts
Releases; R2 receives only the reviewed binary archives and checksums.
The requested release tag must already exist in the private source repository.

Private source checkouts use `SOURCE_DEPLOY_KEY` Actions secrets. Each public key is registered with read-only access on its corresponding private repository. Release identity is checked against the fetched Git tag; source read access does not require a personal token.
