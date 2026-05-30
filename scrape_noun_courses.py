import json
import re
import requests
from bs4 import BeautifulSoup

FACULTY_URLS = [
    "https://nou.edu.ng/ecourseware-faculty-of-edu/",
    "https://nou.edu.ng/ecourseware-faculty-of-sciences/",
    "https://nou.edu.ng/ecourseware-faculty-of-social-sc/",
    "https://nou.edu.ng/ecourseware-faculty-of-management-sc/",
    "https://nou.edu.ng/ecourseware-faculty-of-arts/",
    "https://nou.edu.ng/ecourseware-faculty-of-agric/",
    "https://nou.edu.ng/ecourseware-faculty-of-health-sc/",
    "https://nou.edu.ng/ecourseware-faculty-of-law/",
    "https://nou.edu.ng/ecourseware-faculty-of-computing/"
]

HEADERS = {"User-Agent": "Mozilla/5.0"}

COURSE_RE = re.compile(r"\b([A-Z]{2,4})\s?(\d{3})\b")


def clean(text):
    return re.sub(r"\s+", " ", text).strip()


def extract_courses_from_text(text, source_url):
    courses = {}

    text = clean(text)

    matches = list(COURSE_RE.finditer(text))

    for i, match in enumerate(matches):
        code = f"{match.group(1)}{match.group(2)}"

        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

        chunk = clean(text[start:end])

        # remove credit unit / level / semester / faculty words near the end
        chunk = re.sub(
            r"\b\d+\s+(100|200|300|400|500|600|700|800|900)\s+([12])?\s*(Education|Sciences|Science|Arts|Law|Computing|Management Sciences|Social Sciences|Agricultural Sciences|Health Sciences)?\b.*",
            "",
            chunk,
            flags=re.IGNORECASE
        ).strip()

        # remove common garbage
        chunk = chunk.replace("Course Title", "").replace("Credit Unit", "")
        chunk = chunk.replace("Level", "").replace("Semester", "").replace("Host Faculty", "")
        chunk = clean(chunk)

        if len(chunk) < 3:
            continue

        courses[code] = {
            "title": chunk.title(),
            "source": source_url,
            "psalmedu_material": "https://psalmedu.com/noun-material",
            "summary": "https://psalmedu.com/summary",
            "past_questions": "https://psalmedu.com/noun-past-questions"
        }

    return courses


def scrape_courses():
    all_courses = {}

    for url in FACULTY_URLS:
        print(f"Scraping {url}")

        try:
            response = requests.get(url, headers=HEADERS, timeout=60)
            response.raise_for_status()
        except Exception as e:
            print(f"Failed: {url} -> {e}")
            continue

        soup = BeautifulSoup(response.text, "html.parser")

        # remove scripts/styles
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        page_text = soup.get_text(" ")
        found = extract_courses_from_text(page_text, url)

        print(f"Found {len(found)} courses from {url}")

        all_courses.update(found)

    return all_courses


if __name__ == "__main__":
    courses = scrape_courses()

    with open("courses.json", "w", encoding="utf-8") as f:
        json.dump(courses, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(courses)} total courses to courses.json")