from playwright.sync_api import sync_playwright
import re


def doubleEqualLine():
    print('=====================================================================================================================')
    print('=====================================================================================================================')

def print_ticket_availability(url):
    # Extract the date, from, and to stations from the URL
    date_match = re.search(r"doj=([^&]+)", url)
    from_match = re.search(r"fromcity=([^&]+)", url)
    to_match = re.search(r"tocity=([^&]+)", url)
    
    if date_match and from_match and to_match:
        print("\nDate:", date_match.group(1),"\n")
        print("From Station :", from_match.group(1))
        print("To Station   :", to_match.group(1), "\n")
    
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
        for index, train_el in enumerate(train_elements, 1):
            # Get the train name
            train_name_el = train_el.query_selector('h2[style="text-transform: uppercase;"]')
            if train_name_el:
                print(f"({index})", train_name_el.inner_text())
                # Get the seat availability for each class
                seat_blocks = train_el.query_selector_all('.single-seat-class')
                for block in seat_blocks:
                    seat_class_el = block.query_selector('.seat-class-name')
                    seat_fare_el = block.query_selector('.seat-class-fare')
                    if seat_class_el and seat_fare_el:
                        seat_count_el = block.query_selector('.all-seats.text-left')
                        print("   ", f"{seat_class_el.inner_text():<10}:", f"{seat_count_el.inner_text():<4}", "(", seat_fare_el.inner_text(), ")")
                print("\n")
        
        # Close the browser
        browser.close()

if __name__ == "__main__": 
    # Check ticket availability for different dates and routes
    doubleEqualLine()
    print_ticket_availability("https://eticket.railway.gov.bd/booking/train/search?fromcity=Parbatipur&tocity=Natore&doj=04-Mar-2025&class=S_CHAIR")
    doubleEqualLine()   
    print_ticket_availability("https://eticket.railway.gov.bd/booking/train/search?fromcity=Jashore&tocity=Chilahati&doj=23-Feb-2025&class=S_CHAIR")
    doubleEqualLine()
    print_ticket_availability("https://eticket.railway.gov.bd/booking/train/search?fromcity=Jashore&tocity=Chilahati&doj=24-Feb-2025&class=S_CHAIR")
    doubleEqualLine()
    print_ticket_availability("https://eticket.railway.gov.bd/booking/train/search?fromcity=Jashore&tocity=Chilahati&doj=25-Feb-2025&class=S_CHAIR")
    doubleEqualLine()
    print_ticket_availability("https://eticket.railway.gov.bd/booking/train/search?fromcity=Jashore&tocity=Chilahati&doj=26-Feb-2025&class=S_CHAIR")

    print("\n\n")
    print('=====================================================================================================================')
    print('=====================================================================================================================')
    print('||                                         Finished Execution                                                      ||')
    print('=====================================================================================================================')
    print('=====================================================================================================================')