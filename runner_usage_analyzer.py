#!/usr/bin/env python3
import requests
import csv
import os
import json
import logging
import sys
from datetime import datetime, timedelta
from collections import Counter
from typing import List, Dict, Optional, Any


class GitHubAPIError(Exception):
    """Custom exception for GitHub API errors."""
    pass


class RunnerUsageAnalyzer:
    """Analyzes GitHub Actions runner usage across an organization."""
    
    def __init__(self, github_token: str, org_name: str):
        """
        Initialize the analyzer with GitHub credentials.
        
        Args:
            github_token: GitHub personal access token or GITHUB_TOKEN
            org_name: GitHub organization name
        """
        self.github_token = github_token
        self.org_name = org_name
        self.headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitHub-Runner-Analytics/1.0"
        }
        self.setup_logging()
    
    def setup_logging(self) -> None:
        """Configure logging for the application."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)
    
    def make_api_request(self, url: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make a request to the GitHub API with error handling.
        
        Args:
            url: API endpoint URL
            params: Optional query parameters
            
        Returns:
            JSON response data
            
        Raises:
            GitHubAPIError: If the API request fails
        """
        try:
            self.logger.debug(f"Making API request to: {url}")
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            
            # Check rate limit
            remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
            if remaining < 100:
                self.logger.warning(f"Rate limit running low: {remaining} requests remaining")
            
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed for {url}: {e}")
            raise GitHubAPIError(f"GitHub API request failed: {e}")
    
    def get_repositories(self) -> List[Dict[str, Any]]:
        """
        Fetch all repositories in the organization.
        
        Returns:
            List of repository data dictionaries
        """
        self.logger.info(f"Fetching repositories for organization: {self.org_name}")
        repos = []
        page = 1
        
        while True:
            url = f"https://api.github.com/orgs/{self.org_name}/repos"
            params = {"page": page, "per_page": 100, "sort": "updated", "direction": "desc"}
            
            data = self.make_api_request(url, params)
            if not data:
                break
                
            repos.extend(data)
            self.logger.debug(f"Fetched page {page} with {len(data)} repositories")
            page += 1
            
            # Prevent infinite loops
            if page > 100:  # Max 10,000 repos
                self.logger.warning("Reached maximum page limit for repositories")
                break
        
        self.logger.info(f"Found {len(repos)} repositories")
        return repos
    
    def get_workflow_runs(self, repo_name: str, branch: Optional[str] = None, 
                         days_back: int = 30) -> List[Dict[str, Any]]:
        """
        Get workflow runs for a repository within a time range.
        
        Args:
            repo_name: Repository name
            branch: Optional branch filter
            days_back: Number of days to look back for runs
            
        Returns:
            List of workflow run data
        """
        url = f"https://api.github.com/repos/{self.org_name}/{repo_name}/actions/runs"
        params = {"per_page": 100}
        
        if branch:
            params["branch"] = branch
            
        # Filter by date
        since_date = (datetime.now() - timedelta(days=days_back)).isoformat()
        params["created"] = f">={since_date}"
        
        try:
            data = self.make_api_request(url, params)
            workflow_runs = data.get('workflow_runs', [])
            self.logger.debug(f"Found {len(workflow_runs)} workflow runs for {repo_name}")
            return workflow_runs
        except GitHubAPIError as e:
            self.logger.error(f"Failed to fetch workflow runs for {repo_name}: {e}")
            return []
    
    def get_jobs_for_run(self, repo_name: str, run_id: int) -> List[Dict[str, Any]]:
        """
        Get jobs for a specific workflow run.
        
        Args:
            repo_name: Repository name
            run_id: Workflow run ID
            
        Returns:
            List of job data
        """
        url = f"https://api.github.com/repos/{self.org_name}/{repo_name}/actions/runs/{run_id}/jobs"
        
        try:
            data = self.make_api_request(url)
            return data.get('jobs', [])
        except GitHubAPIError as e:
            self.logger.error(f"Failed to fetch jobs for run {run_id} in {repo_name}: {e}")
            return []

    def analyze_runner_usage(self, target_label: Optional[str] = None, 
                            days_back: int = 30,
                            group_by: str = "repo",
                            status_filter: Optional[str] = None,
                            repo_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Analyze runner usage across the organization.
        
        Args:
            target_label: Optional runner label to filter for. If None, captures all runs.
            days_back: Number of days to look back for analysis
            group_by: Field to group results by (repo, label, status, workflow, branch)
            status_filter: Optional status filter (completed, failure, cancelled, etc.)
            repo_filter: Optional repository name filter (supports partial matching)
            
        Returns:
            List of runner usage data
        """
        if target_label:
            self.logger.info(f"Analyzing runner usage for label: {target_label}")
        else:
            self.logger.info("Analyzing all runner usage (no label filter)")
        
        if status_filter:
            self.logger.info(f"Filtering by status: {status_filter}")
        if repo_filter:
            self.logger.info(f"Filtering by repository pattern: {repo_filter}")
        
        results = []
        
        repos = self.get_repositories()
        total_repos = len(repos)
        
        # Apply repository filter if specified
        if repo_filter:
            repos = [repo for repo in repos if repo_filter.lower() in repo['name'].lower()]
            self.logger.info(f"Repository filter applied: {len(repos)} repositories match '{repo_filter}'")
        
        for idx, repo in enumerate(repos, 1):
            repo_name = repo['name']
            default_branch = repo['default_branch']
            
            self.logger.info(f"Processing repository {idx}/{len(repos)}: {repo_name}")
            
            # Get workflow runs
            runs = self.get_workflow_runs(repo_name, default_branch, days_back)
            
            for run in runs:
                workflow_name = run['name']
                run_id = run['id']
                
                # Get jobs for this run
                jobs = self.get_jobs_for_run(repo_name, run_id)
                
                for job in jobs:
                    job_labels = job.get('labels', [])
                    job_status = job.get('status', 'unknown')
                    runner_label = ', '.join(job_labels) if job_labels else 'unknown'
                    
                    # Apply status filter if specified
                    if status_filter and status_filter.lower() != job_status.lower():
                        continue
                    
                    # Filter by target label if specified, otherwise include all jobs
                    if target_label is None or target_label in job_labels:
                        # Enhanced labeling and categorization
                        runner_type = self._categorize_runner(job_labels)
                        cost_category = self._get_cost_category(job_labels)
                        
                        results.append({
                            'Org': self.org_name,
                            'Repo': repo_name,
                            'Branch': default_branch,
                            'Workflow File': run.get('path', ''),
                            'Workflow Name': workflow_name,
                            'Runner Labels': runner_label,
                            'Runner Type': runner_type,
                            'Cost Category': cost_category,
                            'Job Name': job['name'],
                            'Job Status': job_status,
                            'Run Date': job.get('started_at', ''),
                            'Completed Date': job.get('completed_at', ''),
                            'Duration': self._calculate_duration(job),
                            'Run ID': run_id,
                            'Job ID': job.get('id', ''),
                            'Conclusion': job.get('conclusion', 'unknown'),
                            'HTML URL': job.get('html_url', ''),
                            'Repository Size': repo.get('size', 0),
                            'Repository Language': repo.get('language', 'unknown'),
                            'Repository Visibility': repo.get('visibility', 'unknown')
                        })
        
        # Group results if requested
        if group_by != "none":
            results = self._group_results(results, group_by)
        
        if target_label:
            self.logger.info(f"Found {len(results)} jobs using runner label: {target_label}")
        else:
            self.logger.info(f"Found {len(results)} total jobs across all runners")
        
        return results
    
    def _calculate_duration(self, job: Dict[str, Any]) -> str:
        """
        Calculate job duration from start and end times.
        
        Args:
            job: Job data dictionary
            
        Returns:
            Duration string in format "MM:SS" or "unknown"
        """
        try:
            started_at = job.get('started_at')
            completed_at = job.get('completed_at')
            
            if started_at and completed_at:
                start_time = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
                duration = end_time - start_time
                
                total_seconds = int(duration.total_seconds())
                minutes = total_seconds // 60
                seconds = total_seconds % 60
                start_time = self._parse_iso_datetime(started_at)
                end_time = self._parse_iso_datetime(completed_at)
                if start_time and end_time:
                    duration = end_time - start_time
                    
                    total_seconds = int(duration.total_seconds())
                    minutes = total_seconds // 60
                    seconds = total_seconds % 60
                    return f"{minutes:02d}:{seconds:02d}"
        except (ValueError, TypeError) as e:
            self.logger.debug(f"Failed to calculate duration: {e}")
        
        return "unknown"
    
    def _categorize_runner(self, labels: List[str]) -> str:
        """
        Categorize runner type based on labels.
        
        Args:
            labels: List of runner labels
            
        Returns:
            Runner category string
        """
        labels_str = ' '.join(labels).lower()
        
        if 'self-hosted' in labels_str:
            return 'Self-hosted'
        elif any(gh_label in labels_str for gh_label in ['ubuntu-latest', 'windows-latest', 'macos-latest']):
            return 'GitHub-hosted'
        elif 'ubuntu' in labels_str:
            return 'Ubuntu'
        elif 'windows' in labels_str:
            return 'Windows'
        elif 'macos' in labels_str:
            return 'macOS'
        elif 'linux' in labels_str:
            return 'Linux'
        else:
            return 'Unknown'
    
    def _get_cost_category(self, labels: List[str]) -> str:
        """
        Determine cost category based on runner labels.
        
        Args:
            labels: List of runner labels
            
        Returns:
            Cost category string
        """
        labels_str = ' '.join(labels).lower()
        
        if 'self-hosted' in labels_str:
            return 'Self-hosted (Custom Cost)'
        elif any(size in labels_str for size in ['large', 'xl', 'xxl', '4-core', '8-core', '16-core']):
            return 'Large Instance'
        elif any(gh_label in labels_str for gh_label in ['ubuntu-latest', 'windows-latest', 'macos-latest']):
            return 'Standard GitHub-hosted'
        else:
            return 'Standard'
    
    def _group_results(self, results: List[Dict[str, Any]], group_by: str) -> List[Dict[str, Any]]:
        """
        Group results by specified field.
        
        Args:
            results: List of result dictionaries
            group_by: Field to group by
            
        Returns:
            Grouped results with summary statistics
        """
        if not results:
            return results
        
        from collections import defaultdict
        
        grouped = defaultdict(list)
        
        # Group results by the specified field
        for result in results:
            key = result.get(group_by.title(), 'Unknown')
            if group_by == 'label':
                key = result.get('Runner Labels', 'Unknown')
            elif group_by == 'status':
                key = result.get('Job Status', 'Unknown')
            elif group_by == 'workflow':
                key = result.get('Workflow Name', 'Unknown')
            elif group_by == 'branch':
                key = result.get('Branch', 'Unknown')
            elif group_by == 'runner_type':
                key = result.get('Runner Type', 'Unknown')
            elif group_by == 'cost_category':
                key = result.get('Cost Category', 'Unknown')
            
            grouped[key].append(result)
        
        # Create summary for each group
        summary_results = []
        for group_key, group_items in grouped.items():
            # Calculate group statistics
            total_jobs = len(group_items)
            successful_jobs = sum(1 for item in group_items if item.get('Job Status') == 'completed')
            failed_jobs = sum(1 for item in group_items if item.get('Job Status') == 'failure')
            
            # Calculate average duration
            durations = []
            for item in group_items:
                duration_str = item.get('Duration', '00:00')
                if duration_str != 'unknown' and ':' in duration_str:
                    try:
                        minutes, seconds = map(int, duration_str.split(':'))
                        durations.append(minutes * 60 + seconds)
                    except ValueError:
                        pass
            
            avg_duration = "unknown"
            if durations:
                avg_seconds = sum(durations) / len(durations)
                avg_minutes = int(avg_seconds // 60)
                avg_secs = int(avg_seconds % 60)
                avg_duration = f"{avg_minutes:02d}:{avg_secs:02d}"
            
            # Add group summary
            summary_results.append({
                'Group': group_key,
                'Group Type': group_by.title(),
                'Total Jobs': total_jobs,
                'Successful Jobs': successful_jobs,
                'Failed Jobs': failed_jobs,
                'Success Rate': f"{(successful_jobs/total_jobs*100):.1f}%" if total_jobs > 0 else "0%",
                'Average Duration': avg_duration,
                'Sample Repository': group_items[0].get('Repo', 'Unknown') if group_items else 'Unknown'
            })
        
        return summary_results


class ReportGenerator:
    """Handles generation of various report formats."""
    
    def __init__(self, org_name: str):
        """
        Initialize the report generator.
        
        Args:
            org_name: Organization name for report context
        """
        self.org_name = org_name
        self.logger = logging.getLogger(__name__)
    
    def export_to_csv(self, data: List[Dict[str, Any]], 
                     filename: str = "runner_usage_report.csv") -> None:
        """
        Export results to CSV format.
        
        Args:
            data: List of runner usage data
            filename: Output CSV filename
        """
        if not data:
            self.logger.warning("No data to export to CSV")
            return
        
        try:
            keys = data[0].keys()
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=keys)
                writer.writeheader()
                writer.writerows(data)
            
            self.logger.info(f"CSV report exported to {filename}")
        except Exception as e:
            self.logger.error(f"Failed to export CSV: {e}")
            raise

    def generate_html_report(self, data: List[Dict[str, Any]], 
                           filename: str = "runner_usage_report.html") -> None:
        """
        Generate an HTML report with nice styling.
        
        Args:
            data: List of runner usage data
            filename: Output HTML filename
        """
        if not data:
            self.logger.warning("No data to generate HTML report")
            self._generate_empty_html_report(filename)
            return

        try:
            # Calculate statistics
            total_jobs = len(data)
            
            # Check if data is grouped
            is_grouped = len(data) > 0 and 'Group' in data[0]
            
            if is_grouped:
                unique_groups = len(data)
                unique_repos = len(set(item.get('Sample Repository', 'Unknown') for item in data))
                unique_workflows = 0  # Not applicable for grouped data
                
                # Count by group type
                repo_counts = Counter(item.get('Sample Repository', 'Unknown') for item in data)
                status_counts = Counter()  # Will calculate from grouped data
                label_counts = Counter(item.get('Group', 'Unknown') for item in data)
                
                # Calculate total successful/failed from grouped data
                total_successful = sum(item.get('Successful Jobs', 0) for item in data)
                total_failed = sum(item.get('Failed Jobs', 0) for item in data)
                status_counts['completed'] = total_successful
                status_counts['failure'] = total_failed
            else:
                unique_repos = len(set(item['Repo'] for item in data))
                unique_workflows = len(set(item['Workflow File'] for item in data))
                
                # Count jobs by repository and status
                repo_counts = Counter(item['Repo'] for item in data)
                status_counts = Counter(item['Job Status'] for item in data)
                label_counts = Counter(item['Runner Labels'] for item in data)
            
            html_content = self._generate_html_template(
                total_jobs, unique_repos, unique_workflows, 
                repo_counts, status_counts, label_counts, data, is_grouped
            )
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.logger.info(f"HTML report exported to {filename}")
        except Exception as e:
            self.logger.error(f"Failed to generate HTML report: {e}")
            raise
    
    def _generate_empty_html_report(self, filename: str) -> None:
        """Generate HTML report when no data is available."""
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Runner Usage Report - {self.org_name}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            text-align: center;
            padding: 2rem;
            background: #f6f8fa;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            background: white;
            padding: 2rem;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🏃‍♂️ Runner Usage Report</h1>
        <p>Organization: <strong>{self.org_name}</strong></p>
        <p>No runner usage data found for the specified criteria.</p>
        <p><em>Generated on {datetime.now().strftime('%B %d, %Y at %H:%M UTC')}</em></p>
    </div>
</body>
</html>
"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def _generate_html_template(self, total_jobs: int, unique_repos: int, 
                              unique_workflows: int, repo_counts: Counter, 
                              status_counts: Counter, label_counts: Counter, 
                              data: List[Dict], is_grouped: bool = False) -> str:
        """Generate the main HTML template with data."""
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Runner Usage Report - {self.org_name}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif;
            line-height: 1.5;
            color: #24292f;
            background-color: #ffffff;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            border-radius: 8px;
            margin-bottom: 2rem;
            text-align: center;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .stat-card {{
            background: #f6f8fa;
            border: 1px solid #d0d7de;
            border-radius: 6px;
            padding: 1rem;
            text-align: center;
        }}
        .stat-number {{
            font-size: 2rem;
            font-weight: bold;
            color: #0969da;
        }}
        .stat-label {{
            color: #656d76;
            margin-top: 0.5rem;
        }}
        .section {{
            background: white;
            border: 1px solid #d0d7de;
            border-radius: 6px;
            padding: 1.5rem;
            margin-bottom: 2rem;
        }}
        .section h2 {{
            margin-top: 0;
            color: #24292f;
            border-bottom: 1px solid #d0d7de;
            padding-bottom: 0.5rem;
        }}
        .table-container {{
            overflow-x: auto;
            margin-top: 1rem;
            border: 1px solid #d0d7de;
            border-radius: 6px;
            background: white;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            min-width: 800px;
        }}
        th, td {{
            padding: 0.5rem 0.75rem;
            text-align: left;
            border-bottom: 1px solid #d0d7de;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 200px;
        }}
        th {{
            background-color: #f6f8fa;
            font-weight: 600;
            position: sticky;
            top: 0;
            z-index: 10;
            cursor: pointer;
            user-select: none;
        }}
        th:hover {{
            background-color: #e6edf3;
        }}
        th.sortable::after {{
            content: ' ↕️';
            font-size: 0.8em;
            opacity: 0.5;
        }}
        th.sort-asc::after {{
            content: ' ↑';
            opacity: 1;
        }}
        th.sort-desc::after {{
            content: ' ↓';
            opacity: 1;
        }}
        tr:hover {{
            background-color: #f6f8fa;
        }}
        /* Responsive column widths */
        th:nth-child(1), td:nth-child(1) {{ max-width: 150px; }} /* Repository */
        th:nth-child(2), td:nth-child(2) {{ max-width: 200px; }} /* Workflow */
        th:nth-child(3), td:nth-child(3) {{ max-width: 150px; }} /* Job Name */
        th:nth-child(4), td:nth-child(4) {{ max-width: 120px; }} /* Runner Labels */
        th:nth-child(5), td:nth-child(5) {{ max-width: 120px; }} /* Runner Type */
        th:nth-child(6), td:nth-child(6) {{ max-width: 100px; }} /* Status */
        th:nth-child(7), td:nth-child(7) {{ max-width: 80px; }} /* Duration */
        th:nth-child(8), td:nth-child(8) {{ max-width: 140px; }} /* Run Date */
        .badge {{
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.875rem;
            font-weight: 500;
        }}
        .badge-success {{ background-color: #28a745; color: white; }}
        .badge-failure {{ background-color: #dc3545; color: white; }}
        .badge-in-progress {{ background-color: #fd7e14; color: white; }}
        .badge-default {{ background-color: #6c757d; color: white; }}
        .chart-container {{
            margin: 1rem 0;
            padding: 1.5rem;
            background: #f6f8fa;
            border-radius: 8px;
            border: 1px solid #d0d7de;
        }}
        .chart-header {{
            margin-bottom: 1.5rem;
            text-align: center;
        }}
        .chart-header h3 {{
            margin: 0 0 0.5rem 0;
            color: #24292f;
            font-size: 1.1rem;
            font-weight: 600;
        }}
        .chart-description {{
            margin: 0;
            color: #656d76;
            font-size: 0.875rem;
            line-height: 1.4;
        }}
        .bar-chart {{
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }}
        .bar-item {{
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }}
        .bar-label {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            min-height: 1.5rem;
        }}
        .repo-name {{
            font-weight: 600;
            color: #24292f;
            font-size: 0.875rem;
        }}
        .job-count {{
            font-size: 0.75rem;
            color: #656d76;
            font-weight: 500;
        }}
        .bar-container {{
            width: 100%;
            height: 28px;
            background: #e1e4e8;
            border-radius: 14px;
            overflow: hidden;
            position: relative;
        }}
        .bar {{
            background: linear-gradient(90deg, #0969da, #54aeff);
            height: 100%;
            border-radius: 14px;
            display: flex;
            align-items: center;
            justify-content: flex-end;
            color: white;
            font-size: 0.75rem;
            font-weight: 600;
            padding: 0 0.75rem;
            min-width: 40px;
            position: relative;
            transition: all 0.3s ease;
        }}
        .bar:hover {{
            background: linear-gradient(90deg, #0860ca, #4a9eff);
            transform: scaleY(1.1);
        }}
        .bar-value {{
            text-shadow: 0 1px 2px rgba(0,0,0,0.3);
        }}
        .chart-footer {{
            margin-top: 1.5rem;
            padding-top: 1rem;
            border-top: 1px solid #d0d7de;
            text-align: center;
        }}
        .text-muted {{
            color: #656d76;
            font-style: italic;
        }}
        
        /* Responsive design for charts */
        @media (max-width: 768px) {{
            .chart-container {{
                padding: 1rem;
            }}
            .bar-label {{
                flex-direction: column;
                align-items: flex-start;
                gap: 0.25rem;
            }}
            .repo-name {{
                font-size: 0.8rem;
            }}
            .job-count {{
                font-size: 0.7rem;
            }}
            .bar-container {{
                height: 24px;
            }}
            .bar {{
                padding: 0 0.5rem;
                font-size: 0.7rem;
            }}
        }}
        
        /* Animation for chart loading */
        @keyframes slideIn {{
            from {{
                opacity: 0;
                transform: translateX(-20px);
            }}
            to {{
                opacity: 1;
                transform: translateX(0);
            }}
        }}
        
        .bar-item {{
            animation: slideIn 0.6s ease-out;
        }}
        
        .bar-item:nth-child(1) {{ animation-delay: 0.1s; }}
        .bar-item:nth-child(2) {{ animation-delay: 0.2s; }}
        .bar-item:nth-child(3) {{ animation-delay: 0.3s; }}
        .bar-item:nth-child(4) {{ animation-delay: 0.4s; }}
        .bar-item:nth-child(5) {{ animation-delay: 0.5s; }}
        .bar-item:nth-child(6) {{ animation-delay: 0.6s; }}
        .bar-item:nth-child(7) {{ animation-delay: 0.7s; }}
        .bar-item:nth-child(8) {{ animation-delay: 0.8s; }}
        .bar-item:nth-child(9) {{ animation-delay: 0.9s; }}
        .bar-item:nth-child(10) {{ animation-delay: 1.0s; }}
        .timestamp {{
            color: #656d76;
            font-size: 0.875rem;
            text-align: center;
            margin-top: 2rem;
            padding-top: 1rem;
            border-top: 1px solid #d0d7de;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏃‍♂️ Runner Usage Analytics</h1>
            <p>Organization: <strong>{self.org_name}</strong></p>
            <p>Report generated on {datetime.now().strftime('%B %d, %Y at %H:%M UTC')}</p>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{total_jobs}</div>
                <div class="stat-label">Total Jobs</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{unique_repos}</div>
                <div class="stat-label">Repositories</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{unique_workflows}</div>
                <div class="stat-label">Workflow Files</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{status_counts.get('completed', 0)}</div>
                <div class="stat-label">Completed Jobs</div>
            </div>
        </div>

        <div class="section">
            <h2>📊 Jobs by Repository</h2>
            <div class="chart-container">
                <div class="chart-header">
                    <h3>Distribution of Jobs Across Repositories</h3>
                    <p class="chart-description">Shows the total number of workflow jobs executed per repository, with repositories ordered by activity.</p>
                </div>
                <div class="bar-chart">
{self._generate_repo_chart_html(repo_counts)}
                </div>
                <div class="chart-footer">
                    <small class="text-muted">
                        Showing top 10 repositories by job count. Total: {total_jobs} jobs across {unique_repos} repositories.
                    </small>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>🏃‍♂️ Jobs by Runner Labels</h2>
            <div class="chart-container">
                <div class="chart-header">
                    <h3>Runner Type Distribution</h3>
                    <p class="chart-description">Shows the distribution of jobs across different runner types and operating systems.</p>
                </div>
                <div class="bar-chart">
{self._generate_labels_chart_html(label_counts)}
                </div>
                <div class="chart-footer">
                    <small class="text-muted">
                        Runner labels indicate the target environment for workflow execution. Total: {total_jobs} jobs.
                    </small>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>📋 {'Group Summary' if is_grouped else 'Detailed Job Reports'}</h2>
            <div class="table-container">
                <table id="jobsTable">
                    <thead>
                        <tr>
{self._generate_table_header_html(is_grouped)}
                        </tr>
                    </thead>
                    <tbody>
{self._generate_jobs_table_html(data, is_grouped)}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="timestamp">
            Generated by Runner Usage Analyzer | Data from GitHub Actions API
        </div>
    </div>

    <script>
        // Table sorting functionality
        function sortTable(table, column, direction) {{
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            
            const sortedRows = rows.sort((a, b) => {{
                const aText = a.cells[column].textContent.trim();
                const bText = b.cells[column].textContent.trim();
                
                // Handle numeric sorting for duration column
                if (column === 6 || (column === 2 && aText.match(/^\\d+$/))) {{ // Duration column or numeric data
                    const aMinutes = parseDuration(aText);
                    const bMinutes = parseDuration(bText);
                    return direction === 'asc' ? aMinutes - bMinutes : bMinutes - aMinutes;
                }}
                
                // Handle date sorting
                if (column === DURATION_COLUMN_INDEX || (column === RUN_ID_COLUMN_INDEX && aText.match(/^\\d+$/))) {{ // Duration column or numeric data
                    const aMinutes = parseDuration(aText);
                    const bMinutes = parseDuration(bText);
                    return direction === 'asc' ? aMinutes - bMinutes : bMinutes - aMinutes;
                }}
                
                // Handle date sorting
                if (column === RUN_DATE_COLUMN_INDEX || aText.match(/^\\d{{4}}-\\d{{2}}-\\d{{2}}/)) {{ // Run Date column or date format
                    const aDate = new Date(aText);
                    const bDate = new Date(bText);
                    return direction === 'asc' ? aDate - bDate : bDate - aDate;
                }}
                
                // Default string sorting
                return direction === 'asc' 
                    ? aText.localeCompare(bText)
                    : bText.localeCompare(aText);
            }});
            
            // Clear tbody and append sorted rows
            tbody.innerHTML = '';
            sortedRows.forEach(row => tbody.appendChild(row));
        }}
        
        function parseDuration(duration) {{
            // Parse duration format like "02:38", "00:00", "-1:59", or plain numbers
            if (duration.match(/^\\d+$/)) return parseInt(duration);
            
            const parts = duration.split(':');
            if (parts.length !== 2) return 0;
            
            const hours = parseInt(parts[0]) || 0;
            const minutes = parseInt(parts[1]) || 0;
            return hours * 60 + minutes;
        }}
        
        // Initialize table sorting
        document.addEventListener('DOMContentLoaded', function() {{
            const table = document.getElementById('jobsTable');
            if (!table) return;
            
            const headers = table.querySelectorAll('th');
            
            headers.forEach((header, index) => {{
                header.classList.add('sortable');
                header.dataset.column = index;
                
                header.addEventListener('click', function() {{
                    const column = parseInt(this.dataset.column);
                    const currentSort = this.classList.contains('sort-asc') ? 'asc' : 
                                      this.classList.contains('sort-desc') ? 'desc' : null;
                    
                    // Remove sort classes from all headers
                    headers.forEach(h => h.classList.remove('sort-asc', 'sort-desc'));
                    
                    // Determine new sort direction
                    let newDirection;
                    if (currentSort === 'asc') {{
                        newDirection = 'desc';
                        this.classList.add('sort-desc');
                    }} else {{
                        newDirection = 'asc';
                        this.classList.add('sort-asc');
                    }}
                    
                    sortTable(table, column, newDirection);
                }});
            }});
        }});
    </script>
</body>
</html>
"""
    
    def _generate_repo_chart_html(self, repo_counts: Counter) -> str:
        """Generate HTML for repository usage chart."""
        html = ""
        max_count = max(repo_counts.values()) if repo_counts else 1
        
        for repo, count in repo_counts.most_common(10):
            width_percent = (count / max_count) * 100
            job_text = "job" if count == 1 else "jobs"
            html += f"""
                    <div class="bar-item">
                        <div class="bar-label">
                            <span class="repo-name">{repo}</span>
                            <span class="job-count">{count} {job_text}</span>
                        </div>
                        <div class="bar-container">
                            <div class="bar" style="width: {width_percent}%">
                                <span class="bar-value">{count}</span>
                            </div>
                        </div>
                    </div>"""
        
        return html
    
    def _generate_labels_chart_html(self, label_counts: Counter) -> str:
        """Generate HTML for runner labels usage chart."""
        html = ""
        max_count = max(label_counts.values()) if label_counts else 1
        
        for labels, count in label_counts.most_common(10):
            width_percent = (count / max_count) * 100
            # Truncate long label strings for display
            display_labels = labels if len(labels) <= 30 else labels[:27] + "..."
            job_text = "job" if count == 1 else "jobs"
            html += f"""
                    <div class="bar-item">
                        <div class="bar-label">
                            <span class="repo-name">{display_labels}</span>
                            <span class="job-count">{count} {job_text}</span>
                        </div>
                        <div class="bar-container">
                            <div class="bar" style="width: {width_percent}%">
                                <span class="bar-value">{count}</span>
                            </div>
                        </div>
                    </div>"""
        
        return html
    
    
    def _generate_table_header_html(self, is_grouped: bool) -> str:
        """Generate HTML for table header based on data type."""
        if is_grouped:
            return """
                            <th>Group</th>
                            <th>Group Type</th>
                            <th>Total Jobs</th>
                            <th>Successful</th>
                            <th>Failed</th>
                            <th>Success Rate</th>
                            <th>Avg Duration</th>"""
        else:
            return """
                            <th>Repository</th>
                            <th>Workflow</th>
                            <th>Job Name</th>
                            <th>Runner Labels</th>
                            <th>Runner Type</th>
                            <th>Status</th>
                            <th>Duration</th>
                            <th>Run Date</th>"""
    
    def _generate_jobs_table_html(self, data: List[Dict], is_grouped: bool = False) -> str:
        """Generate HTML for jobs table."""
        html = ""
        
        if is_grouped:
            # Generate grouped data table
            for item in sorted(data, key=lambda x: x.get('Total Jobs', 0), reverse=True):
                success_rate = item.get('Success Rate', '0%')
                rate_class = 'badge-success' if float(success_rate.rstrip('%')) > 80 else 'badge-failure' if float(success_rate.rstrip('%')) < 50 else 'badge-in-progress'
                
                html += f"""
                        <tr>
                            <td><strong>{item.get('Group', 'Unknown')}</strong></td>
                            <td>{item.get('Group Type', 'Unknown')}</td>
                            <td>{item.get('Total Jobs', 0)}</td>
                            <td>{item.get('Successful Jobs', 0)}</td>
                            <td>{item.get('Failed Jobs', 0)}</td>
                            <td><span class="badge {rate_class}">{success_rate}</span></td>
                            <td>{item.get('Average Duration', 'unknown')}</td>
                        </tr>"""
        else:
            # Generate detailed job data table
            sorted_data = sorted(data, key=lambda x: x.get('Run Date', ''), reverse=True)
            
            for item in sorted_data:
                status_class = self._get_status_class(item.get('Job Status', 'unknown'))
                runner_type = item.get('Runner Type', 'Unknown')
                cost_category = item.get('Cost Category', 'Standard')
                
                html += f"""
                        <tr>
                            <td><strong>{item.get('Repo', 'Unknown')}</strong></td>
                            <td>{item.get('Workflow Name', 'Unknown')}</td>
                            <td>{item.get('Job Name', 'Unknown')}</td>
                            <td><span class="badge badge-default">{item.get('Runner Labels', 'unknown')}</span></td>
                            <td><span class="badge badge-default" title="{cost_category}">{runner_type}</span></td>
                            <td><span class="badge {status_class}">{item.get('Job Status', 'unknown')}</span></td>
                            <td>{item.get('Duration', 'unknown')}</td>
                            <td>{item.get('Run Date', 'unknown')}</td>
                        </tr>"""
        
        return html
    
    def _get_status_class(self, status: str) -> str:
        """Get CSS class for job status badge."""
        status_map = {
            'completed': 'badge-success',
            'success': 'badge-success',
            'failure': 'badge-failure',
            'cancelled': 'badge-failure',
            'in_progress': 'badge-in-progress',
            'queued': 'badge-in-progress'
        }
        return status_map.get(status.lower(), 'badge-default')

    def generate_github_summary(self, data: List[Dict[str, Any]]) -> str:
        """
        Generate GitHub Actions step summary.
        
        Args:
            data: List of runner usage data
            
        Returns:
            Summary markdown string
        """
        if not data:
            self.logger.warning("No data for GitHub summary")
            summary = "# 🏃‍♂️ Runner Usage Report\n\n**No runner usage data found.**\n"
        else:
            total_jobs = len(data)
            unique_repos = len(set(item['Repo'] for item in data))
            unique_workflows = len(set(item['Workflow File'] for item in data))
            
            repo_counts = Counter(item['Repo'] for item in data)
            status_counts = Counter(item['Job Status'] for item in data)
            label_counts = Counter(item['Runner Labels'] for item in data)
            
            summary = f"""# 🏃‍♂️ Runner Usage Report

## 📊 Summary Statistics
- **Total Jobs**: {total_jobs}
- **Repositories Analyzed**: {unique_repos}
- **Unique Workflow Files**: {unique_workflows}
- **Organization**: {self.org_name}
- **Successful Jobs**: {status_counts.get('completed', 0)}
- **Failed Jobs**: {status_counts.get('failure', 0)}

## 🔝 Top Repositories by Runner Usage
"""
            
            for repo, count in repo_counts.most_common(5):
                summary += f"- **{repo}**: {count} jobs\n"
            
            summary += f"""
## 🏃‍♂️ Top Runner Labels
"""
            
            for labels, count in label_counts.most_common(5):
                summary += f"- **{labels}**: {count} jobs\n"
            
            summary += f"""
## 📋 Recent Jobs
| Repository | Workflow | Job Name | Runner Labels | Status | Date |
|------------|----------|----------|---------------|--------|------|
"""
            
            # Show last 10 jobs
            sorted_data = sorted(data, key=lambda x: x['Run Date'], reverse=True)[:10]
            for item in sorted_data:
                summary += f"| {item['Repo']} | {item['Workflow Name']} | {item['Job Name']} | {item['Runner Labels']} | {item['Job Status']} | {item['Run Date']} |\n"
        
        summary += f"\n*Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}*"
        
        # Write to GitHub Actions summary
        github_step_summary = os.environ.get('GITHUB_STEP_SUMMARY')
        if github_step_summary:
            try:
                with open(github_step_summary, 'w', encoding='utf-8') as f:
                    f.write(summary)
                self.logger.info("GitHub Actions summary updated")
            except Exception as e:
                self.logger.error(f"Failed to write GitHub Actions summary: {e}")
        else:
            self.logger.debug("GitHub Actions summary not available (not running in GitHub Actions)")
        
        return summary


def main():
    """Main function to run the runner usage analysis."""
    try:
        # Get configuration from environment variables
        github_token = os.environ.get('GITHUB_TOKEN')
        org_name = os.environ.get('ORG_NAME')
        target_label = os.environ.get('TARGET_RUNNER_LABEL')  # Now optional
        days_back = int(os.environ.get('DAYS_BACK', '30'))
        group_by = os.environ.get('GROUP_BY', 'none').lower()
        status_filter = os.environ.get('STATUS_FILTER')
        repo_filter = os.environ.get('REPO_FILTER')
        
        if not github_token:
            raise ValueError("GITHUB_TOKEN environment variable is required")
        if not org_name:
            raise ValueError("ORG_NAME environment variable is required")
        
        # Initialize analyzer and report generator
        analyzer = RunnerUsageAnalyzer(github_token, org_name)
        report_generator = ReportGenerator(org_name)
        
        # Analyze runner usage
        print("🔍 Analyzing runner usage...")
        usage_data = analyzer.analyze_runner_usage(target_label, days_back, group_by, status_filter, repo_filter)
        
        # Generate reports
        print("📊 Generating reports...")
        report_generator.export_to_csv(usage_data)
        report_generator.generate_html_report(usage_data)
        report_generator.generate_github_summary(usage_data)
        
        print("✅ Analysis complete!")
        
        if usage_data:
            if target_label:
                print(f"📈 Found {len(usage_data)} jobs using runner label: {target_label}")
            else:
                print(f"📈 Found {len(usage_data)} total jobs across all runners")
        else:
            print("⚠️  No jobs found matching the specified criteria")
            
    except Exception as e:
        logging.error(f"❌ Analysis failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()