---
name: discovery-url-deletion
description: Delete specific URLs from IBM Watson Discovery collections by querying for documents matching those URLs and removing them from the index
disable-model-invocation: true
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
argument-hint: "[urls-file (optional)]"
---

# Delete URLs from Watson Discovery

Delete specific URLs from all collections in an IBM Watson Discovery project. This does NOT delete entire collections or indexes — only the individual documents matching the provided URLs.

## Prerequisites

- Python 3.9+ installed
- Dependencies installed: `pip install -r requirements.txt`
- `config.env` populated with your Watson Discovery credentials:
  - `DISCOVERY_API_KEY` — your IBM Cloud IAM API key
  - `DISCOVERY_URL` — your Discovery service URL (including `/instances/<instance-id>`)
  - `DISCOVERY_PROJECT_ID` — your project ID
  - `DISCOVERY_API_VERSION` — API version date (default `2023-03-31`)

## Steps

1. Read the URLs to delete:
   - If `$ARGUMENTS` is provided, use it as the path to a URL file
   - Otherwise use `urls_to_delete.txt` in the project root
   - The file should have one URL per line; lines starting with `#` and blank lines are ignored

2. Run the deletion script:
   ```bash
   cd /Users/dkoul/watson-discovery-url-deletion && python delete_urls.py $ARGUMENTS
   ```

3. Review the output summary and report results to the user:
   - How many URLs were processed
   - How many documents were deleted
   - How many URLs were not found in any collection
   - Any errors encountered

4. If there are errors:
   - Authentication errors → ask the user to verify their API key in `config.env`
   - Project/collection not found → ask the user to verify their project ID in `config.env`
   - URL not found → confirm the URL field name (`metadata.source.url`) matches their document schema
