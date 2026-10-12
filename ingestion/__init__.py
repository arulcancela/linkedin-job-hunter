"""Ingestion module for fetching and parsing job postings."""

from ingestion.extractor import extract_job_from_url
from ingestion.text_reader import read_from_clipboard_or_input, read_from_file

__all__ = ["extract_job_from_url", "read_from_clipboard_or_input", "read_from_file"]
