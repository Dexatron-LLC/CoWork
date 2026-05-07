# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project intent

CoWork is an AI coworking / agent-collaboration tool. The repository is in a greenfield state — there is no source code, build system, or test suite yet. Architecture and tooling decisions are still open.

## Status: greenfield

When operating in this repo, **do not fabricate** commands, file layouts, or conventions that are not present. If something looks like it should exist (a build script, a module, a config file) and it does not, ask the user rather than inventing it.

This file should be updated by whichever session establishes the first concrete decisions — language/runtime, package manager, test framework, directory layout — so subsequent sessions inherit real context rather than this notice.

## Owner / context

- GitHub: `Dexatron-LLC/CoWork` (public)
- Maintainer: Dexter J. Le Blanc Jr. (`dexter@dexatron.com`)
- Local working directory: `/mnt/d/Source/AI/cowork` (WSL view of `D:\Source\AI\cowork`)

## Update protocol

Once the project has real structure, replace the *Status: greenfield* section with:

1. **Common commands** — only the non-obvious ones (e.g. how to run a single test, how to start the dev loop), not generic `npm install` boilerplate.
2. **Architecture** — the cross-file "big picture" that requires reading several modules to reconstruct. Skip anything a `find` or `grep` would surface in seconds.
3. **Conventions that aren't enforced by tooling** — naming rules, layering boundaries, anything a linter wouldn't catch.

Leave the *Project intent* and *Owner / context* sections in place.
