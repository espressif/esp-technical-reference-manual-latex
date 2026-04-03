#!/usr/bin/env python3
"""Check LaTeX links for broken internal and/or external links"""

import os
import re
import argparse
import requests
from requests.exceptions import RequestException
from urllib.parse import unquote
from concurrent.futures import ThreadPoolExecutor

# Unescape LaTeX-escaped characters in URLs (e.g., \_ → _)
def unescape_latex_url(url):
    return url.replace(r'\_', '_').replace(r'\%', '%')

def decode_url(url):
    return unquote(url)

# Extract external links from \href{}{} and \url{} LaTeX commands
def find_external_links(tex_content):
    patterns = [
        r'\\href\{([^\}]+)\}\{[^\}]*\}',
        r'\\url\{([^\}]+)\}'
    ]
    links = []
    for pattern in patterns:
        links.extend(re.findall(pattern, tex_content))
    return links

# Attempt to validate a URL with retry logic
def check_url(url, retries=3, timeout=10):
    headers = {"User-Agent": "Mozilla/5.0 (compatible; LinkChecker/1.0)"}
    last_status = None
    for _ in range(retries):
        try:
            response = requests.get(url, headers=headers, allow_redirects=True, timeout=timeout)
            status = response.status_code
            if status in (200, 301, 302, 401, 403, 418):
                return True, status
            last_status = status
        except RequestException as e:
            last_status = str(e)
    return False, last_status

# Validate multiple URLs concurrently
def check_url_parallel(urls):
    results = []
    seen = set()
    with ThreadPoolExecutor() as executor:
        future_to_url = {
            executor.submit(check_url, url): url
            for url in urls if url not in seen and not seen.add(url)
        }
        for future in future_to_url:
            url = future_to_url[future]
            try:
                is_valid, status = future.result()
                if not is_valid:
                    results.append((url, status))
            except Exception as e:
                results.append((url, str(e)))
    return results

# Parse LaTeX warnings from the log file, omitting known suppressed lines
def extract_warnings(log_path):
    pattern = re.compile(r'LaTeX Warning: (.+)')
    suppressed = {
        "Label `tab:release-status' multiply defined.",
        "There were undefined references.",
        "There were multiply-defined labels.",
    }
    with open(log_path, 'r', encoding='utf-8') as f:
        return [
            m.group(1) for line in f
            if (m := pattern.search(line)) and m.group(1) not in suppressed
        ]

# Classify a warning's type
def classify_warning(warning):
    is_multiply = "multiply defined" in warning
    is_undefined = "undefined" in warning
    is_reg = "fielddesc" in warning or "regdesc" in warning
    return is_multiply, is_undefined, is_reg

# Filter warnings based on type and user options
def filter_warnings(warnings, include_reg_undefined):
    filtered = []
    for w in warnings:
        is_multiply, is_undefined, is_reg = classify_warning(w)

        if is_multiply:
            filtered.append(w)
        elif is_undefined and not is_reg:
            filtered.append(w)
        elif is_undefined and is_reg and include_reg_undefined:
            filtered.append(w)
    return filtered

# Recursively find all .tex files under the specified directory
def find_tex_files(start_dir):
    tex_files = []
    for root, _, files in os.walk(start_dir):
        for f in files:
            if f.endswith(".tex"):
                tex_files.append(os.path.join(root, f))
    return tex_files

# Check for broken external links in LaTeX files
def check_external_links(tex_files):
    url_to_files = {}
    for tex_file in tex_files:
        try:
            with open(tex_file, 'r', encoding='utf-8') as f:
                content = f.read()
                links = find_external_links(content)
                clean_links = [
                    decode_url(unescape_latex_url(url)) for url in links
                    if not url.startswith(r'\linkprefix')
                    and not url.startswith(r'\docpathlatest')
                    and not url.startswith('#1')
                ]
                for url in clean_links:
                    url_to_files.setdefault(url, set()).add(tex_file)
        except Exception as e:
            print(f"Error reading {tex_file}: {e}")
    broken_results = check_url_parallel(list(url_to_files.keys()))
    return [(url, status, sorted(url_to_files[url])) for url, status in broken_results]

def main():
    parser = argparse.ArgumentParser(description="Check broken internal and/or external links in LaTeX documents.")
    parser.add_argument("target", help="Target name (e.g. ESP32-C5)")
    parser.add_argument("lang", choices=["EN", "CN"], help="Language (EN or CN)")

    parser.add_argument("-int", "--internal", action="store_true", help="Check broken internal links (excluding register/field-related warnings by default)")
    parser.add_argument("-ext", "--external", action="store_true", help="Check broken external links only")
    parser.add_argument("-all", "--all", action="store_true", help="Check both internal and external links")
    parser.add_argument("-reg", "--reg", action="store_true", help="Include register/field-related undefined warnings (valid only with -int or -all)")

    args = parser.parse_args()

    # Validate -reg only allowed with -int or -all
    if args.reg and not (args.internal or args.all):
        parser.error("The -reg option can only be used with -int or -all.")

    # Default behavior if no mode flag is given
    if not (args.internal or args.external or args.all):
        args.internal = True
        args.external = True

    run_warnings = args.internal or args.all
    run_links = args.external or args.all

    if run_warnings:
        print(f"\n🔍 Reading LaTeX warnings from: {os.path.join(args.target, 'out', f'{args.target}-main__{args.lang}.log')}")
        all_warnings = extract_warnings(os.path.join(args.target, "out", f"{args.target}-main__{args.lang}.log"))
        include_reg = args.reg or args.all  # -all implies register warnings included
        filtered_warnings = filter_warnings(all_warnings, include_reg)

        if filtered_warnings:
            print("\n⚠️ LaTeX Warnings:")
            for w in filtered_warnings:
                print(f"  {w}")
        else:
            print("\n✅ No relevant LaTeX warnings found.")

    if run_links:
        print(f"\n🔗 Checking external links under: {args.target}")
        tex_files = find_tex_files(args.target)
        broken_links = check_external_links(tex_files)
        if broken_links:
            print("\n❌ Broken External Links:")
            for url, status, sources in broken_links:
                print(f"  {url} (Status: {status})")
                for src in sources:
                    print(f"    ↳ Found in: {src}")
        else:
            print("\n✅ No broken external links found.")

if __name__ == "__main__":
    main()