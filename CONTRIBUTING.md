# Contributing

## Development flow

1. Create a branch from `main`
2. Implement focused changes
3. Run local checks:

```bash
make lint
make test
docker compose config >/dev/null
```

4. Update docs for behavior/config changes
5. Open a PR using the template

## Commit and PR quality

- Keep commits atomic
- Include migration files with model changes
- Include tests for new API behavior
- Avoid introducing secrets in commits

## Release compatibility

For changes that impact deployment or API contracts, include:

- backward-compatibility note
- upgrade steps
- rollback note
