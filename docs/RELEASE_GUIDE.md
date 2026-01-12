# GitHub Release Guide

Step-by-step instructions for creating and managing releases for FragAudit.

---

## Creating a New Release

### Step 1: Ensure Code is Ready

```bash
# Pull latest changes
git pull origin main

# Run tests locally
python -m pytest tests/ -v

# Verify all tests pass before releasing
```

### Step 2: Update Version References

Update version in these files:
- `README.md` — Version badge
- `CHANGELOG.md` — Add new version section at top

### Step 3: Commit Version Bump

```bash
git add README.md CHANGELOG.md
git commit -m "chore: bump version to vX.Y.Z"
git push origin main
```

### Step 4: Create Git Tag

```bash
# Create annotated tag
git tag -a vX.Y.Z -m "Release vX.Y.Z - Brief description"

# Push tag to GitHub
git push origin vX.Y.Z
```

### Step 5: Create GitHub Release

1. Go to: https://github.com/Pl4yer-ONE/FragAudit/releases/new

2. **Choose a tag**: Select the tag you just pushed (e.g., `v3.0.0`)

3. **Release title**: Use format:
   ```
   vX.Y.Z – Feature Name
   ```
   Example: `v3.0.0 – Demo Player Edition`

4. **Description**: Copy from CHANGELOG.md for this version. Format:
   ```markdown
   ## What's New
   
   ### Added
   - Feature 1
   - Feature 2
   
   ### Changed
   - Change 1
   
   ### Fixed
   - Fix 1
   
   ## Full Changelog
   See [CHANGELOG.md](CHANGELOG.md) for complete history.
   ```

5. **Attachments** (optional but recommended):
   - Demo GIF showing the player in action
   - Screenshot of analysis output
   - Sample report JSON

6. **Pre-release checkbox**: 
   - ✅ Check if this is alpha/beta
   - Leave unchecked for stable releases

7. Click **"Publish release"**

---

## Release Naming Convention

| Version | Meaning |
|---------|---------|
| `vX.0.0` | Major release (breaking changes, major features) |
| `vX.Y.0` | Minor release (new features, backward compatible) |
| `vX.Y.Z` | Patch release (bug fixes only) |
| `vX.Y.Z-alpha` | Pre-release alpha |
| `vX.Y.Z-beta` | Pre-release beta |
| `vX.Y.Z-rc1` | Release candidate |

---

## Deleting a Tag (If Needed)

```bash
# Delete local tag
git tag -d vX.Y.Z

# Delete remote tag
git push origin --delete vX.Y.Z
```

---

## Viewing Release History

```bash
# List all tags
git tag -l

# Show tag details
git show vX.Y.Z

# View on GitHub
# https://github.com/Pl4yer-ONE/FragAudit/releases
```

---

## Automating Releases (Future)

Consider adding `.github/workflows/release.yml` for automated releases:

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          generate_release_notes: true
```

This automatically creates a GitHub release when you push a tag.

---

## Current Tags

| Tag | Description |
|-----|-------------|
| `v3.0.0` | Demo Player Edition |
| `v3.0.1` | Bug fixes |
| `v3.0.1-license` | License lockdown |

---

## Checklist Before Release

- [ ] All tests pass locally
- [ ] CI pipeline is green
- [ ] CHANGELOG.md updated
- [ ] Version badges updated
- [ ] No uncommitted changes
- [ ] Tag created and pushed
- [ ] GitHub release published
