# Onboarding

rs-mock is a super lightweight redshift mocker for in-process.

## How it Works

This relies on duckdb and sqlglot. We take redshift sql and turn it into duckdb to run against duckdb databases.

## Codebase style and guidelines

Coding style: All code must be clean, documented and minimal. That means:

- Use `uv` for everything, there's a make command for common commands
- Keep It Simple Stupid (KISS) by reducing the "Concept Count". That means,
  strive for fewer functions or methods, fewer helpers. If a helper is only
  called by a single callsite, then prefer to inline it into the caller.
- At the same time, Don't Repeat Yourself (DRY)
- There is a tension between KISS and DRY. If you find yourself in a situation
  where you're forced to make a helper method just to avoid repeating yourself,
  the best solution is to look for a way to avoid even having to do the
  complicated work at all.
- If some code looks heavyweight, perhaps with lots of conditionals, then think
  harder for a more elegant way of achieving it. In some cases however (like pattern matching), this is innevitable and fine.
- Code should have comments and functions should have docstrings, but both should be
  concise. The best comments are ones that introduce invariants, or prove that invariants are being upheld, or indicate which invariants the code relies upon. Don't write duplicate comments, overly long comments, or comments for things that are obvious from
  reading the code.
- It's ok to write unperformant code, especially when building a new feature, or fixing one. Performance is all relative, we need something useful at first, performant later. 

- **Unreachable states must raise, not silently degrade.** Do not use defensive
  programming to handle states that should be impossible!

## Commands

```bash
make test # run tests

make lint # run linter and type checker

make prek # run prek/pre-commit
```