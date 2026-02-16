#!/usr/bin/env python3
"""
Delete specific URLs from IBM Watson Discovery collections.

Reads URLs from urls_to_delete.txt, searches all collections in the
configured project for documents matching those URLs, and deletes them.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from ibm_watson import DiscoveryV2
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator


def load_config():
    """Load configuration from config.env file."""
    env_path = Path(__file__).parent / "config.env"
    load_dotenv(env_path)

    required = ["DISCOVERY_API_KEY", "DISCOVERY_URL", "DISCOVERY_PROJECT_ID"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        print(f"ERROR: Missing required config in .env: {', '.join(missing)}")
        sys.exit(1)

    return {
        "api_key": os.getenv("DISCOVERY_API_KEY"),
        "url": os.getenv("DISCOVERY_URL"),
        "project_id": os.getenv("DISCOVERY_PROJECT_ID"),
        "version": os.getenv("DISCOVERY_API_VERSION", "2023-03-31"),
    }


def load_urls(filepath):
    """Load URLs from a text file (one per line, # comments and blanks ignored)."""
    path = Path(filepath)
    if not path.exists():
        print(f"ERROR: URL file not found: {filepath}")
        sys.exit(1)

    urls = []
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            urls.append(stripped)

    return urls


def create_client(config):
    """Initialize the Watson Discovery client."""
    authenticator = IAMAuthenticator(config["api_key"])
    discovery = DiscoveryV2(version=config["version"], authenticator=authenticator)
    discovery.set_service_url(config["url"])
    return discovery


def get_collections(discovery, project_id):
    """Return a list of (collection_id, collection_name) tuples."""
    response = discovery.list_collections(project_id=project_id).get_result()
    collections = response.get("collections", [])
    return [(c["collection_id"], c.get("name", "Unnamed")) for c in collections]


def find_documents_by_url(discovery, project_id, collection_id, url):
    """Query a collection for documents matching the given source URL.

    Returns a list of document_id strings.
    """
    # DQL exact-match filter on the metadata source URL field
    filter_query = f'metadata.source.url::"{url}"'

    doc_ids = []
    offset = 0
    page_size = 100

    while True:
        response = discovery.query(
            project_id=project_id,
            collection_ids=[collection_id],
            filter=filter_query,
            return_=["document_id", "metadata.source.url"],
            count=page_size,
            offset=offset,
        ).get_result()

        results = response.get("results", [])
        if not results:
            break

        for doc in results:
            doc_id = doc.get("document_id")
            if doc_id:
                doc_ids.append(doc_id)

        if len(results) < page_size:
            break
        offset += page_size

    return doc_ids


def delete_document(discovery, project_id, collection_id, document_id):
    """Delete a single document and return True on success."""
    response = discovery.delete_document(
        project_id=project_id,
        collection_id=collection_id,
        document_id=document_id,
    ).get_result()

    return response.get("status") == "deleted"


def main():
    url_file = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).parent / "urls_to_delete.txt")

    config = load_config()
    urls = load_urls(url_file)

    if not urls:
        print("No URLs found in input file. Nothing to do.")
        sys.exit(0)

    print(f"Loaded {len(urls)} URL(s) to delete.")

    discovery = create_client(config)
    project_id = config["project_id"]

    collections = get_collections(discovery, project_id)
    if not collections:
        print("ERROR: No collections found in the project.")
        sys.exit(1)

    print(f"Found {len(collections)} collection(s):")
    for cid, cname in collections:
        print(f"  - {cname} ({cid})")
    print()

    total_deleted = 0
    total_not_found = 0
    errors = []

    for url in urls:
        print(f"Processing: {url}")
        found_any = False

        for collection_id, collection_name in collections:
            doc_ids = find_documents_by_url(discovery, project_id, collection_id, url)

            if not doc_ids:
                continue

            found_any = True
            for doc_id in doc_ids:
                try:
                    success = delete_document(discovery, project_id, collection_id, doc_id)
                    if success:
                        print(f"  Deleted doc {doc_id} from '{collection_name}'")
                        total_deleted += 1
                    else:
                        print(f"  WARNING: Unexpected status deleting doc {doc_id} from '{collection_name}'")
                        errors.append((url, doc_id, collection_name, "unexpected status"))
                except Exception as e:
                    print(f"  ERROR deleting doc {doc_id} from '{collection_name}': {e}")
                    errors.append((url, doc_id, collection_name, str(e)))

        if not found_any:
            print("  Not found in any collection.")
            total_not_found += 1

    # Summary
    print("\n--- Summary ---")
    print(f"URLs processed:  {len(urls)}")
    print(f"Documents deleted: {total_deleted}")
    print(f"URLs not found:  {total_not_found}")
    if errors:
        print(f"Errors:          {len(errors)}")
        for url, doc_id, cname, err in errors:
            print(f"  {url} | doc {doc_id} in '{cname}': {err}")


if __name__ == "__main__":
    main()
