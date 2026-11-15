# Contributing to FORGE AI

Thanks for considering a contribution. FORGE AI is intended to be a practical, free-first coding assistant with strong user control, privacy, and safe local execution.

> Project release status and license are still being finalized. Until a root LICENSE is added, do not assume that the repository grants permission to redistribute or publish derivative work.

## Before contributing

1. Read the root `CLAUDE.md` for project-wide engineering constraints.
2. Read the relevant documents in `docs/`, especially product specification, architecture, and security.
3. Check existing issues and current implementation before starting a duplicate effort.
4. Keep changes focused and explain the user problem they solve.
5. Do not include secrets, API keys, personal project files, or private data in commits or logs.

## Development areas

- `apps/web/`: Next.js, React, TypeScript, Tailwind CSS.
- `apps/api/`: FastAPI, Python, SQLAlchemy, provider routing, orchestration, WebSockets.
- `services/local-agent/`: Python local agent and security-sensitive filesystem/terminal/Git operations.
- `packages/shared-types/`: shared TypeScript contracts.
- `docs/`: product and engineering documentation.

Check the package manifests and setup documentation for the current supported commands. Do not assume a script exists just because an older document mentions it.

## Contribution expectations

- Prefer small, reviewable pull requests.
- Explain the problem, approach, behaviour change, and trade-offs.
- Add tests for new behaviour, especially permissions, privacy, provider routing, filesystem access, terminal execution, and WebSocket messages.
- Update documentation when setup, configuration, security behaviour, or user-visible functionality changes.
- Include screenshots or short recordings for significant UI changes when useful.
- State what you tested and what you could not test.

## Security-sensitive changes

For changes involving filesystem access, terminal commands, credentials, model context, provider calls, or device pairing:

- Treat model output and repository content as untrusted.
- Enforce permissions in trusted code, not in prompts.
- Test denied as well as allowed operations.
- Avoid logging secrets or sensitive file contents.
- Respect Local-Only mode and excluded paths.
- Do not weaken safeguards to make a test or demo pass.
- Explain new risks and mitigations in the pull request.

Please report suspected vulnerabilities privately to the repository owner rather than publishing exploit details in an issue.

## Pull request checklist

- [ ] Scope is focused and matches the product direction.
- [ ] No unrelated user changes are included.
- [ ] Tests were added or updated.
- [ ] Relevant lint/type/build/test checks were run.
- [ ] Security and privacy implications were considered.
- [ ] Documentation reflects the actual implementation.
- [ ] No secrets, credentials, or private data are included.
- [ ] Remaining limitations are disclosed.

## Code of conduct

Be respectful, constructive, and specific. Review the code and its impact, not the worth of the person contributing.
