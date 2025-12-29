#!/bin/bash
# Cleanup script to untrack sensitive files and suggest history rewrite steps.
# Run these commands from repo root. Review before running.

# 1) Add/update .gitignore (already done). Commit the change first:
# git add .gitignore && git commit -m "chore: ignore sensitive local files"

# 2) Untrack sensitive files that may already be in the repo (examples):
# Replace or add any path you want to keep only locally
SENSITIVE=(
  "config/.env"
  "config/mt5_credentials.enc"
  "config/mt5.yaml"
  "archive/telegram_bot/config.json"
  ".env"
  "logs/"
  "data/"
)

for f in "${SENSITIVE[@]}"; do
  if git ls-files --error-unmatch "$f" > /dev/null 2>&1; then
    echo "Removing from index (will remain locally): $f"
    git rm --cached -r "$f"
  else
    echo "Not tracked (ok): $f"
  fi
done

# 3) Commit the removals
# git commit -m "chore: remove sensitive files from repo index (keep local)"

# 4) OPTIONAL: To purge these files from git history (more intrusive):
# Use BFG or git-filter-repo. Example with git-filter-repo (recommended):
# pip install git-filter-repo
# git filter-repo --invert-paths --paths config/.env --paths config/mt5_credentials.enc --paths .env --force
# After history rewrite you must force-push: git push --force

# 5) If you prefer BFG (easier):
# 1) install BFG jar
# 2) java -jar bfg.jar --delete-files config/.env --delete-files config/mt5_credentials.enc
# 3) git reflog expire --expire=now --all && git gc --prune=now --aggressive
# 4) git push --force

# NOTE: History rewrite will affect all collaborators. Coordinate before doing it.

echo "Cleanup script finished. Review and run the commented git commands manually."
