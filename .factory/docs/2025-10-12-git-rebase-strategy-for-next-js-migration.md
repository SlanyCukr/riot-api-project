## Rebase Strategy

### Current Situation
- **Local main**: Has 2 commits migrating to Next.js (commits `5983b10`, `1b5df29`)
- **origin/main**: Has 2 commits with Vite/React frontend changes (commits `f7967d5`, `5d16f07`)
- The branches diverged at commit `fa6d762`

### Commits to Integrate from origin/main

#### Commit 1: `5d16f07` - "Added project scope and recommended extensions"
**Files changed:**
- `.gitignore` - Added entries
- `.vscode/.prettierignore` - New file
- `.vscode/extensions.json` - New file (VS Code recommendations)
- `README.md` - Added reference to project scope
- `docs/project-scope.md` - **New file** (122 lines of project planning)

**Status**: ✅ **Safe to integrate** - No frontend-specific changes

#### Commit 2: `f7967d5` - "Add provisional left menu, sample pages"
**Files changed:**
- `.env.example` - **DELETED** (but we have a newer Next.js version)
- `CLAUDE.md` - Updated with project scope references
- `docs/docker-troubleshooting.md` - **New file**
- `docs/project-scope.md` - Minor update
- `frontend/*` - **All Vite/React changes** (App.tsx, Layout.tsx, pages, etc.)
- `frontend/tailwind.config.js` - **DELETED** (Vite-specific)
- `image/favicon.ico` - **New file**
- `image/logo.png` - **New file**
- `scripts/docker-cleanup.sh` - **New file**

**Status**: ⚠️ **Partial integration** - Need to cherry-pick non-frontend files

### Rebase Plan

**Approach**: Rebase with selective integration to preserve Next.js migration while extracting valuable non-frontend additions.

#### Step 1: Rebase onto origin/main
```bash
git rebase origin/main
```

#### Step 2: Resolve Conflicts Intelligently

**For commit `5d16f07`**: Accept all changes (no conflicts expected)

**For commit `1b5df29` (Next.js migration)**:
- **Keep all Next.js frontend files**
- **Discard** `.env.example` deletion (keep our Next.js version)
- **Merge** CLAUDE.md changes (combine project scope references with Next.js tech stack)
- **Accept** new non-frontend files:
  - `docs/docker-troubleshooting.md`
  - `docs/project-scope.md` update
  - `image/favicon.ico`
  - `image/logo.png`
  - `scripts/docker-cleanup.sh`

#### Step 3: Update CLAUDE.md
Merge both versions to include:
- Next.js tech stack (current)
- Project scope references (from origin/main)
- Keep simplified commands (current)

#### Step 4: Force Push
```bash
git push origin main --force-with-lease
```

### Expected Result
- ✅ Next.js frontend preserved
- ✅ VS Code extensions recommendations added
- ✅ Project scope documentation integrated
- ✅ Docker troubleshooting guide added
- ✅ Image assets (logo, favicon) added
- ✅ Docker cleanup script added
- ✅ CLAUDE.md updated with both improvements
- ✅ Linear git history on origin/main
