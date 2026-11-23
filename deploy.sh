#!/bin/sh
# ---------------------------------------------------------------------------
# deploy.sh — publish the current main branch to the Hugging Face Space
# ---------------------------------------------------------------------------
#
# Hugging Face rejects binary files that are not in its Xet/LFS storage, and
# the project report (13 MB of PNGs, a PDF and a DOCX) is both binary and
# irrelevant to running the app. Those files stay on GitHub.
#
# This script therefore builds a single-commit, report-free history on an
# orphan branch and force-pushes it to the Space. Force is correct here: the
# Space is a deployment target, not a source of truth, and this script is the
# only thing that writes to it. GitHub keeps the full history.
#
# Usage:  ./deploy.sh
# ---------------------------------------------------------------------------

set -e

REPO="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO"

EXCLUDE="report docs"
BRANCH="space-deploy"

if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "error: you have uncommitted changes. Commit them first." >&2
    exit 1
fi

START="$(git rev-parse --abbrev-ref HEAD)"
SHA="$(git rev-parse --short HEAD)"

cleanup() {
    git checkout -q -f "$START" 2>/dev/null || true
    git branch -D "$BRANCH" >/dev/null 2>&1 || true
}
trap cleanup EXIT

git branch -D "$BRANCH" >/dev/null 2>&1 || true
git checkout -q --orphan "$BRANCH"

# Drop the report from the index only; the files stay on disk untouched.
for path in $EXCLUDE; do
    [ -e "$path" ] && git rm -r -q --cached "$path"
done

git commit -q -m "Deploy $SHA"
echo "Pushing $(git rev-list --count HEAD) commit to the Space..."
git push space "$BRANCH":main --force

echo
echo "Pushed. Build logs: https://huggingface.co/spaces/savreet28/career-engine"
