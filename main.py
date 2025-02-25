# Import required libraries
from playwright.sync_api import sync_playwright  # For web automation
import re  # For regular expressions
import itertools  # For generating combinations
from datetime import datetime  # For date handling
from playwright._impl._errors import TimeoutError as PlaywrightTimeoutError  # For handling timeouts
import time  # For timing operations

def doubleEqualLine(file):
    # Add a separator line to the output file
    file.write('='*117 + '\n')

def endExecution(file):
    # Write execution completion message with decorative formatting
    file.write("\n\n")
    file.write('='*117 + '\n')
    file.write('||' + '~'*43 + '||   Finished Execution    ||' + '~'*41 + '||\n')
    file.write('='*117 + '\n')

def validate_date(date_str):
    # Check if the provided date string is in valid dd-mm-yyyy format
    try:
        return bool(datetime.strptime(date_str, "%d-%m-%Y"))
    except ValueError:
        return False

def convert_date_format(date_str):
    # Convert date from dd-mm-yyyy to dd-MMM-yyyy format (required by the website)
    date_obj = datetime.strptime(date_str, "%d-%m-%Y")
    return date_obj.strftime("%d-%b-%Y")

def get_search_date():
    # Function to get and validate search date from user
    while True:
        # Ask if user wants to use current date
        use_current = input("Use current date for search? (y/n): ").lower()
        if use_current in ['y', 'n']:
            if use_current == 'y':
                # Return current date in required format
                return datetime.now().strftime("%d-%m-%Y")
            else:
                # Get user input date and validate it
                while True:
                    date_str = input("Enter date (dd-mm-yyyy): ")
                    if validate_date(date_str):
                        return date_str
                    print("Invalid date format. Please use dd-mm-yyyy format.")
        print("Please enter 'y' or 'n'")

def print_ticket_availability(url, file, max_retries=3):
    # Extract search parameters from URL for logging
    date_match = re.search(r"doj=([^&]+)", url)
    from_match = re.search(r"fromcity=([^&]+)", url)
    to_match = re.search(r"tocity=([^&]+)", url)
    
    # Write search parameters to output file
    if date_match and from_match and to_match:
        file.write(f"\nDate: {date_match.group(1)}\n\n")
        file.write(f"From Station : {from_match.group(1)}\n")
        file.write(f"To Station   : {to_match.group(1)}\n\n")
    
    attempt = 0
    while attempt < max_retries:
        try:
            with sync_playwright() as p:
                # Launch the browser
                browser = p.chromium.launch(headless=True)
                # Open a new page
                page = browser.new_page()
                
                # Set longer timeout and handle navigation
                page.set_default_timeout(60000)  # 60 seconds timeout
                page.set_default_navigation_timeout(60000)
                
                # Navigate with custom timeout
                try:
                    page.goto(url, timeout=60000, wait_until='networkidle')
                    page.wait_for_selector('span.all-seats.text-left, span.no-ticket-found-first-msg', timeout=60000)
                    
                    # Check if no trains are found
                    no_trains_el = page.query_selector('span.no-ticket-found-first-msg')
                    if no_trains_el:
                        file.write("No train found for selected dates or cities.\nPlease try different dates or cities.\n\n")
                    else:
                        # Select all train elements
                        train_elements = page.query_selector_all('app-single-trip')
                        for index, train_el in enumerate(train_elements, 1):
                            # Get the train name
                            train_name_el = train_el.query_selector('h2[style="text-transform: uppercase;"]')
                            if train_name_el:
                                # Get journey times
                                start_time = train_el.query_selector('.journey-start .journey-date')
                                end_time = train_el.query_selector('.journey-end .journey-date')
                                
                                start_time_text = start_time.inner_text().split(", ")[1] if start_time else "N/A"
                                end_time_text = end_time.inner_text().split(", ")[1] if end_time else "N/A"
                                
                                # Print train name with journey times
                                file.write(f"({index}) {train_name_el.inner_text()} ({start_time_text}-{end_time_text})\n")
                                
                                # Get the seat availability for each class
                                seat_blocks = train_el.query_selector_all('.single-seat-class')
                                for block in seat_blocks:
                                    seat_class_el = block.query_selector('.seat-class-name')
                                    seat_fare_el = block.query_selector('.seat-class-fare')
                                    if seat_class_el and seat_fare_el:
                                        seat_count_el = block.query_selector('.all-seats.text-left')
                                        file.write(f"   {seat_class_el.inner_text():<10}: {seat_count_el.inner_text():<4} ({seat_fare_el.inner_text()})\n")
                                file.write("\n")
                    
                    browser.close()
                    return  # Success - exit the retry loop
                    
                except PlaywrightTimeoutError:
                    print(f"\nTimeout on attempt {attempt + 1} for {url}")
                    browser.close()
                    attempt += 1
                    if attempt < max_retries:
                        print("Retrying after 5 seconds...")
                        time.sleep(5)
                    continue
                
        except Exception as e:
            print(f"\nError on attempt {attempt + 1}: {str(e)}")
            attempt += 1
            if attempt < max_retries:
                print("Retrying after 5 seconds...")
                time.sleep(5)
            else:
                file.write(f"Error accessing this route after {max_retries} attempts.\n\n")
                print(f"Failed after {max_retries} attempts")

if __name__ == "__main__":
    # Read and display available stations
    with open('C:/Users/babla/Desktop/folders/Projects/ticket/stations.txt', 'r') as file:
        stations = [line.strip() for line in file.readlines()]
    
    # Display available stations with numbering
    print("\nAvailable stations:")
    print("------------------")
    for idx, station in enumerate(stations, 1):
        print(f"{idx}: {station}")
    print("\n")
    
    # Get search date and format it
    date_str = get_search_date()
    formatted_date = convert_date_format(date_str)
    
    # Get station range from user
    start_index = int(input("Enter the starting station number (1-based): ")) - 1
    end_index = int(input("Enter the ending station number (1-based): ")) - 1
    
    # Generate valid station combinations
    station_combinations = []
    for i, from_station in enumerate(stations):
        start = max(i + 1, start_index)
        end = min(end_index + 1, len(stations))
        for to_station in stations[start:end]:
            if from_station != to_station:
                station_combinations.append((from_station, to_station))
    
    # Process combinations and write results
    total_combinations = len(station_combinations)
    output_file = open('C:/Users/babla/Desktop/folders/Projects/ticket/output.txt', 'w', encoding='utf-8')
    
    try:
        for i, (from_station, to_station) in enumerate(station_combinations, 1):
            # Display progress
            remaining = total_combinations - i
            print(f"\nProcessing route: {i} out of {total_combinations} ({from_station} to {to_station}) - Remaining: {remaining}")
            
            # Time the operation
            start_time = time.time()
            
            # Write separator and process the route
            doubleEqualLine(output_file)
            url = f"https://eticket.railway.gov.bd/booking/train/search?fromcity={from_station}&tocity={to_station}&doj={formatted_date}&class=S_CHAIR"
            print_ticket_availability(url, output_file)
            
            # Calculate and display time taken
            end_time = time.time()
            elapsed_time = end_time - start_time
            print(f"Time taken for {from_station} to {to_station}: {elapsed_time:.2f} seconds")
            
            # Ensure output is written immediately
            output_file.flush()
        
        # Write completion message
        endExecution(output_file)
        print("\n-----------------Execution completed--------------------")
    
    finally:
        # Ensure file is closed properly
        output_file.close()