# Contributing

`opendatalab/Sciverse-Agent-Tools` is the primary development repository for
the SciVerse Agent Tools project. Issues, PRs, and discussions all happen
here.

## Reporting issues

- Bug reports (please include version: `pip show sciverse` /
  `npm view sciverse version`)
- Feature requests
- Tool description / SKILL.md improvements
- Documentation typos and clarifications

## Pull requests

PRs are welcome — they're merged directly into `main` after review.

Workflow:

1. Fork or branch
2. Make changes; follow [Conventional Commits](https://www.conventionalcommits.org/)
   in your commit messages
3. Open a PR — the `test.yml` workflow runs SDK + MCP tests + lint +
   drift-check
4. Maintainer reviews
5. Merge to `main` → `release.yml` runs `semantic-release` → automated PyPI /
   npm / ClawHub publish

## Release process

Versions are managed by `semantic-release` — commit messages following
[Conventional Commits](https://www.conventionalcommits.org/) drive automated
version bumps and publishing:

| Type | Effect |
|---|---|
| `feat: ...` | minor bump |
| `fix: ...` / `perf: ...` / `refactor: ...` / `docs: ...` | patch bump |
| `chore: ...` / `style: ...` / `test: ...` | no release |
| Anything with `BREAKING CHANGE:` footer or `!` suffix | major bump |

On every push to `main`, the `release.yml` workflow:

1. Analyses commits since the last tag
2. Bumps `openapi.yaml` / Python / TypeScript / MCP / ClawHub manifest versions
3. Regenerates derived artifacts (SDK tool constants, ClawHub SKILL.md, ...)
4. Publishes to PyPI / npm / ClawHub
5. Tags `v${version}` and creates a GitHub Release with notes
6. Commits the bump back to `main` with `[skip ci]`

## License

[Apache-2.0](./LICENSE)
