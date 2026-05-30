import json
import re
import requests
from bs4 import BeautifulSoup

FACULTY_URLS = [
    "https://nou.edu.ng/ecourseware-faculty-of-edu/",
    "https://nou.edu.ng/ecourseware-faculty-of-science/",
    "https://nou.edu.ng/ecourseware-faculty-of-social-sciences/",
    "https://nou.edu.ng/ecourseware-faculty-of-management-sciences/",
    "https://nou.edu.ng/ecourseware-faculty-of-arts/",
    "https://nou.edu.ng/ecourseware-faculty-of-agricultural-sciences/",
    "https://nou.edu.ng/ecourseware-faculty-of-health-sciences/",
    "https://nou.edu.ng/ecourseware-faculty-of-law/",
    "https://nou.edu.ng/ecourseware-faculty-of-computing/"
]

COURSE_RE = re.compile(r"\b[A-Z]{2,4}\s?\d{3}\b")

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def clean(text):
    return re.sub(r"\s+", " ", text).strip()


def scrape_courses():
    courses = {}

    for url in FACULTY_URLS:
        print(f"Scraping {url}")

        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
        except Exception as e:
            print(f"Failed: {url} -> {e}")
            continue

        soup = BeautifulSoup(response.text, "html.parser")

        for link in soup.find_all("a", href=True):
            text = clean(link.get_text(" "))
            href = link["href"]

            match = COURSE_RE.search(text)
            if not match:
                continue

            code = match.group().replace(" ", "").upper()
            title = clean(text.replace(match.group(), ""))

            if not title:
                continue

            courses[code] = {
                "title": title,
                "source": url,
                "material_source": href,
                "psalmedu_material": "https://psalmedu.com/noun-material",
                "summary": "https://psalmedu.com/summary",
                "past_questions": "https://psalmedu.com/noun-past-questions"
            }

    return courses


if __name__ == "__main__":
    courses = scrape_courses()

    with open("courses.json", "w", encoding="utf-8") as f:
        json.dump(courses, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(courses)} courses to courses.json")
