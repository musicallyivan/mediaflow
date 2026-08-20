# Security Policy

## Supported Versions

Only the latest public release receives security fixes. Older versions may stop
receiving fixes once a new version is published.

| Version | Supported |
| --- | --- |
| 1.6.x | ✅ |
| < 1.6 | ✖️ |

## Reporting a Vulnerability

If you find a security issue in Media Flow, please do not publish it publicly
until it has been reviewed.

Report the vulnerability by opening a private security advisory in this GitHub
repository:

1. Go to the repository on GitHub.
2. Open the **Security** tab.
3. Choose **Report a vulnerability**.
4. Include the affected version, your operating system, clear reproduction
   steps, expected behavior, actual behavior, and any relevant logs or files.

If private advisories are not available, open a regular issue with only a brief
description and avoid sharing exploit details publicly.

## Response Expectations

- New reports are reviewed as soon as reasonably possible.
- Valid vulnerabilities are prioritized based on severity and practical impact.
- Fixes are released through GitHub Releases when available.
- Credit can be included in release notes if the reporter wants attribution.

## Scope

Security reports should focus on issues in the Media Flow application, installer,
packaging, update flow, or repository files.

Media Flow processes local files with `ffmpeg`. Issues in third-party tools,
Windows, cloud sync providers, or unsupported modified builds should be reported
to the appropriate upstream project unless Media Flow introduces the vulnerable
behavior.
