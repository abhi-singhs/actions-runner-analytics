# Runner Analytics Configuration

## Environment Variables

### Required
- `GITHUB_TOKEN`: GitHub personal access token or GITHUB_TOKEN
- `ORG_NAME`: GitHub organization name

### Optional Filtering & Grouping
- `TARGET_RUNNER_LABEL`: Filter by specific runner label (e.g., "self-hosted", "ubuntu-latest")
- `DAYS_BACK`: Number of days to analyze (default: 30)
- `STATUS_FILTER`: Filter by job status (completed, failure, cancelled, in_progress)
- `REPO_FILTER`: Filter by repository name pattern (supports partial matching)
- `GROUP_BY`: Group results by field (none, repo, label, status, workflow, branch, runner_type, cost_category)

## Usage Examples

### Analyze All Runners (Default)
```bash
GITHUB_TOKEN=your_token ORG_NAME=your_org python runner_usage_analyzer.py
```

### Filter by Specific Runner Label
```bash
TARGET_RUNNER_LABEL="self-hosted" python runner_usage_analyzer.py
```

### Filter by Status and Group by Repository
```bash
STATUS_FILTER="completed" GROUP_BY="repo" python runner_usage_analyzer.py
```

### Filter by Repository Pattern
```bash
REPO_FILTER="frontend" python runner_usage_analyzer.py
```

### Advanced Filtering
```bash
TARGET_RUNNER_LABEL="ubuntu-latest" \
STATUS_FILTER="completed" \
REPO_FILTER="api" \
GROUP_BY="runner_type" \
DAYS_BACK="7" \
python runner_usage_analyzer.py
```

## Grouping Options

- **none**: No grouping, show individual jobs
- **repo**: Group by repository
- **label**: Group by runner labels
- **status**: Group by job status
- **workflow**: Group by workflow name
- **branch**: Group by branch
- **runner_type**: Group by runner type (GitHub-hosted, Self-hosted, etc.)
- **cost_category**: Group by cost category

## Runner Categories

### Runner Types
- **GitHub-hosted**: ubuntu-latest, windows-latest, macos-latest
- **Self-hosted**: Custom runners
- **Ubuntu/Windows/macOS**: Platform-specific runners

### Cost Categories
- **Standard GitHub-hosted**: Default GitHub runners
- **Large Instance**: Larger GitHub runners (4-core, 8-core, etc.)
- **Self-hosted (Custom Cost)**: Organization-managed runners

## Report Features

### Enhanced Data Fields
- Runner Labels (all labels for each job)
- Runner Type (categorized)
- Cost Category
- Job Conclusion
- Repository metadata (size, language, visibility)
- Enhanced duration tracking

### Visual Reports
- Interactive HTML dashboard
- Repository usage charts
- Runner label distribution
- Status breakdown with success rates
- Group summaries with statistics

### Export Formats
- CSV with all enhanced fields
- HTML interactive dashboard
- GitHub Actions summary with key metrics
