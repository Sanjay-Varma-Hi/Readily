import re

# Test text that contains "Page 27 of 72"
test_text = " and bill for the applicable Qualifying Services (excluding GEMT Services) on \nthe date of service. Notwithstanding the above, if the Provider's written contract with CalOptima Health  does \nnot meet the network provider criteria set forth in DHCS APL 19 -001: Medi -Cal Managed Care Health Plan \nGuidanc e on Network Provider Status and/or in DHCS guidance regarding Directed Payments, the services \nprovided by the Provider under that contract shall not be eligible for Directed Payments for rating periods \ncommencing on or after July 1, 2019.  \n \n \n \nPage 27 of 72                                    AA.1000: Medi -Cal Glossary of Terms                               Revised:  02/01/2025  Emergency Management Team (EMT) : CalOptima Health  ..."

print("Testing page extraction patterns:")
print(f"Text contains 'Page 27 of 72': {'Page 27 of 72' in test_text}")

# Test different patterns
page_patterns = [
    r'Page (\d+) of \d+',
    r'page (\d+) of \d+',
    r'PAGE (\d+) OF \d+',
    r'Page\s+(\d+)\s+of\s+\d+',
    r'Page\s+(\d+)\s+of\s+(\d+)'
]

for i, pattern in enumerate(page_patterns):
    page_match = re.search(pattern, test_text, re.IGNORECASE)
    if page_match:
        print(f"Pattern {i+1} matched: {pattern} -> Page {page_match.group(1)}")
    else:
        print(f"Pattern {i+1} did not match: {pattern}")

# Test the exact text we see
exact_pattern = r'Page 27 of 72'
if re.search(exact_pattern, test_text):
    print(f"Exact pattern matched: {exact_pattern}")
else:
    print(f"Exact pattern did not match: {exact_pattern}")

# Look for any "Page" followed by numbers
any_page = re.search(r'Page\s*(\d+)\s*of\s*(\d+)', test_text)
if any_page:
    print(f"Any page pattern matched: Page {any_page.group(1)} of {any_page.group(2)}")
else:
    print("No page pattern matched at all")
