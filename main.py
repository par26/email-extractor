import csv
import re
import requests
from googlesearch import search
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlunparse
import dns.resolver
import time
from random import randint
import yagooglesearch

# Configuration
max_pages = 15
pageAvoid = ["xml", "zip", "doc", "ppt"]

def find_email_in_text(text):
    email_regex = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_regex, text)
    return list(set(emails))  # Removes duplicates

def get_website_url(business_name, proxies):

    time.sleep(randint(20, 30))

    query = f"{business_name} official site"


    proxyIndex = randint(0, len(proxies)-1)

    client = yagooglesearch.SearchClient(
        query,
        proxy=proxies[proxyIndex],
    )

    try:
        # Only disable SSL/TLS verification for the HTTPS proxy using a self-signed certificate.
        if proxies[proxyIndex].startswith("http://"):
            client.verify_ssl = False


        search_results = client.search()
        for url in search_results:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    return url
            except requests.RequestException:
                continue
    except Exception as e:
        print(f"Error during Google search: {e}")
    return None

def clean_emails(emails):
    cleaned_emails = []
    for email in emails:
        if isinstance(email, list):
            cleaned_emails.extend(email)
        else:
            cleaned_emails.append(email)
    return cleaned_emails

def is_valid_email(email):
    email_regex = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    if not re.fullmatch(email_regex, email):
        return False

    domain = email.split('@')[1]
    try:
        records = dns.resolver.resolve(domain, 'MX')
        return bool(records)
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
        return False

def urljoin(base_url, relative_url):
    base_parts = urlparse(base_url)
    relative_parts = urlparse(relative_url)

    if relative_parts.scheme:
        return relative_url

    path = relative_parts.path
    if not path.startswith('/'):
        base_path = base_parts.path.rsplit('/', 1)[0]
        path = f"{base_path}/{path}"

    full_url_parts = (
        base_parts.scheme,
        base_parts.netloc,
        path,
        relative_parts.params,
        relative_parts.query,
        relative_parts.fragment
    )
    return urlunparse(full_url_parts)

def scrape_email_from_website(url):
    try:
        visited = set()
        to_visit = [url]
        all_content = ""

        while to_visit and len(visited) < max_pages:
            current_url = to_visit.pop(0)
            if current_url in visited:
                continue

            print(f"Crawling: {current_url}")
            try:
                response = requests.get(current_url)
                visited.add(current_url)

                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    all_content += response.text

                    for link in soup.find_all('a', href=True):
                        full_url = urljoin(url, link['href'])
                        if full_url.startswith(url) and full_url not in visited and check_url_valid(full_url):
                            to_visit.append(full_url)
            except requests.RequestException:
                continue  # Skip to the next URL if there's a problem with the request

        emails = find_email_in_text(all_content)
        if emails:
            valid_emails = [email for email in emails if is_valid_email(email)]
            return valid_emails
        return []
    except requests.RequestException:
        return []

def check_url_valid(url):
    for page in pageAvoid:
        if page in url:
            return False
    return True

def main():
    businesses = []
    with open('businesses.csv', 'r') as infile:
        reader = csv.reader(infile)
        businesses = [row[0] for row in reader]

    # Open emails.csv in append mode and write header only if the file is empty
    with open('emails.csv', 'a', newline='') as outfile:
        writer = csv.writer(outfile)
        
        # Check if the file is empty to write headers
        outfile.seek(0, 2)  # Move to the end of file
        if outfile.tell() == 0:  # Check if it's an empty file
            writer.writerow(['Business Name', 'Email'])

        proxies = []
        with open('proxy.csv', 'r') as infile:
            reader = csv.reader(infile)
            proxies = [row[0] for row in reader]
        
        for business in businesses:
            print(f"Processing: {business}")
            url = get_website_url(business, proxies)
            if url:
                emails = scrape_email_from_website(url)
                if emails:
                    for email in emails:
                        writer.writerow([business, email])
                        print(f"Wrote to CSV: {business}, {email}")
                else:
                    writer.writerow([business, 'No email found'])
                    print(f"No email found for {business}")
            else:
                writer.writerow([business, 'No URL found'])
                print(f"No URL found for {business}")

    print("Scraping completed. Check emails.csv for results.")

if __name__ == "__main__":
    main()
