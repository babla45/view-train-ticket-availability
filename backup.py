from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # Set headless=True if you don't want a GUI
    page = browser.new_page()

    # Navigate to the website
    page.goto("https://eticket.railway.gov.bd/")

    # Click "I AGREE" button
    page.get_by_role("button", name="I AGREE").click()

    # Select "From" location
    page.get_by_role("textbox", name="From").click()
    page.get_by_role("textbox", name="From").fill("Khulna")

    # Select "To" location
    page.get_by_role("textbox", name="To").click()
    page.get_by_role("textbox", name="To").fill("Parbatipur")

    # Select date
    page.get_by_role("img", name="...").click()
    page.get_by_role("link", name="27").click()

    # Select class
    page.get_by_label("Choose Class").select_option("S_CHAIR")

    # Click "Search Trains"
    page.get_by_role("button", name="Search Trains").click()

    # Keep the browser open for inspection
    page.wait_for_timeout(10000)  # Wait for 5 seconds before closing
    browser.close()

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

from playwright.sync_api import sync_playwright

def print_ticket_availability(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)
        page.wait_for_selector('span.all-seats.text-left')
        
        train_name_el = page.query_selector('.search-body-head h3')
        if train_name_el:
            print("Train Name:", train_name_el.inner_text())
        
        seat_blocks = page.query_selector_all('.single-seat-class')
        for block in seat_blocks:
            seat_class_el = block.query_selector('.seat-class-name')
            if seat_class_el:
                seat_count_el = block.query_selector('.all-seats.text-left')
                print(seat_class_el.inner_text(), ":", seat_count_el.inner_text() if seat_count_el else 0)
        
        browser.close()

if __name__ == "__main__":
    print_ticket_availability("https://eticket.railway.gov.bd/booking/train/search?fromcity=Jashore&tocity=Chilahati&doj=23-Feb-2025&class=S_CHAIR")
