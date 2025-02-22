from playwright.sync_api import sync_playwright
import re

def print_ticket_availability(url):
    # Extract the date from the URL
    date_match = re.search(r"doj=([^&]+)", url)
    if date_match:
        print("Date:", date_match.group(1))
    
    with sync_playwright() as p:
        # Launch the browser
        browser = p.chromium.launch(headless=True)
        # Open a new page
        page = browser.new_page()
        # Navigate to the URL
        page.goto(url)
        # Wait for the seat availability elements to load
        page.wait_for_selector('span.all-seats.text-left')
        
        # Select all train elements
        train_elements = page.query_selector_all('app-single-trip')
        for train_el in train_elements:
            # Get the train name
            train_name_el = train_el.query_selector('h2[style="text-transform: uppercase;"]')
            if train_name_el:
                print("Train Name:", train_name_el.inner_text())
                # Get the seat availability for each class
                seat_blocks = train_el.query_selector_all('.single-seat-class')
                for block in seat_blocks:
                    seat_class_el = block.query_selector('.seat-class-name')
                    if seat_class_el:
                        seat_count_el = block.query_selector('.all-seats.text-left')
                        print(seat_class_el.inner_text(), ":", seat_count_el.inner_text() if seat_count_el else 0)
        
        # Close the browser
        browser.close()

if __name__ == "__main__":
    # Check ticket availability for different dates and routes
    print_ticket_availability(
        "https://eticket.railway.gov.bd/booking/train/search?fromcity=Parbatipur&tocity=Natore&doj=04-Mar-2025&class=S_CHAIR"
    )
    print('=====================================================================================================================')
    print_ticket_availability(
        "https://eticket.railway.gov.bd/booking/train/search?fromcity=Jashore&tocity=Chilahati&doj=23-Feb-2025&class=S_CHAIR"
    )
    print('=====================================================================================================================')
    # Uncomment the following lines to check more dates and routes
    print_ticket_availability(
        "https://eticket.railway.gov.bd/booking/train/search?fromcity=Jashore&tocity=Chilahati&doj=24-Feb-2025&class=S_CHAIR"
    )
    print('=====================================================================================================================')
    print_ticket_availability(
        "https://eticket.railway.gov.bd/booking/train/search?fromcity=Jashore&tocity=Chilahati&doj=25-Feb-2025&class=S_CHAIR"
    )
    print('=====================================================================================================================')
    print_ticket_availability(
        "https://eticket.railway.gov.bd/booking/train/search?fromcity=Jashore&tocity=Chilahati&doj=26-Feb-2025&class=S_CHAIR"
    )