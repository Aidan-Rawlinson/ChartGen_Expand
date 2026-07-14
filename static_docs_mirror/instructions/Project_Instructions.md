# Project Instructions: ChartGen_Expand

## Project Folder Path
This project maps to the following folder in the MCP root:

"C:\mcp_projects\ChartGen_Expand"

---

## Session Start Protocol

Trigger words: **Review** or **Wake up**

On receiving "Review" or "Wake up", read two sources:
1. dynamic_docs folder (all four documents) -- check Current_State first to establish whether this is a new project or a project in progress before reading further
2. code_base folder (full structure with description of each component, but not the code itself)

If Current_State shows Status: New Project and code_base is empty, use exactly this format:

> Reviewed dynamic_docs: Status is New Project.
> Reviewed code_base: empty -- full sight of project folder confirmed.
>[SHOW EMPTY LINE]
> Working on a secret project, are we, sir?
>[SHOW EMPTY LINE]
> Would you like me to talk through setting up Git on the folder?

If the user says yes, use the Git Setup Guide below as a strong reference. The guide assumes a typical Windows setup -- adapt your support to the user's actual situation rather than following the steps as a rigid script.

For all subsequent sessions, use this format:

> Reviewed code_base: [brief summary of contents].
> Reviewed dynamic_docs: [what Current_State shows, what Next_Session flags].

---

Session End Protocol
Trigger word: Close-down
Close-down should only be initiated once the session's work is complete and ready to commit. The sequence is:
1. Update Current_State.md
Read the current file. Rewrite it in full, but keep concise, to reflect the current state of the project.

2. Update Next_Session.md
Read the current file. Rewrite it in full, but keep concise,  with the handoff for the next session.

3. Update Progression_Log.md
Do not read the existing file. Append a new session entry at the bottom only. Do not rewrite or restate any existing content.

4. Update Decisions.md
Do not read the existing file. Append any new decisions at the bottom only. Do not rewrite or restate any existing content. If no new decisions were made this session, state "No new decisions" and move on.

5. Update static_docs_mirror/project_files
Write any new or changed files, remove any files that are no longer present in Project Files. If unchanged, state "No change to project documents" and move on.

6. Prompt for Project Files update if needed
If project documents have changed, prompt the user to update the Project Files in Claude Desktop and wait for confirmation.

7. Verify Project Files match
List all files in static_docs_mirror/project_files, compare against all files visible in Project Files, and flag any mismatch before proceeding.

8. Check the project folder
Surface everything in the project folder, flag anything that looks like it should not be committed, and ask the user to confirm or amend the .gitignore before proceeding.

9. Propose commit message
Present a suggested commit message using the Git convention — a short summary title on the first line, a blank line, then a fuller description of what changed — and wait for user approval.

10. Commit
If the user approves, trigger the git_commit tool with the agreed message. If the user declines, discuss and revise before proceeding.

11. Confirm
Confirm close-down is complete.

---

## Scrap Session Protocol

Trigger word: **Scrap Session**

On receiving "Scrap Session":
1. Confirm with the user: "Are you sure? This will revert all changes made this session and cannot be undone."
2. Wait for user confirmation
3. Trigger the git_revert tool to restore the project folder to its last committed state
4. Respond: "Project folder restored -- close session"

---

## Git Setup Guide

This guide is a reference for helping the user set up Git on a new project folder. It assumes a typical Windows setup -- use it to shape your support, not as a script to follow rigidly. The user's environment may differ; adapt accordingly.

### Prerequisites
- Git installed on the machine
- A GitHub account

### Steps

**1. Open a command prompt**

**2. Navigate to the project folder**
```
cd C:\mcp_projects\[ProjectName]
```

**3. Initialise Git**
```
git init
```
Expected output: `Initialized empty Git repository in C:/mcp_projects/[ProjectName]/.git/`

**4. Create a repository on GitHub**
Create a new repository on GitHub and copy its URL (format: `https://github.com/[username]/[repo].git`)

**5. Link the remote**
```
git remote add origin https://github.com/[username]/[repo].git
```

**6. Set the default branch**
```
git branch -M main
```

**7. Stage and make the initial commit**
```
git add .
git commit -m "Initial commit"
```

**8. Set the upstream and push**
```
git push -u origin main
```

### Notes
- Steps 7 and 8 must be done in this order -- git push -u origin main will fail if there are no commits yet.
- From this point, all future commits and pushes are handled by the Close-down protocol.
- Authentication: GitHub requires a Personal Access Token (PAT) as the password when pushing via HTTPS. If prompted, use the PAT not the GitHub account password. Generate one at GitHub -- Settings -- Developer Settings -- Personal Access Tokens -- Tokens (classic) -- repo scope.

---

## Project-Specific Conventions

- "Keep responses short unless I ask for detail"
- "Don't speculate — ask if unclear"
- "Don't read files unless explicitly instructed to"
- "Don't summarise at the end of a response unless asked"
- "Return only what was asked for — no explanation wrap"