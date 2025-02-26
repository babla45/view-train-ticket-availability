from playwright.sync_api import sync_playwright
import re
import concurrent.futures
from datetime import datetime
from playwright._impl._errors import TimeoutError as PlaywrightTimeoutError
import time
import os

# Constants for performance tuning
MAX_WORKERS = 3  # Number of parallel browser instances
BATCH_SIZE = 5   # Number of routes per browser instance

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

def process_route(browser, from_station, to_station, formatted_date, output_file):
    """Process a single route using the provided browser instance"""
    url = f"https://eticket.railway.gov.bd/booking/train/search?fromcity={from_station}&tocity={to_station}&doj={formatted_date}&class=S_CHAIR"
    
    # Create a new context for each route (lighter than new browser)
    context = browser.new_context()
    page = context.new_page()
    
    # Write header information
    output_file.write(f"\nDate: {formatted_date}\n\n")
    output_file.write(f"From Station : {from_station}\n")
    output_file.write(f"To Station   : {to_station}\n\n")
    
    try:
        # Set timeouts
        page.set_default_timeout(30000)  # Reduced from 60000 for faster failure detection
        page.set_default_navigation_timeout(30000)
        
        # Navigate and wait for critical elements
        page.goto(url, wait_until='domcontentloaded')  # Changed from 'networkidle' for speed
        page.wait_for_selector('span.all-seats.text-left, span.no-ticket-found-first-msg', timeout=30000)
        
        # Check if no trains are found
        no_trains_el = page.query_selector('span.no-ticket-found-first-msg')
        if no_trains_el:
            output_file.write("No train found for selected dates or cities.\nPlease try different dates or cities.\n\n")
        else:
            # Process train elements more efficiently
            train_elements = page.query_selector_all('app-single-trip')
            
            # Extract data from page more efficiently in one go
            train_data = []
            for index, train_el in enumerate(train_elements, 1):
                train_name_el = train_el.query_selector('h2[style="text-transform: uppercase;"]')
                if not train_name_el:
                    continue
                
                # Use JavaScript evaluation for faster data extraction
                train_info = page.evaluate('''
                    (trainEl) => {
                        const nameEl = trainEl.querySelector('h2[style="text-transform: uppercase;"]');
                        const startTimeEl = trainEl.querySelector('.journey-start .journey-date');
                        const endTimeEl = trainEl.querySelector('.journey-end .journey-date');
                        const seatBlocks = Array.from(trainEl.querySelectorAll('.single-seat-class'));
                        
                        const seatInfo = seatBlocks.map(block => {
                            const classEl = block.querySelector('.seat-class-name');
                            const fareEl = block.querySelector('.seat-class-fare');
                            const countEl = block.querySelector('.all-seats.text-left');
                            
                            return {
                                class: classEl ? classEl.textContent.trim() : 'N/A',
                                fare: fareEl ? fareEl.textContent.trim() : 'N/A',
                                count: countEl ? countEl.textContent.trim() : '0'
                            };
                        });
                        
                        return {
                            name: nameEl ? nameEl.textContent.trim() : 'Unknown',
                            startTime: startTimeEl ? startTimeEl.textContent.split(", ")[1] : 'N/A',
                            endTime: endTimeEl ? endTimeEl.textContent.split(", ")[1] : 'N/A',
                            seats: seatInfo
                        };
                    }
                ''', train_el)
                
                train_data.append(train_info)
            
            # Write the data to file
            for index, train in enumerate(train_data, 1):
                output_file.write(f"({index}) {train['name']} ({train['startTime']}-{train['endTime']})\n")
                
                for seat in train['seats']:
                    output_file.write(f"   {seat['class']:<10}: {seat['count']:<4} ({seat['fare']})\n")
                
                output_file.write("\n")
    
    except PlaywrightTimeoutError:
        output_file.write(f"Timeout error accessing {from_station} to {to_station}\n\n")
    except Exception as e:
        output_file.write(f"Error processing {from_station} to {to_station}: {str(e)}\n\n")
    finally:
        # Always close the context to free resources
        context.close()
    
    return from_station, to_station

def process_batch(route_batch, formatted_date, output_lock):
    """Process a batch of routes using a single browser instance"""
    with sync_playwright() as p:
        # Launch a browser instance to be reused across all routes in this batch
        browser = p.chromium.launch(headless=True)
        
        results = []
        for from_station, to_station in route_batch:
            # Create a temporary file for this route
            temp_filename = f"temp_{from_station}_{to_station}.txt"
            with open(temp_filename, 'w', encoding='utf-8') as temp_file:
                start_time = time.time()
                
                try:
                    # Process the route
                    process_route(browser, from_station, to_station, formatted_date, temp_file)
                    elapsed_time = time.time() - start_time
                    results.append((from_station, to_station, elapsed_time, temp_filename))
                    print(f"Completed {from_station} to {to_station} in {elapsed_time:.2f} seconds")
                except Exception as e:
                    print(f"Error processing {from_station} to {to_station}: {str(e)}")
        
        # Close the browser when done with all routes in this batch
        browser.close()
        
        return results

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
    start_index = int(input("Enter the starting station number (1-based): ")) - 1
    end_index = int(input("Enter the ending station number (1-based): ")) - 1
    
    # Generate combinations between start_index and end_index
    station_combinations = []
    for i, from_station in enumerate(stations):
        start = max(i + 1, start_index)
        end = min(end_index + 1, len(stations))
        for to_station in stations[start:end]:
            if from_station != to_station:
                station_combinations.append((from_station, to_station))
    
    total_combinations = len(station_combinations)
    print(f"Total routes to process: {total_combinations}")
    
    # Create batches for processing
    batches = [station_combinations[i:i+BATCH_SIZE] for i in range(0, len(station_combinations), BATCH_SIZE)]
    
    # Process batches in parallel
    all_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit batch processing tasks
        future_to_batch = {
            executor.submit(process_batch, batch, formatted_date, None): i 
            for i, batch in enumerate(batches)
        }
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(future_to_batch):
            batch_index = future_to_batch[future]
            try:
                batch_results = future.result()
                all_results.extend(batch_results)
                print(f"Completed batch {batch_index+1}/{len(batches)}")
            except Exception as e:
                print(f"Batch {batch_index} generated an exception: {e}")
    
    # Combine results into final output file
    with open('C:/Users/babla/Desktop/folders/Projects/ticket/output.txt', 'w', encoding='utf-8') as output_file:
        for from_station, to_station, elapsed_time, temp_filename in all_results:
            doubleEqualLine(output_file)
            
            # Copy content from temp file
            with open(temp_filename, 'r', encoding='utf-8') as temp_file:
                output_file.write(temp_file.read())
            
            # Delete temp file
            os.remove(temp_filename)
        
        endExecution(output_file)
    
    # Calculate and display total time
    total_time = time.time() - overall_start
    print(f"\nTotal execution time: {total_time:.2f} seconds for {total_combinations} routes")
    print(f"Average time per route: {total_time/total_combinations:.2f} seconds")
    print("\n-----------------Execution completed--------------------")