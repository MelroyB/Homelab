# Publishing and Build Automation

## What is automated

After setup, GitHub Actions will:

- run CI on PRs, main/develop pushes, and version tags (`v*.*.*`)
- run a publish quality gate (lint/test/build/compose validation) before release images
- publish Docker images for backend/frontend on version tags
- create a GitHub Release with generated notes on version tags

Workflows:

- `.github/workflows/ci.yml`
- `.github/workflows/docker-publish.yml`

## Registry targets

### GHCR (default)

Images are published to:

- `ghcr.io/<owner>/<repo>-backend`
- `ghcr.io/<owner>/<repo>-frontend`

Tags include:

- semantic tag (`vX.Y.Z`)
- version without `v` (`X.Y.Z`)
- `latest`
- commit SHA tag

### Docker Hub (optional)

If secrets exist, images are also published to:

- `<DOCKERHUB_USERNAME>/homelab-control-backend`
- `<DOCKERHUB_USERNAME>/homelab-control-frontend`

Required repo secrets:

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

## GitHub repository setup checklist

1. Set default branch to `main`
2. Enable branch protection on `main`:
   - require PR
   - require CI checks
3. Enable GitHub Actions and Packages permissions
4. Add Docker Hub secrets if Docker Hub publishing is required
5. Verify `GITHUB_TOKEN` has package write permission (workflow permissions are set)

## Release process

1. Merge release-ready code to `main`
2. Create and push a version tag:

```bash
git tag -a v0.1.0 -m "Release v0.1.0"
git push origin v0.1.0
```

3. Automation runs:
   - CI
   - Docker publish
   - GitHub release notes generation (inside `docker-publish.yml`)

## Manual publish (without tag)

`docker-publish.yml` supports `workflow_dispatch` with `version` input.
Use this only when needed; tag-based release is preferred for traceability.

## Verifying published artifacts

- GHCR: `https://github.com/<owner>/<repo>/pkgs/container/...`
- Docker Hub: `https://hub.docker.com/r/<username>/...`
- GitHub Releases page should contain the new version entry

## Deployment from published images (optional)

Use the provided `docker-compose.publish.yml` overlay to deploy released images:

```bash
BACKEND_IMAGE=ghcr.io/<owner>/<repo>-backend:v0.1.0 \
FRONTEND_IMAGE=ghcr.io/<owner>/<repo>-frontend:v0.1.0 \
docker compose -f docker-compose.yml -f docker-compose.publish.yml up -d
```
