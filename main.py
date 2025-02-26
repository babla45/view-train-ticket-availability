from playwright.sync_api import sync_playwright
import re
import concurrent.futures
from datetime import datetime
from playwright._impl._errors import TimeoutError as PlaywrightTimeoutError
import time
import os
import io

# Constants for performance tuning - adjusted for better performance
MAX_WORKERS = 4  # Reduced from 3 - fewer workers but better resource utilization
BATCH_SIZE = 12  # Increased from 5 - process more routes per browser instance

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

def process_route(page, from_station, to_station, formatted_date, show_no_train_details):
    """Process a single route using an existing page"""
    url = f"https://eticket.railway.gov.bd/booking/train/search?fromcity={from_station}&tocity={to_station}&doj={formatted_date}&class=S_CHAIR"
    
    # Use StringIO to avoid file I/O overhead
    output_buffer = io.StringIO()
    has_available_seats = False
    
    try:
        # Navigate and wait for critical elements - reduced timeouts
        page.goto(url, wait_until='domcontentloaded', timeout=15000)
        page.wait_for_selector('span.all-seats.text-left, span.no-ticket-found-first-msg', timeout=15000)
        
        # Check if no trains are found
        no_trains_el = page.query_selector('span.no-ticket-found-first-msg')
        if no_trains_el:
            if show_no_train_details:
                # Write detailed output
                output_buffer.write(f"\nDate         : {formatted_date}\n")
                output_buffer.write(f"From-To      : {from_station}-{to_station}\n\n")
                output_buffer.write("No train found for selected dates or cities.\nPlease try different dates or cities.\n\n")
            else:
                # Write simplified output
                output_buffer.write(f"No train found for route {from_station}-{to_station}\n")
            return output_buffer.getvalue(), False
        else:
            # More efficient data extraction using a simpler approach
            train_elements = page.query_selector_all('app-single-trip')
            
            # First, check if any train has available seats
            for train_el in train_elements:
                seat_blocks = train_el.query_selector_all('.single-seat-class')
                for block in seat_blocks:
                    count = block.query_selector('.all-seats.text-left')
                    if count and count.inner_text() != "0":
                        has_available_seats = True
                        break
                if has_available_seats:
                    break
            
            # If no available seats and user doesn't want details
            if not has_available_seats and not show_no_train_details:
                output_buffer.write(f"Available 0 tickets for the route {from_station}-{to_station}\n")
                return output_buffer.getvalue(), False
            
            # Otherwise write full detailed output
            output_buffer.write(f"\nDate         : {formatted_date}\n")
            output_buffer.write(f"From-To      : {from_station}-{to_station}\n\n")
            
            for index, train_el in enumerate(train_elements, 1):
                # Extract train name
                train_name = train_el.query_selector('h2[style="text-transform: uppercase;"]')
                if not train_name:
                    continue
                    
                # Get times
                start_time = train_el.query_selector('.journey-start .journey-date')
                end_time = train_el.query_selector('.journey-end .journey-date')
                
                start_time_text = start_time.inner_text().split(", ")[1] if start_time else "N/A"
                end_time_text = end_time.inner_text().split(", ")[1] if end_time else "N/A"
                
                # Write train info
                output_buffer.write(f"({index}) {train_name.inner_text()} ({start_time_text}-{end_time_text})\n")
                
                # Get seat info
                seat_blocks = train_el.query_selector_all('.single-seat-class')
                for block in seat_blocks:
                    class_name = block.query_selector('.seat-class-name')
                    fare = block.query_selector('.seat-class-fare')
                    count = block.query_selector('.all-seats.text-left')
                    
                    if class_name and fare:
                        output_buffer.write(f"   {class_name.inner_text():<10}: {count.inner_text() if count else '0':<4} ({fare.inner_text()})\n")
                
                output_buffer.write("\n")
    
    except PlaywrightTimeoutError:
        output_buffer.write(f"Timeout error accessing {from_station} to {to_station}\n\n")
    except Exception as e:
        output_buffer.write(f"Error processing {from_station} to {to_station}: {str(e)}\n\n")
    
    return output_buffer.getvalue(), has_available_seats

def process_batch(route_batch, formatted_date, completed_routes_counter, total_combinations, show_no_train_details):
    """Process a batch of routes using a single browser instance"""
    with sync_playwright() as p:
        # Launch browser with reduced resource usage
        browser = p.chromium.launch(headless=True)
        
        # Create a single context for all routes in batch
        context = browser.new_context()
        
        results = []
        for from_station, to_station, route_index in route_batch:
            start_time = time.time()
            
            # Create a new page for each route from the shared context
            page = context.new_page()
            
            try:
                # Process the route and get the output text
                output_text, has_seats = process_route(page, from_station, to_station, formatted_date, show_no_train_details)
                elapsed_time = time.time() - start_time
                results.append((from_station, to_station, route_index, output_text, has_seats))
                
                # Update completed routes counter and calculate remaining
                completed_routes_counter.value += 1
                completed = completed_routes_counter.value
                remaining = total_combinations - completed
                
                # Format the route with proper padding for alignment
                route_text = f"( {from_station} to {to_station} )"
                
                # Calculate the width needed for the count based on total combinations
                count_width = len(str(total_combinations))
                
                # Add availability indicator to the status message
                status = "✓" if has_seats else "✗"
                
                # Print with fixed width and better alignment - using right alignment for the count
                print(f"{completed:>{count_width}}. [{status}] Completed {route_text:<35} in {elapsed_time:.2f} seconds - remaining {remaining} routes")
                
            except Exception as e:
                print(f"Error processing {from_station} to {to_station}: {str(e)}")
                # Add error message to maintain sequence
                error_output = f"\nDate: {formatted_date}\n\nFrom Station : {from_station}\nTo Station   : {to_station}\n\n"
                error_output += f"Error: Could not retrieve data for this route: {str(e)}\n\n"
                results.append((from_station, to_station, route_index, error_output, False))
                
                # Still update counter for failed routes
                completed_routes_counter.value += 1
            finally:
                page.close()  # Close page after each route
        
        # Clean up resources
        context.close()
        browser.close()
        
        return results

# Create a class to hold counter that can be shared between threads
class Counter:
    def __init__(self):
        self.value = 0

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

if __name__ == "__main__":
    # Record overall start time
    overall_start = time.time()
    
    # Read station combinations from stations.txt first
    with open('C:/Users/babla/Desktop/folders/Projects/ticket/stations.txt', 'r') as file:
        stations = [line.strip() for line in file.readlines()]
    
    # Print available stations with one-based indices
    print("\nAvailable stations:")
    print("------------------")
    for idx, station in enumerate(stations, 1):
        print(f"{idx}: {station}")
    print("\n")
    
    # Get and validate date input
    date_str = get_search_date()
    formatted_date = convert_date_format(date_str)
    
    # Prompt the user to enter the starting and ending station numbers (1-based)
    start_index = int(input("Enter the starting station range for combination: ")) - 1
    end_index = int(input("Enter the ending station range for combination: ")) - 1
    
    # Ask if user wants detailed output for empty routes
    show_no_train_details = input("Include detailed output for routes with no trains or no seats? (y/n): ").lower() == 'y'
    
    # Generate combinations between start_index and end_index with index to preserve order
    station_combinations = []
    route_index = 0
    for i, from_station in enumerate(stations):
        start = max(i + 1, start_index)
        end = min(end_index + 1, len(stations))
        for to_station in stations[start:end]:
            if from_station != to_station:
                station_combinations.append((from_station, to_station, route_index))
                route_index += 1
    
    total_combinations = len(station_combinations)
    print(f"Total number of routes to process: {total_combinations}\nProcessing routes...\n")
    
    # Create batches for processing
    batches = [station_combinations[i:i+BATCH_SIZE] for i in range(0, len(station_combinations), BATCH_SIZE)]
    
    # Process batches in parallel
    all_results = []
    completed_routes_counter = Counter()  # Share counter between threads
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit batch processing tasks with shared counter
        future_to_batch = {
            executor.submit(process_batch, batch, formatted_date, completed_routes_counter, total_combinations, show_no_train_details): i 
            for i, batch in enumerate(batches)
        }
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(future_to_batch):
            batch_index = future_to_batch[future]
            try:
                batch_results = future.result()
                all_results.extend(batch_results)
                print(f"        Completed batch {batch_index+1}/{len(batches)}")
            except Exception as e:
                print(f"Batch {batch_index} generated an exception: {e}")
    
    # Sort results by route_index to maintain original order
    all_results.sort(key=lambda x: x[2])
    
    # Write directly to output file - no temp files
    with open('C:/Users/babla/Desktop/folders/Projects/ticket/output.txt', 'w', encoding='utf-8') as output_file:
        for from_station, to_station, route_index, output_text, has_seats in all_results:
            doubleEqualLine(output_file)
            output_file.write(output_text)
        
        endExecution(output_file)
    
    # Calculate and display total time
    total_time = time.time() - overall_start
    print(f"\nTotal execution time: {total_time:.2f} seconds for {total_combinations} routes")
    print(f"Average time per route: {total_time/total_combinations:.2f} seconds")
    print(f"Status: Completed {completed_routes_counter.value} routes out of {total_combinations} total routes")
    print("\n-----------------Execution completed--------------------")