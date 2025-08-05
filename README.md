# 🏃‍♂️ GitHub Actions Runner Analytics

A comprehensive tool for analyzing GitHub Actions runner usage across your organization. Track, visualize, and optimize your CI/CD infrastructure with detailed insights into runner performance, costs, and utilization patterns.

## ✨ Features

### 📊 **Comprehensive Analytics**
- **Complete Runner Visibility**: Analyze all workflow runs or filter by specific runner labels
- **Advanced Filtering**: Filter by repository, status, runner type, and date ranges
- **Intelligent Grouping**: Group results by repository, runner type, cost category, status, and more
- **Cost Analysis**: Categorize runners by cost implications (Standard, Large Instance, Self-hosted)

### 📈 **Rich Reporting**
- **Interactive HTML Dashboard**: Beautiful, responsive reports with charts and statistics
- **CSV Export**: Detailed data export for further analysis
- **GitHub Actions Summary**: Automatic summary in workflow runs
- **GitHub Pages Integration**: Auto-deploy reports to a public dashboard

### 🔍 **Smart Categorization**
- **Runner Type Classification**: GitHub-hosted, Self-hosted, Platform-specific
- **Cost Categories**: Standard, Large Instance, Custom Cost
- **Success Rate Analysis**: Track job success/failure rates across different runners
- **Duration Tracking**: Monitor job execution times and performance

### 🎯 **Flexible Configuration**
- **Environment Variables**: Easy configuration via environment variables
- **Workflow Inputs**: Interactive GitHub Actions workflow with dropdown filters
- **Multiple Grouping Options**: Analyze data from different perspectives

## 🚀 Quick Start

### 1. Set up GitHub Secrets

Go to your repository **Settings** → **Secrets and variables** → **Actions** and add:

- `GH_TOKEN`: GitHub Personal Access Token with required permissions
- `ORG_NAME`: Your GitHub organization name

### 2. Run the Analysis

#### **Via GitHub Actions (Recommended)**
1. Go to the **Actions** tab in your repository
2. Select "Runner Usage Monitor" workflow
3. Click "Run workflow"
4. Configure filters using the dropdown options:
   - Runner label filter
   - Date range (days back)
   - Grouping options
   - Status filter
   - Repository filter

#### **Via Command Line**
```bash
# Install dependencies
pip install -r requirements.txt

# Basic analysis (all runners)
GITHUB_TOKEN=your_token ORG_NAME=your_org python runner_usage_analyzer.py

# Advanced filtering
TARGET_RUNNER_LABEL="self-hosted" \
STATUS_FILTER="completed" \
GROUP_BY="runner_type" \
DAYS_BACK="7" \
python runner_usage_analyzer.py
```

### 3. View Results

- **GitHub Actions Summary**: Check the workflow run summary for key metrics
- **Download Reports**: Get CSV and HTML reports from workflow artifacts
- **GitHub Pages**: Access the interactive dashboard via your repository's GitHub Pages URL

## 📋 Configuration Options

### Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `GITHUB_TOKEN` | ✅ | GitHub token with repo and org permissions | `ghp_xxxx` |
| `ORG_NAME` | ✅ | GitHub organization name | `microsoft` |
| `TARGET_RUNNER_LABEL` | ❌ | Filter by specific runner label | `self-hosted` |
| `DAYS_BACK` | ❌ | Number of days to analyze (default: 30) | `7` |
| `STATUS_FILTER` | ❌ | Filter by job status | `completed` |
| `REPO_FILTER` | ❌ | Filter by repository name pattern | `frontend` |
| `GROUP_BY` | ❌ | Group results by field | `runner_type` |

### Grouping Options

- **none**: Individual jobs (detailed view)
- **repo**: Group by repository
- **label**: Group by runner labels
- **status**: Group by job status
- **workflow**: Group by workflow name
- **branch**: Group by branch
- **runner_type**: Group by runner type
- **cost_category**: Group by cost implications

## 📊 Report Insights

### **HTML Dashboard Features**
- 📈 **Summary Statistics**: Total jobs, repositories, success rates
- 📊 **Usage Charts**: Visual distribution of runners and repositories
- 📋 **Detailed Tables**: Sortable data with status indicators
- 🏷️ **Smart Labels**: Color-coded badges for status and runner types
- 📱 **Responsive Design**: Works on desktop and mobile

### **Data Fields**
- Repository and workflow information
- Runner labels and categorization
- Job status and duration
- Cost category analysis
- Success/failure rates
- Repository metadata (language, size, visibility)

### **Cost Analysis**
- **Standard GitHub-hosted**: Default free/paid GitHub runners
- **Large Instance**: Premium GitHub runners (4-core, 8-core, etc.)
- **Self-hosted (Custom Cost)**: Your organization's runners

## 🔧 Setup & Installation

### Prerequisites
- Python 3.7+
- GitHub organization with Actions enabled
- GitHub token with appropriate permissions

### Required GitHub Token Permissions
- `repo`: Access to repositories
- `actions:read`: Read workflow runs and jobs
- `read:org`: List organization repositories

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/actions-runner-analytics.git
   cd actions-runner-analytics
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure secrets** (for GitHub Actions)
   - Add `GH_TOKEN` and `ORG_NAME` to repository secrets

4. **Enable GitHub Pages** (optional)
   - Go to Settings → Pages
   - Source: "GitHub Actions"

## 📊 Usage Examples

### **Basic Analysis**
```bash
# Analyze all runners for the last 30 days
python runner_usage_analyzer.py
```

### **Filter by Runner Type**
```bash
# Only self-hosted runners
TARGET_RUNNER_LABEL="self-hosted" python runner_usage_analyzer.py

# Only GitHub-hosted Ubuntu runners
TARGET_RUNNER_LABEL="ubuntu-latest" python runner_usage_analyzer.py
```

### **Group Analysis**
```bash
# Group by repository to see which repos use runners most
GROUP_BY="repo" python runner_usage_analyzer.py

# Group by runner type for cost analysis
GROUP_BY="runner_type" python runner_usage_analyzer.py

# Group by cost category for budget planning
GROUP_BY="cost_category" python runner_usage_analyzer.py
```

### **Advanced Filtering**
```bash
# Failed jobs in frontend repositories, last 7 days
STATUS_FILTER="failure" \
REPO_FILTER="frontend" \
DAYS_BACK="7" \
python runner_usage_analyzer.py

# Self-hosted runner performance analysis
TARGET_RUNNER_LABEL="self-hosted" \
GROUP_BY="status" \
DAYS_BACK="14" \
python runner_usage_analyzer.py
```

## 🔄 Automation

The tool includes a GitHub Actions workflow that:
- ⏰ **Runs daily** at midnight (configurable)
- 🎯 **Manual triggers** with custom parameters
- 📊 **Generates reports** automatically
- 🌐 **Deploys to GitHub Pages** for easy access
- 📁 **Uploads artifacts** for download

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- 📖 **Documentation**: Check the [config.md](config.md) file for detailed configuration options
- 🐛 **Issues**: Report bugs or request features via GitHub Issues
- 💡 **Discussions**: Join the conversation in GitHub Discussions

## 🎯 Use Cases

- **Cost Optimization**: Identify expensive runner usage patterns
- **Performance Monitoring**: Track job success rates and duration
- **Resource Planning**: Understand runner demand across repositories
- **Compliance**: Monitor self-hosted runner usage
- **Optimization**: Find opportunities to improve CI/CD efficiency
