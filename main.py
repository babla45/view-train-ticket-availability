from playwright.sync_api import sync_playwright
# import re
import concurrent.futures
from datetime import datetime, timedelta
from playwright._impl._errors import TimeoutError as PlaywrightTimeoutError
import time
# import os
import io
from multiprocessing import Value
import re

# Constants for performance tuning
MAX_WORKERS = 6  # Increased parallel browser instances
BATCH_SIZE = 40  # Larger batches reduce browser launch overhead
NAVIGATION_TIMEOUT = 15000  # 15 seconds
SELECTOR_TIMEOUT = 10000   # 10 seconds
# Add counters for routes with and without seats
ROUTES_WITH_SEATS = Value('i', 0)
ROUTES_WITHOUT_SEATS = Value('i', 0)

def doubleEqualLine(file):
    file.write('='*84 + '\n')

def endExecution(file):
    file.write("\n\n")
    file.write('='*84 + '\n')
    file.write('|| ' + '~'*24 + ' ||   Finished Execution   || ' + '~'*24 + ' ||\n')
    file.write('='*84 + '\n')

def validate_date(date_str):
    try:
        return bool(datetime.strptime(date_str, "%d-%m-%Y"))
    except ValueError:
        return False

def convert_date_format(date_str):
    date_obj = datetime.strptime(date_str, "%d-%m-%Y")
    return date_obj.strftime("%d-%b-%Y")

def process_route(page, from_station, to_station, formatted_date, show_no_train_details):
    """Process a single route using a shared page"""
    url = f"https://eticket.railway.gov.bd/booking/train/search?fromcity={from_station}&tocity={to_station}&doj={formatted_date}&class=S_CHAIR"
    output_buffer = io.StringIO()
    has_available_seats = False

    try:
        # Removed redundant navigation reset
        # page.goto('about:blank', wait_until='commit', timeout=NAVIGATION_TIMEOUT)
        page.goto(url, wait_until='domcontentloaded', timeout=NAVIGATION_TIMEOUT)
        
        # Wait for critical elements with optimized timeout
        page.wait_for_selector('span.all-seats.text-left, span.no-ticket-found-first-msg', timeout=SELECTOR_TIMEOUT)

        # Check if no trains are found
        no_trains_el = page.query_selector('span.no-ticket-found-first-msg')
        if no_trains_el:
            if show_no_train_details:
                output_buffer.write(f"\nDate          : {formatted_date}\nFrom-To       : {from_station}-{to_station}\n✗ No train found for selected dates or cities. Please try different dates or cities.\n\n")
            else:
                output_buffer.write(f"Date: {formatted_date} - No train found for route {from_station}-{to_station}\n")
            return output_buffer.getvalue(), False
        
        # Quick check for any available seats using optimized selector
        available_seat = page.query_selector('.all-seats.text-left:not(:text-is("0"))')
        has_available_seats = available_seat is not None

        # Update the seat availability counters
        if has_available_seats:
            with ROUTES_WITH_SEATS.get_lock():
                ROUTES_WITH_SEATS.value += 1
        else:
            with ROUTES_WITHOUT_SEATS.get_lock():
                ROUTES_WITHOUT_SEATS.value += 1

        if not has_available_seats and not show_no_train_details:
            output_buffer.write(f"Date: {formatted_date} - Available 0 tickets for the route {from_station}-{to_station}\n")
            return output_buffer.getvalue(), False

        # Only process full details when necessary
        output_buffer.write(f"\n    Date      : {formatted_date}\n    From-To   : {from_station}-{to_station}")
        output_buffer.write(f"\n    URL       : {url}\n\n")
        
        train_elements = page.query_selector_all('app-single-trip')
        
        # Process and filter trains if we're not showing zero-ticket trains
        filtered_trains = []
        for index, train_el in enumerate(train_elements, 1):
            train_name = train_el.query_selector('h2[style="text-transform: uppercase;"]')
            journey_duration = train_el.query_selector('.journey-duration').inner_text()
            if not train_name:
                continue

            # Efficient time extraction
            times = train_el.evaluate('''el => {
                const start = el.querySelector('.journey-start .journey-date')?.innerText.split(', ')[1] || 'N/A';
                const end = el.querySelector('.journey-end .journey-date')?.innerText.split(', ')[1] || 'N/A';
                return {start, end};
            }''')
            
            # Consolidated seat data extraction
            seats_data = train_el.evaluate('''el => {
                return [...el.querySelectorAll('.single-seat-class')].map(seat => ({
                    class_name: seat.querySelector('.seat-class-name')?.innerText || '',
                    fare: seat.querySelector('.seat-class-fare')?.innerText || '',
                    count: seat.querySelector('.all-seats.text-left')?.innerText || '0'
                }));
            }''')
            
            # Check if any tickets are available for this train
            has_tickets = False
            for seat in seats_data:
                if seat['count'] != '0':
                    has_tickets = True
                    break
            
            # If we're not showing zero-ticket trains and this train has no tickets, skip it
            if not show_no_train_details and not has_tickets:
                continue
                
            # If we get here, the train should be included in the output
            filtered_trains.append({
                'index': index,
                'name': train_name.inner_text(),
                'times': times,
                'duration': journey_duration,
                'seats': seats_data
            })
        
        # Write the filtered trains to the output buffer
        for idx, train in enumerate(filtered_trains, 1):
            output_buffer.write(f"({idx}) {train['name']} ({train['times']['start']}-{train['times']['end']}) [{train['duration']}]\n")
            
            for seat in train['seats']:
                output_buffer.write(f"    {seat['class_name']:<10}: {seat['count']:<4} ({seat['fare']})\n")
            output_buffer.write("\n")

    except PlaywrightTimeoutError:
        output_buffer.write(f"Timeout error accessing {from_station} to {to_station}\n\n")
    except Exception as e:
        output_buffer.write(f"Error processing {from_station} to {to_station}: {str(e)}\n\n")
    
    return output_buffer.getvalue(), has_available_seats

def process_batch(route_batch, formatted_date, completed_routes_counter, total_combinations, show_no_train_details):
    """Process a batch of routes using a single browser and page"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        results = []
        for from_station, to_station, route_index in route_batch:
            start_time = time.time()
            try:
                output_text, has_seats = process_route(page, from_station, to_station, formatted_date, show_no_train_details)
                elapsed_time = time.time() - start_time
                results.append((from_station, to_station, route_index, output_text, has_seats))

                with completed_routes_counter.get_lock():
                    completed_routes_counter.value += 1
                    completed = completed_routes_counter.value
                    remaining = total_combinations - completed

                route_text = f"( {from_station} to {to_station} )"
                count_width = len(str(total_combinations))
                status = "✓" if has_seats else "✗"
                print(f"{completed:>{count_width}}. [{status}] Completed {route_text:<35} in {elapsed_time:.2f}s - remaining {remaining}")

            except Exception as e:
                error_output = f"\nJourney Date: {formatted_date}\n\nFrom Station : {from_station}\nTo Station   : {to_station}\n\nError: {str(e)}\n\n"
                results.append((from_station, to_station, route_index, error_output, False))
                with completed_routes_counter.get_lock():
                    completed_routes_counter.value += 1
                print(f"Error processing {from_station} to {to_station}: {str(e)}")

        page.close()
        context.close()
        browser.close()
        return results

def get_search_date():
    while True:
        use_current = input("\n\nUse current date for search? (y/n): ").lower()
        if use_current == 'y':
            return [datetime.now().strftime("%d-%m-%Y")]
        elif use_current == 'n':
            # Display next 11 days (including today) as a list
            today = datetime.now()
            dates = [(today + timedelta(days=i)) for i in range(11)]
            
            print(f"\nAvailable dates for search:\n{'='*27}")
            for idx, date in enumerate(dates, 1):
                date_str = date.strftime("%d-%m-%Y")
                print(f"{idx}: {date_str} ({date.strftime('%A')})")
            # print(f"{'='*27}")
            
            print(f"\nChoose option: e.g. for single: 5, for range: 2-5, for multiple: 1,3,6\n{'='*70}")
            
            while True:
                date_input = input("Enter your date selection: ")
                selected_dates = []
                
                # Check if input is a range (e.g., "1-5")
                if '-' in date_input and ',' not in date_input:
                    try:
                        start, end = map(int, date_input.split('-'))
                        if 1 <= start <= end <= 11:
                            selected_dates = [dates[i-1].strftime("%d-%m-%Y") for i in range(start, end+1)]
                        else:
                            print("Invalid range. Please use numbers between 1 and 11.")
                            continue
                    except ValueError:
                        print("Invalid range format. Use format like '1-5'.")
                        continue
                # Check if input is a comma-separated list
                elif ',' in date_input:
                    try:
                        indices = [int(idx.strip()) for idx in date_input.split(',')]
                        if all(1 <= idx <= 11 for idx in indices):
                            selected_dates = [dates[idx-1].strftime("%d-%m-%Y") for idx in indices]
                        else:
                            print("Invalid selection. Please use numbers between 1 and 11.")
                            continue
                    except ValueError:
                        print("Invalid format. Use comma-separated numbers like '1,3,5'.")
                        continue
                # Check if input is a single number
                else:
                    try:
                        idx = int(date_input)
                        if 1 <= idx <= 11:
                            selected_dates = [dates[idx-1].strftime("%d-%m-%Y")]
                        else:
                            print("Invalid selection. Please use a number between 1 and 11.")
                            continue
                    except ValueError:
                        print("Invalid input. Please enter a number, range, or comma-separated list.")
                        continue
                
                # Confirm dates are in valid format
                if all(validate_date(date) for date in selected_dates):
                    return selected_dates
                
                print("Invalid date selection. Please try again.")
        
        print("Please enter 'y' or 'n'")

def parse_station_list_file():
    """Parse the stationList.txt file to extract train routes and their stations"""
    train_routes = []
    mixed_counter = 1  # Counter for Mixed routes
    
    try:
        with open('stationList.txt', 'r') as file:
            lines = file.readlines()
            i = 0
            
            while i < len(lines):
                line = lines[i].strip()
                
                # Skip empty lines
                if not line:
                    i += 1
                    continue
                
                # Check for route headers with numbers (e.g., "5. Mixed from uttarbanga to Dhaka")
                match = re.match(r'^\d+\.\s+(.+)$', line)
                if match:
                    route_name = match.group(1).strip()
                    
                    # If the line ends with a colon, it's a standard train entry
                    if route_name.endswith(':'):
                        route_name = route_name[:-1].strip()
                        
                    # Check if this is a Mixed route and apply special format
                    if "Mixed" in route_name:
                        route_name = f"Mixed_{mixed_counter} {route_name.replace('Mixed', '').strip()}"
                        mixed_counter += 1
                    
                    # Collect stations for this route
                    stations = []
                    i += 1
                    
                    # Keep reading until we hit another numbered entry or end of file
                    while i < len(lines) and not re.match(r'^\d+\.', lines[i].strip()):
                        station = lines[i].strip()
                        if station:  # Only add non-empty lines
                            stations.append(station)
                        i += 1
                    
                    # Add the route with its stations
                    if stations:
                        train_routes.append((route_name, stations))
                    
                else:
                    i += 1  # Move to next line if not a route header
            
        return train_routes
    except FileNotFoundError:
        print("stationList.txt file not found.")
        return []
    except Exception as e:
        print(f"Error parsing stationList.txt: {str(e)}")
        return []

def get_stations():
    """Let user choose which station list to use"""
    # First, check if default stations.txt exists
    try:
        with open('stations.txt', 'r') as file:
            default_stations = [line.strip() for line in file.readlines()]
    except FileNotFoundError:
        print("stations.txt file not found.")
        default_stations = []
    
    # Parse train routes from stationList.txt
    train_routes = parse_station_list_file()
    
    # Display options to user in a formatted table
    print("\nSelect a train to use its route (station list):\n")
    # Make the default option more visible with stars
    print(" 1.  Default station list         provided in stations.txt file")
    
    for i, (route_name, _) in enumerate(train_routes, 2):
        # Split route name to extract train name and route info
        parts = route_name.split(",") if "," in route_name else [route_name, ""]
        
        # For Mixed routes, split differently
        if "Mixed_" in parts[0]:
            # Extract Mixed_N and the route info
            mixed_parts = parts[0].split(" ", 1)
            train_name = mixed_parts[0]
            route_info = mixed_parts[1] if len(mixed_parts) > 1 else ""
        else:
            train_name = parts[0].strip()
            route_info = parts[1].strip() if len(parts) > 1 else ""
        
        # Format the output with proper alignment, ensuring consistent spacing
        # Right-align the number with fixed width to ensure proper alignment for all numbers
        print(f"{i:>2}.  {train_name:<28} {route_info}")
    
    # Get user's choice
    total_options = len(train_routes) + 1
    selected_route_name = "Default station list"
    
    while True:
        try:
            choice = int(input(f"\nEnter your choice (1-{total_options}): "))
            
            if choice == 1:
                if not default_stations:
                    print("Default station list is empty. Please choose another option.")
                    continue
                return default_stations, selected_route_name
            elif 2 <= choice <= total_options:
                selected_stations = train_routes[choice - 2][1]
                selected_route_name = "("+str(choice-1) + ") " + train_routes[choice - 2][0]
                print(f"\nSelected Train Route : {selected_route_name}")
                print(f"Number of stations   : {len(selected_stations)}")
                return selected_stations, selected_route_name
            else:
                print(f"Please enter a number between 1 and {total_options}.")
        except ValueError:
            print("Please enter a valid number.")

def find_intermediate_routes(stations, src_idx, dst_idx, range_val):
    """Find routes using intermediate stations based on user input"""
    # Define source station range
    src_start = max(0, src_idx - range_val)
    src_end = min(len(stations) - 1, src_idx + range_val)
    
    # Define destination station range
    dst_start = max(0, dst_idx - range_val)
    dst_end = min(len(stations) - 1, dst_idx + range_val)
    
    # Define intermediate station range (all stations between source and destination)
    intermediate_start = src_idx + 1
    intermediate_end = dst_idx - 1
    
    # If there are no valid intermediate stations
    if intermediate_start > intermediate_end:
        return []
    
    # Generate all possible routes through intermediate stations
    routes = []
    for src in range(src_start, src_end + 1):
        for dst in range(dst_start, dst_end + 1):
            for mid in range(intermediate_start, intermediate_end + 1):
                # Add route: source -> intermediate -> destination
                routes.append((stations[src], stations[mid], stations[dst]))
    
    return routes

def extract_train_names(route_text):
    """Extract train names from route text output"""
    train_names = []
    lines = route_text.split('\n')
    
    for line in lines:
        # Look for lines that start with a train listing pattern like "(1) TRAIN_NAME"
        if re.match(r'^\(\d+\)\s+[A-Z\s]+\s+\(', line):
            # Extract the train name between the number and the time
            match = re.match(r'^\(\d+\)\s+([A-Z\s]+)\s+\(', line)
            if match:
                train_name = match.group(1).strip()
                train_names.append(train_name)
    
    return train_names

def filter_route_for_common_trains(route_text, common_trains):
    """Filter route text to only include information about common trains"""
    filtered_lines = []
    include_section = False
    current_train = None
    
    # Get header lines (Date, From-To, URL)
    header_lines = []
    for line in route_text.split('\n')[:5]:
        if line.strip() and not line.startswith('('):
            header_lines.append(line)
    
    filtered_lines.extend(header_lines)
    filtered_lines.append("")  # Empty line after header
    
    # Process each line to filter for common trains
    for line in route_text.split('\n'):
        # Check if this is a train line (starts with a number in parentheses)
        if re.match(r'^\(\d+\)\s+', line):
            # Extract train name
            match = re.match(r'^\(\d+\)\s+([A-Z\s]+)\s+\(', line)
            if match:
                train_name = match.group(1).strip()
                # Check if this train is in the common trains list
                if train_name in common_trains:
                    include_section = True
                    current_train = train_name
                    filtered_lines.append(line)
                else:
                    include_section = False
        # If we're in a section for a common train, include seat details
        elif include_section and line.strip() and '    ' in line:
            filtered_lines.append(line)
        # Include empty line after a train's details to maintain formatting
        elif include_section and line.strip() == '':
            filtered_lines.append(line)
    
    return '\n'.join(filtered_lines)

def process_intermediate_routes(all_results_by_date, intermediate_routes, formatted_date):
    """Process intermediate routes using already retrieved data instead of making new requests"""
    intermediate_date_results = []
    
    # Get the direct route results for this date
    direct_results = {(r[0], r[1]): (r[3], r[4]) for r in all_results_by_date['results']}
    
    # For each intermediate route
    for idx, (src, mid, dst) in enumerate(intermediate_routes):
        # Try to find first leg (source to intermediate)
        first_result = direct_results.get((src, mid), (f"No data found for route {src} to {mid}", False))
        first_leg, first_has_seats = first_result
        
        # Try to find second leg (intermediate to destination)
        second_result = direct_results.get((mid, dst), (f"No data found for route {mid} to {dst}", False))
        second_leg, second_has_seats = second_result
        
        # Skip routes with no train or no available seats on at least one leg
        if not first_has_seats or not second_has_seats:
            print(f"Skipping intermediate route {idx+1}/{len(intermediate_routes)}: {src} -> {mid} -> {dst} (no train or seats available)")
            continue
        
        # Extract train names from both legs
        first_leg_trains = extract_train_names(first_leg)
        second_leg_trains = extract_train_names(second_leg)
        
        # Find common trains between the two legs
        common_trains = set(first_leg_trains).intersection(set(second_leg_trains))
        
        # Skip if there are no common trains
        if not common_trains:
            print(f"Skipping intermediate route {idx+1}/{len(intermediate_routes)}: {src} -> {mid} -> {dst} (no common trains)")
            continue
        
        # Filter the leg details to only include common trains
        filtered_first_leg = filter_route_for_common_trains(first_leg, common_trains)
        filtered_second_leg = filter_route_for_common_trains(second_leg, common_trains)
            
        # Combine the results of viable routes
        combined_output = f"\nINTERMEDIATE ROUTE: {src}-{mid}-{dst}\n"
        combined_output += f"Date: {formatted_date}\n"
        combined_output += f"Common trains: {', '.join(common_trains)}\n\n"
        combined_output += "FIRST LEG:\n==========\n" + filtered_first_leg + "\n\n"
        combined_output += "SECOND LEG:\n==========\n" + filtered_second_leg + "\n"
        
        # Add to results
        intermediate_date_results.append((src, dst, idx, combined_output, True))
        print(f"Processed intermediate route {idx+1}/{len(intermediate_routes)}: {src} -> {mid} -> {dst} (found {len(common_trains)} common trains)")
    
    return intermediate_date_results

if __name__ == "__main__":
    overall_start = time.time()
    
    # Show the welcome banner at the beginning
    print(f"\n{'.' * 116}\n{'.' * 40}|| _______  Find Tickets  _______ ||{'.' * 40}\n{'.' * 116}\n")
    
    # Use get_stations instead of directly reading stations.txt
    stations, selected_route_name = get_stations()
    
    # Ask for date selection before showing stations
    date_list = get_search_date()
    
    # Now display available stations
    print(f"\nAvailable stations:\n{'='*19}\n")
    for idx, station in enumerate(stations, 1):
        print(f"{idx}: {station}")
    print("")

    start_index = int(input("Enter starting station : ")) - 1
    end_index = int(input("Enter ending station : ")) - 1
    show_no_train_details = input("Include details for no trains/seats? (y/n): ").lower() == 'y'
    
    # Ask for intermediate routing input
    use_intermediate = input("Find routes with intermediate stations? (y/n): ").lower()
    intermediate_routes = []
    
    if use_intermediate == 'y':
        # Format: source_idx destination_idx range
        try:
            route_input = input("Enter { source, destination, range_length} in a single line (e.g., '4 15 2'): ")
            src, dst, range_val = map(int, route_input.split())
            
            # Adjust to 0-based indexing
            src_idx = src - 1
            dst_idx = dst - 1
            
            # Validate input values
            if 0 <= src_idx < len(stations) and 0 <= dst_idx < len(stations) and src_idx < dst_idx:
                intermediate_routes = find_intermediate_routes(stations, src_idx, dst_idx, range_val)
                print(f"Found {len(intermediate_routes)} possible intermediate routes")
            else:
                print("Invalid station indices. Using default values.")
                # Use first and last station in the selected range with default range=2
                src_idx = start_index
                dst_idx = end_index
                range_val = 2
                intermediate_routes = find_intermediate_routes(stations, src_idx, dst_idx, range_val)
                print(f"Using default intermediate route: {stations[src_idx]} to {stations[dst_idx]} with range {range_val}")
                print(f"Found {len(intermediate_routes)} possible intermediate routes")
        except ValueError:
            print("Invalid input format. Using default values.")
            # Use first and last station in the selected range with default range=2
            src_idx = start_index
            dst_idx = end_index
            range_val = 2
            intermediate_routes = find_intermediate_routes(stations, src_idx, dst_idx, range_val)
            print(f"Using default intermediate route: {stations[src_idx]} to {stations[dst_idx]} with range {range_val}")
            print(f"Found {len(intermediate_routes)} possible intermediate routes")
    else:
        # Use default values if user doesn't press 'y', but with range=0
        src_idx = start_index
        dst_idx = end_index
        range_val = 0  # Changed from 2 to 0 as requested
        intermediate_routes = find_intermediate_routes(stations, src_idx, dst_idx, range_val)
        print(f"Using default intermediate route: {stations[src_idx]} to {stations[dst_idx]} with range {range_val}")
        print(f"Found {len(intermediate_routes)} possible intermediate routes")
    
    print("\nProcessing routes...\n")

    station_combinations = []
    route_index = 0
    for i in range(len(stations)):
        # Reverse the inner loop to go from highest index to lowest
        for j in range(min(end_index, len(stations)-1), max(i, start_index-1), -1):
            if j > i:  # Ensure we're only creating combinations where j > i
                from_station = stations[i]
                to_station = stations[j]
                station_combinations.append((from_station, to_station, route_index))
                route_index += 1

    total_combinations = len(station_combinations) * len(date_list)
    
    # Dictionary to store results for all dates
    all_results_by_date = {}
    
    for date_str in date_list:
        # Reset counters for each date
        ROUTES_WITH_SEATS.value = 0
        ROUTES_WITHOUT_SEATS.value = 0
        
        formatted_date = convert_date_format(date_str)
        print(f"\nProcessing for date: {formatted_date}\n")
        
        batches = [station_combinations[i:i+BATCH_SIZE] for i in range(0, len(station_combinations), BATCH_SIZE)]
        completed_routes_counter = Value('i', 0)
        date_results = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(process_batch, batch, formatted_date, completed_routes_counter, len(station_combinations), show_no_train_details) for batch in batches]
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    batch_results = future.result()
                    date_results.extend(batch_results)
                except Exception as e:
                    print(f"Batch generated exception: {e}")

        date_results.sort(key=lambda x: x[2])
        all_results_by_date[date_str] = {
            'results': date_results,
            'with_seats': ROUTES_WITH_SEATS.value,
            'without_seats': ROUTES_WITHOUT_SEATS.value
        }
    
    # Process intermediate routes using already retrieved data
    intermediate_results = {}
    if intermediate_routes:
        print("\nProcessing intermediate routes using existing data...\n")
        
        for date_str in date_list:
            formatted_date = convert_date_format(date_str)
            print(f"\nProcessing intermediate routes for date: {formatted_date}")
            
            # Process intermediate routes using already retrieved data
            intermediate_date_results = process_intermediate_routes(
                all_results_by_date[date_str], 
                intermediate_routes, 
                formatted_date
            )
            
            intermediate_results[date_str] = intermediate_date_results
    
    # Calculate overall statistics
    total_routes_with_seats = sum(data['with_seats'] for data in all_results_by_date.values())
    total_routes_without_seats = sum(data['without_seats'] for data in all_results_by_date.values())
    total_no_train_routes = total_combinations - (total_routes_with_seats + total_routes_without_seats)
    total_time = time.time() - overall_start
    minutes = total_time / 60
    
    # Print summary once at the end
    print("\n\n\n------------------------------  Summary  ----------------------------------\n")
    print(f"Total routes processed: {total_combinations} (across {len(date_list)} date(s))")
    print(f"Routes with available seats: {total_routes_with_seats}/{total_combinations} ({total_routes_with_seats/total_combinations*100:.1f}%)")
    print(f"Routes without available seats: {total_routes_without_seats}/{total_combinations} ({total_routes_without_seats/total_combinations*100:.1f}%)")
    print(f"Routes with no train service: {total_no_train_routes}/{total_combinations} ({total_no_train_routes/total_combinations*100:.1f}%)")
    
    if intermediate_routes:
        print(f"Intermediate routes processed: {len(intermediate_routes)}")
    
    # Write to file
    with open('output.txt', 'w', encoding='utf-8') as output_file:
        output_file.write(f"\n{'.' * 84}\n{'.' * 24}|| _______ Md Babla Islam _______ ||{'.' * 24}\n{'.' * 84}\n\n\n\n")
        output_file.write(f"Summary: \n\n")
        output_file.write("Execution date and time             : " + datetime.now().strftime("%Y-%m-%d %I:%M:%S %p") + '\n')
        output_file.write(f"Selected Train Route                : {selected_route_name}\n")
        output_file.write(f"Selected station range (from-to)    : ({start_index+1}-{end_index+1}) ({stations[start_index]} ==> {stations[end_index]})\n")
        output_file.write(f"Journey Dates                       : {', '.join(convert_date_format(d) for d in date_list)}\n")
        output_file.write(f"Total number of routes/combinations : {total_combinations}\n")
        output_file.write(f"Total execution time                : {total_time:.2f} seconds ({minutes:.2f} minutes)\n")
        output_file.write(f"Average execution time per route    : {total_time/total_combinations:.2f} seconds\n")
        output_file.write(f"Routes with seats                   : {total_routes_with_seats}\nRoutes without seats                : {total_routes_without_seats}\nRoutes with no train service        : {total_no_train_routes}\n\n")
        
        # Add station list
        output_file.write("Station List:\n")
        for station in stations[start_index:end_index+1]:
            output_file.write(f"{station}\n")
        output_file.write("\n\n\n")
        
        # Write results for all dates
        for date_str in date_list:
            formatted_date = convert_date_format(date_str)
            output_file.write(f"{'=' * 84}\n")
            output_file.write(f"RESULTS FOR DATE: {formatted_date}\n")
            output_file.write(f"{'=' * 84}\n\n")
            
            for result in all_results_by_date[date_str]['results']:
                doubleEqualLine(output_file)
                output_file.write(result[3])
        
        # Write intermediate route results if any
        if intermediate_routes:
            output_file.write(f"\n\n{'=' * 84}\n")
            output_file.write(f"INTERMEDIATE ROUTE RESULTS\n")
            output_file.write(f"{'=' * 84}\n\n")
            
            for date_str in date_list:
                formatted_date = convert_date_format(date_str)
                output_file.write(f"{'=' * 84}\n")
                output_file.write(f"INTERMEDIATE ROUTES FOR DATE: {formatted_date}\n")
                output_file.write(f"{'=' * 84}\n\n")
                
                for result in intermediate_results[date_str]:
                    doubleEqualLine(output_file)
                    output_file.write(result[3])
                
        endExecution(output_file)

    print(f"\nTotal execution time: {total_time:.2f} seconds ({minutes:.2f} minutes) for {total_combinations} routes")
    print(f"Average execution time per route: {total_time/total_combinations:.2f}s")
    print("\n------------------------  Execution completed  ----------------------------\n")
    print("\nResults are saved in output.txt file.\n\n")
