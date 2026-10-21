# AGENTS.md

Guidance for AI coding agents (Claude Code, Codex, etc.) working in this repository.

## Context

- Collaborative coding hackathon: 2 hours, 4 problems, problems unseen until start.
- Team of 4 humans, each working with their own agent. Several agents may edit this repo at the same time.
- Language, framework, build and test commands are not known yet. Do not assume any; check the problem statement and existing files first.

## Layout

- `q1/`, `q2/`, `q3/`, `q4/`: one folder per problem (assumed mapping, confirm when problems are released). Currently each holds only a placeholder `lighthouses.txt` that can be deleted.

## Problem status

- **Q2 (Word Search Generation): DONE. Do not modify anything in `q2/`.** The submission is `q2/solution_improved.py`, which passed the judge. Everything else is archived in `q2/archive/`. See `q2/README.md`.

## Working rules

- Time is the scarce resource. Get a simple correct solution passing the given examples first, then optimise.
- Stay inside the folder of the problem you were assigned. Do not edit another problem's folder or shared files (including this one) unless asked.
- Keep each problem self-contained: its own code, input and run instructions, no cross-folder imports.
- Commit small and often; `git pull --rebase` before `git push` to avoid clobbering teammates. Never force-push.
- Don't commit large generated files, build output or secrets.

## Update this file

Once the languages, run/test commands and problem details are known, record them here (and delete this line), ideally one short section per problem.
