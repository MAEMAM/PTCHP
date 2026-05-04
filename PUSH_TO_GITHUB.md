# Pushing to GitHub

The repo is already initialized with `main` as the default branch and one clean commit. You just need to create the GitHub repo and push.

## One-time: install GitHub CLI (recommended)

```bash
# macOS
brew install gh

# Ubuntu/Debian
sudo apt install gh

# Windows
winget install --id GitHub.cli
```

## Path A — GitHub CLI (one command)

From inside the unzipped `PTCHP_Bundle/` folder:

```bash
gh auth login                              # first time only
gh repo create PTCHP --public --source=. --push
```

That's it. Replace `--public` with `--private` if you want a private repo.

## Path B — Manual (if you don't want gh)

1. Create the repo on GitHub.com — leave it empty (no README, no .gitignore, no license).

2. From inside `PTCHP_Bundle/`:

```bash
git remote add origin git@github.com:YOUR_USERNAME/PTCHP.git
git push -u origin main
```

If you use HTTPS instead of SSH:

```bash
git remote add origin https://github.com/YOUR_USERNAME/PTCHP.git
git push -u origin main
```

## Verifying

```bash
git remote -v       # should show origin
git log --oneline   # should show the initial commit
git status          # should be clean
```

## What's already done for you

- `git init -b main` — done
- `.gitignore` — written (ignores `.env`, source xlsx, build artifacts, caches)
- `LICENSE` — MIT (change to whatever your org requires)
- `git add .` + initial commit — done

You can verify with `git log --oneline` before pushing.

## A note about the source data

The `.gitignore` excludes `*.xlsx` deliberately — the four CRM exports contain real case data and shouldn't go into a public repo. The pre-computed `dashboard_data.json` (which is what the dashboard actually reads) is also excluded by default; if you want the dashboard to render with real numbers when someone clones the repo, generate a privacy-safe / aggregated version of that file and commit it explicitly:

```bash
git add -f dashboard_data.json
git commit -m "Add aggregated dashboard data"
```

Note that the dashboard already has the data inlined into `PTCHP_Dashboard.html`, so this is only needed if you want a rebuildable pipeline.
