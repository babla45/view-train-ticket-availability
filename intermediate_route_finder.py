import re
from datetime import datetime
import io

def doubleEqualLine(file):
    file.write('='*84 + '\n')

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
            # Add 4 spaces before the Date line to match the indentation of other lines
            if line.strip().startswith("Date"):
                header_lines.append("    " + line.strip())
            else:
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

def parse_output_file(file_path):
    """Parse the output.txt file to extract route information"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            
        # Extract the date
        date_match = re.search(r'Journey Dates\s+:\s+([^,\n]+)', content)
        if not date_match:
            print("Could not find date information in the output file.")
            return None
            
        formatted_date = date_match.group(1).strip()
        
        # Extract the selected train route from the summary section
        selected_route_match = re.search(r'Selected Train Route\s+:\s+(.+?)$', content, re.MULTILINE)
        selected_route = selected_route_match.group(1).strip() if selected_route_match else "Unknown"
        print(f"Found selected train route: {selected_route}")
        
        # Extract the selected station range
        station_range_match = re.search(r'Selected station range \(from-to\)\s+:\s+\((\d+)-(\d+)\) \(([^=]+) ==> ([^)]+)\)', content)
        selected_stations = None
        if station_range_match:
            start_idx = int(station_range_match.group(1))
            end_idx = int(station_range_match.group(2))
            start_station = station_range_match.group(3).strip()
            end_station = station_range_match.group(4).strip()
            selected_stations = {
                'start_idx': start_idx,
                'end_idx': end_idx,
                'start_station': start_station,
                'end_station': end_station
            }
            print(f"Found selected station range: {start_station} (#{start_idx}) to {end_station} (#{end_idx})")
        
        # Extract station list from the file
        stations = []
        station_list_match = re.search(r'Station List:(.*?)={84}', content, re.DOTALL)
        
        if station_list_match:
            station_list_text = station_list_match.group(1).strip()
            # Extract each station name from the list
            stations = [line.strip() for line in station_list_text.split('\n') if line.strip()]
        else:
            # If no station list found, try to read from stations.txt
            try:
                with open('stations.txt', 'r', encoding='utf-8') as stations_file:
                    stations = [line.strip() for line in stations_file.readlines() if line.strip()]
                print("Station list not found in output.txt, using stations.txt instead.")
            except FileNotFoundError:
                print("Warning: No station list found in output.txt and stations.txt not found.")
        
        # Extract route sections
        route_sections = []
        sections = re.split(r'={84}', content)
        
        for section in sections:
            # Look for sections with route information
            if "From-To" in section and "URL" in section:
                # Extract the route information
                from_to_match = re.search(r'From-To\s+:\s+([^-]+)-([^\n]+)', section)
                if from_to_match:
                    from_station = from_to_match.group(1).strip()
                    to_station = from_to_match.group(2).strip()
                    
                    # Check if this section has train information
                    has_trains = bool(re.search(r'\(\d+\)\s+[A-Z\s]+\s+\(', section))
                    
                    if has_trains:
                        route_sections.append({
                            'from': from_station,
                            'to': to_station,
                            'content': section.strip(),
                            'has_seats': True  # Assume it has seats if it has train information
                        })
        
        return {
            'date': formatted_date,
            'routes': route_sections,
            'stations': stations,
            'selected_route': selected_route,
            'selected_stations': selected_stations
        }
        
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return None
    except Exception as e:
        print(f"Error parsing output file: {str(e)}")
        return None

def find_intermediate_routes(routes, src_station, dst_station, range_val):
    """Find potential intermediate routes from the parsed route data with specified range"""
    intermediate_routes = []
    
    # Find source and destination stations in routes
    src_indices = [i for i, route in enumerate(routes) if route['from'] == src_station]
    dst_indices = [i for i, route in enumerate(routes) if route['to'] == dst_station]
    
    if not src_indices or not dst_indices:
        print(f"Source station '{src_station}' or destination station '{dst_station}' not found in routes")
        return []
    
    # Get all stations from the routes
    all_stations = set()
    for route in routes:
        all_stations.add(route['from'])
        all_stations.add(route['to'])
    
    all_stations = sorted(list(all_stations))
    
    # Find indices of source and destination in the sorted station list
    try:
        src_idx = all_stations.index(src_station)
        dst_idx = all_stations.index(dst_station)
    except ValueError:
        print(f"Could not find source or destination in station list")
        return []
    
    # Define source station range
    src_start = max(0, src_idx - range_val)
    src_end = min(len(all_stations) - 1, src_idx + range_val)
    
    # Define destination station range
    dst_start = max(0, dst_idx - range_val)
    dst_end = min(len(all_stations) - 1, dst_idx + range_val)
    
    # Define intermediate station range (all stations between source and destination)
    intermediate_start = min(src_idx, dst_idx) + 1
    intermediate_end = max(src_idx, dst_idx) - 1
    
    # If there are no valid intermediate stations
    if intermediate_start > intermediate_end:
        print("No intermediate stations found between source and destination")
        return []
    
    # Generate all possible routes through intermediate stations
    for i in range(src_start, src_end + 1):
        for j in range(dst_start, dst_end + 1):
            for k in range(intermediate_start, intermediate_end + 1):
                src = all_stations[i]
                dst = all_stations[j]
                mid = all_stations[k]
                
                # Find first leg (source to intermediate)
                first_leg = next((r for r in routes if r['from'] == src and r['to'] == mid), None)
                if not first_leg:
                    continue
                
                # Find second leg (intermediate to destination)
                second_leg = next((r for r in routes if r['from'] == mid and r['to'] == dst), None)
                if not second_leg:
                    continue
                
                # We've found a valid intermediate route
                intermediate_routes.append({
                    'src': src,
                    'mid': mid,
                    'dst': dst,
                    'first_leg': first_leg,
                    'second_leg': second_leg
                })
    
    return intermediate_routes

def extract_train_specific_stations(parsed_data):
    """
    Extract stations relevant to the selected train route
    based on the route ID and train name from the summary
    """
    selected_route = parsed_data.get('selected_route', '')
    
    # If no selected route or it's "Default station list", return all stations
    if not selected_route or selected_route == "Default station list":
        print("Using all available stations (no specific train route selected)")
        return parsed_data['stations']
    
    # Try to extract the train route information
    match = re.match(r'\((\d+)\)\s+(.+)', selected_route)
    if not match:
        print(f"Could not parse train route format: {selected_route}, using all available stations")
        return parsed_data['stations']
    
    route_number = match.group(1)
    train_name = match.group(2)
    print(f"Processing for train route #{route_number}: {train_name}")
    
    # Extract stations for this specific train route from stationList.txt
    try:
        with open('stationList.txt', 'r') as file:
            content = file.read()
            
            # Find the section for this train route
            # Look for patterns like "1. TRAIN_NAME" or similar
            pattern = rf"{route_number}\.\s+{re.escape(train_name)}"
            section_match = re.search(pattern, content)
            
            if not section_match:
                print(f"Could not find train route {route_number} in stationList.txt, using all available stations")
                return parsed_data['stations']
            
            # Find the start position of this section
            start_pos = section_match.start()
            
            # Find the next section start or end of file
            next_section_match = re.search(r'\n\d+\.', content[start_pos+1:])
            if next_section_match:
                end_pos = start_pos + 1 + next_section_match.start()
                section_text = content[start_pos:end_pos]
            else:
                section_text = content[start_pos:]
            
            # Extract station names from the section
            station_lines = section_text.split('\n')[1:]  # Skip the first line with the train name
            specific_stations = [line.strip() for line in station_lines if line.strip()]
            
            if not specific_stations:
                print(f"No stations found for train route {route_number}, using all available stations")
                return parsed_data['stations']
            
            print(f"Found {len(specific_stations)} stations specific to train route {route_number}")
            return specific_stations
            
    except FileNotFoundError:
        print("stationList.txt not found, using all available stations")
        return parsed_data['stations']
    except Exception as e:
        print(f"Error extracting train-specific stations: {str(e)}, using all available stations")
        return parsed_data['stations']

def process_intermediate_routes(parsed_data, src_station=None, dst_station=None, range_val=None):
    """Process intermediate routes from the parsed data"""
    if not parsed_data:
        return []
        
    routes = parsed_data['routes']
    formatted_date = parsed_data['date']
    
    # Get train-specific stations from stationList.txt if possible
    all_stations = extract_train_specific_stations(parsed_data)
    
    if not all_stations:
        # Fallback to extracting stations from routes if no station list was found
        all_stations = set()
        for route in routes:
            all_stations.add(route['from'])
            all_stations.add(route['to'])
        all_stations = sorted(list(all_stations))
    
    # Display the station range from output.txt if available
    if parsed_data.get('selected_stations'):
        sel_stations = parsed_data['selected_stations']
        print(f"\nSelected station range from output.txt: ({sel_stations['start_idx']}-{sel_stations['end_idx']}) ({sel_stations['start_station']} ==> {sel_stations['end_station']})")
    
    # Don't show the full station list again since we've already displayed the stations within the selected range
    # Just prompt the user directly
    try:
        src_idx = int(input("\nEnter source station number: ")) - 1
        dst_idx = int(input("Enter destination station number: ")) - 1
        
        if 0 <= src_idx < len(all_stations) and 0 <= dst_idx < len(all_stations):
            src_station = all_stations[src_idx]
            dst_station = all_stations[dst_idx]
            print(f"\nSelected route: {src_station} to {dst_station}")
        else:
            print("Invalid station indices")
            return []
    except ValueError:
        print("Invalid input")
        return []
    
    # Always ask for range value
    try:
        range_val = int(input("Enter range for intermediate routes (e.g., 2): "))
        if range_val < 0:
            print("Range must be positive")
            return []
    except ValueError:
        print("Invalid range value")
        return []
    
    print(f"\nFinding intermediate routes from {src_station} to {dst_station} with range {range_val}")
    
    # Find potential intermediate routes
    intermediate_routes = find_intermediate_routes(routes, src_station, dst_station, range_val)
    intermediate_results = []
    
    # Process each intermediate route
    for idx, route in enumerate(intermediate_routes, 1):
        src = route['src']
        mid = route['mid']
        dst = route['dst']
        first_leg = route['first_leg']
        second_leg = route['second_leg']
        
        # Skip routes where either leg doesn't have seats
        if not first_leg['has_seats'] or not second_leg['has_seats']:
            print(f"Skipping intermediate route {idx}/{len(intermediate_routes)}: {src} -> {mid} -> {dst} (no train or seats available)")
            continue
        
        # Extract train names from both legs
        first_leg_trains = extract_train_names(first_leg['content'])
        second_leg_trains = extract_train_names(second_leg['content'])
        
        # Find common trains between the two legs
        common_trains = set(first_leg_trains).intersection(set(second_leg_trains))
        
        # Skip if there are no common trains
        if not common_trains:
            print(f"Skipping intermediate route {idx}/{len(intermediate_routes)}: {src} -> {mid} -> {dst} (no common trains)")
            continue
        
        # Filter the leg details to only include common trains
        filtered_first_leg = filter_route_for_common_trains(first_leg['content'], common_trains)
        filtered_second_leg = filter_route_for_common_trains(second_leg['content'], common_trains)
        
        # Combine the results of viable routes
        combined_output = f"\nINTERMEDIATE ROUTE: {src} ==> {mid} ==> {dst}\n"
        combined_output += f"Date: {formatted_date}\n"
        combined_output += f"Common trains: {', '.join(common_trains)}\n\n"
        combined_output += "FIRST LEG:\n==========\n" + filtered_first_leg + "\n\n"
        combined_output += "SECOND LEG:\n==========\n" + filtered_second_leg + "\n"
        
        intermediate_results.append({
            'src': src,
            'mid': mid, 
            'dst': dst,
            'output': combined_output,
            'common_trains': common_trains
        })
        
        print(f"Processed intermediate route {idx}/{len(intermediate_routes)}: {src} -> {mid} -> {dst} (found {len(common_trains)} common trains)")
    
    return intermediate_results

def write_results(intermediate_results, output_file_path, parsed_data):
    """Write the intermediate route results to a file"""
    with open(output_file_path, 'w', encoding='utf-8') as file:
        # Write header
        file.write(f"\n{'.' * 84}\n{'.' * 24}|| _______ Intermediate Routes _______ ||{'.' * 24}\n{'.' * 84}\n\n\n\n")
        
        # Write summary
        file.write(f"Summary: \n\n")
        file.write("Execution date and time             : " + datetime.now().strftime("%Y-%m-%d %I:%M:%S %p") + '\n')
        file.write(f"Selected Train Route                : {parsed_data.get('selected_route', 'Unknown')}\n")
        
        # Add selected station range if available
        if parsed_data.get('selected_stations'):
            sel = parsed_data['selected_stations']
            file.write(f"Selected station range (from-to)    : ({sel['start_idx']}-{sel['end_idx']}) ({sel['start_station']} ==> {sel['end_station']})\n")
        
        file.write(f"Journey Date                        : {parsed_data['date']}\n")
        
        # Add station list to output
        if parsed_data.get('stations'):
            file.write("\nStation List:\n")
            train_specific_stations = extract_train_specific_stations(parsed_data)
            for station in train_specific_stations:
                file.write(f"{station}\n")
            file.write("\n")
            
        file.write(f"Total potential intermediate routes : {len(intermediate_results)}\n\n\n\n")
        
        # Write intermediate route results
        file.write(f"{'=' * 84}\n")
        file.write(f"INTERMEDIATE ROUTE RESULTS\n")
        file.write(f"{'=' * 84}\n\n")
        
        file.write(f"{'=' * 84}\n")
        file.write(f"INTERMEDIATE ROUTES FOR DATE: {parsed_data['date']}\n")
        file.write(f"{'=' * 84}\n\n")
        
        for result in intermediate_results:
            doubleEqualLine(file)
            file.write(result['output'])
        
        # Write footer
        file.write("\n\n")
        file.write('='*84 + '\n')
        file.write('|| ' + '~'*24 + ' ||   Finished Execution   || ' + '~'*24 + ' ||\n')
        file.write('='*84 + '\n')

def display_selected_station_range(parsed_data):
    """
    Display the stations from the selected train route that fall within the user's selected range
    """
    # Get the selected train route information
    selected_route = parsed_data.get('selected_route', '')
    if not selected_route:
        print("No train route selection found.")
        return
    
    # Get the selected station range
    selected_stations_info = parsed_data.get('selected_stations')
    if not selected_stations_info:
        print("No station range information found.")
        return
    
    # Extract route number and name
    match = re.match(r'\((\d+)\)\s+(.+)', selected_route)
    if not match:
        print(f"Could not parse train route format: {selected_route}")
        return
    
    route_number = match.group(1)
    train_name = match.group(2)
    
    # Get start and end indices
    start_idx = selected_stations_info['start_idx']
    end_idx = selected_stations_info['end_idx']
    
    # Get the full list of stations for this train route
    try:
        with open('stationList.txt', 'r') as file:
            content = file.read()
            
            # Find the section for this train route
            pattern = rf"{route_number}\.\s+{re.escape(train_name)}"
            section_match = re.search(pattern, content)
            
            if not section_match:
                print(f"Could not find train route {route_number} in stationList.txt")
                return
            
            # Find the start position of this section
            start_pos = section_match.start()
            
            # Find the next section start or end of file
            next_section_match = re.search(r'\n\d+\.', content[start_pos+1:])
            if next_section_match:
                end_pos = start_pos + 1 + next_section_match.start()
                section_text = content[start_pos:end_pos]
            else:
                section_text = content[start_pos:]
            
            # Extract station names from the section
            station_lines = section_text.split('\n')[1:]  # Skip the first line with the train name
            all_stations = [line.strip() for line in station_lines if line.strip()]
            
            if not all_stations:
                print(f"No stations found for train route {route_number}")
                return
            
            # Display only stations within the selected range
            print(f"\nSelected Train Route: {selected_route}")
            print(f"Stations within selected range ({start_idx}-{end_idx}):")
            print("="*60)
            print(" #  | Station Name")
            print("-"*60)
            
            # Display stations in the selected range
            for i, station in enumerate(all_stations, 1):
                if start_idx <= i <= end_idx:
                    print(f" {i:<3}| {station}")
            
            print("="*60)
            
    except FileNotFoundError:
        print("stationList.txt not found")
    except Exception as e:
        print(f"Error displaying train stations: {str(e)}")

def main():
    # Show welcome banner
    print(f"\n{'.' * 84}\n{'.' * 24}|| _______ Intermediate Routes _______ ||{'.' * 24}\n{'.' * 84}\n")
    
    input_file = 'output.txt'
    output_file = 'intermediate_routes.txt'
    
    print(f"Parsing {input_file} for route information...")
    parsed_data = parse_output_file(input_file)
    
    if not parsed_data:
        print("Failed to parse output file. Exiting.")
        return
    
    print(f"Found {len(parsed_data['routes'])} route sections for date: {parsed_data['date']}")
    
    if parsed_data['stations']:
        print(f"Found {len(parsed_data['stations'])} stations in the station list")
    else:
        print("No station list found in the output file")
    
    # Display the stations in the selected range
    display_selected_station_range(parsed_data)
        
    print("Processing intermediate routes...")
    
    # Get user input for source, destination, and range
    intermediate_results = process_intermediate_routes(parsed_data)
    
    if not intermediate_results:
        print("No viable intermediate routes found matching your criteria.")
        return
    
    print(f"Found {len(intermediate_results)} viable intermediate routes with common trains")
    
    write_results(intermediate_results, output_file, parsed_data)
    
    print(f"Results written to {output_file}")

if __name__ == "__main__":
    main()
