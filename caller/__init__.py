
from os import pathsep, write
from posixpath import split


def read_and_call(file_name, outputdir, write_depths, write_mins):
    """Takes a depth file and calculates where peaks are within that file

    Args:
        file_name (String): The name of the depth file
        outputdir (String): The directory to output to
        write_depths (Bool): Wheather to write the compressed depth file to file or not
    """
    depths = {}
    chromosome = "null"
    output_file = open(outputdir + "/" + "tanoa_called_peaks.peaks", 'w')
    if write_depths or write_mins:
        if write_depths:
            compressed_depths_output = open(outputdir + "/" + "compressed_depths.depths", 'w')
        else:
            compressed_depths_output = "null"
        if write_mins:
            min_output = open(outputdir + "/" + "tanoa_called_mins.minimums", 'w')
        else:
            min_output = "null"
    else:
        compressed_depths_output = "null"
        min_output = "null"

    with open(file_name, "r") as file:
        for line in file:
            line.strip()
            split_line = line.split()
            ch = split_line[0].strip()
            if chromosome == "null":
                chromosome = ch
                print("Reading in ", ch)
            if chromosome == ch: #Standard chromosome check to run software 1 ch at a time
                depths[split_line[1].strip()] = split_line[2].strip()
            else:
                #do processing here
                print("Compressing " + chromosome)
                compressed_depths = compress(depths) #Compress the depths to make later algorithms work better
                depths = {}                           #and faster
                prossess_and_write_peaks(chromosome, compressed_depths, output_file, write_depths, compressed_depths_output, write_mins, min_output)
                #####
                print("Reading in ", ch)
                chromosome = ch
                depths[split_line[1]] = split_line[2]
        print("Compressing " + chromosome)
        compressed_depths = compress(depths) #Compress the depths to make later algorithms work better
        depths = {} 
        prossess_and_write_peaks(chromosome, depths, output_file, write_depths, compressed_depths_output, write_mins, min_output)
        #This gets the last chromosome in the file 

    output_file.close
    if write_depths:
        compressed_depths_output.close

def prossess_and_write_peaks(chromosome, compressed_depths, output_file, write_depths, compressed_depths_output, write_mins, min_output):
    print("Calling peaks")
    peak_list = call_peaks(compressed_depths) #calls peaks 
    peak_list = clean_peaks(peak_list)
    write_peaks_to_file(peak_list, output_file, chromosome) #writes them
    if write_depths:
        write_depths_to_file(compressed_depths_output, chromosome, compressed_depths)
    if write_mins:
        min_list = call_troughs(compressed_depths)
        write_peaks_to_file(min_list, min_output, chromosome)
    print("Peaks in " + chromosome + " called and written to file")

def compress(depths):
    """Compress takes a depth file and compresses the depths into "steps": The zones of consistent depth 
    registered as one singular depth for the sake of finding peaks

    Args:
        depths (dictionary): The origional Depth file

    Returns:
        dictionary: The dictionary of compressed depth files
    """
    depths_compressed = {}
    keys = list(depths.keys())
    start_key = keys[0]
    start = depths[keys[0]]
    jump = False

    for index, key in enumerate(keys):
        end = depths[key]
        if index > 0:
            int_prev = int(keys[index - 1])
            int_end = int(key)
            if int_end - int_prev != 1:
                jump = True
        if start != end or jump:
            key_out =  str(start_key) + "-" + str(key) 
            depths_compressed[key_out] = start
            start = end
            start_key = key
            jump = False

    return depths_compressed

def clean_peaks(peak_list):
    new_peaks = []
    for index, peak in enumerate(peak_list):
        split_peak = peak.split("-")
        start = split_peak[0]
        end = split_peak[1]
        if index != len(peak_list) - 1:
            next_peak_split = peak_list[index + 1].split("-")
            start_next = next_peak_split[0]
            end_next = next_peak_split[1]
            if int(start_next) - int(end) <= 150:
                new_peak = start + "-" + end_next
                new_peaks.append(new_peak)
            else:
                if len(new_peaks) != 0:
                    last_peak = new_peaks[-1]
                    last_split = last_peak.split("-")
                    last_end = last_split[1]
                    if int(end) != int(last_end):
                        new_peaks.append(peak)
                else:
                    new_peaks.append(peak)
    return new_peaks

def write_peaks_to_file(peaks, output_file, chromosome):
    """Wries a given list of peaks to file

    Args:
        peaks ([type]): [description]
        output_file ([type]): [description]
        chromosome ([type]): [description]
    """
    for peak in peaks:
        split_peak = peak.split("-")
        begin_peak = split_peak[0]
        end_peak = split_peak[1]
        output_file.write(chromosome + " " + begin_peak + " " + end_peak + "\n")

def write_depths_to_file(output, chromosome, compressed_depths):
    """Wries depths to file if the Write_Depths field was set to True

    Args:
        output (File): The file object which is used to write to file
        chromosome (String): The name of the chromosome who's depths are being added to the file
        compressed_depths (Dictionary): A dictionary of compressed depths in location: depth format
    """
    keys = list(compressed_depths.keys())
    for key in keys:
        split_keys = key.split("-")
        output.write(chromosome + " " + split_keys[0] + " " + split_keys[1] + " " + compressed_depths[key] + "\n")
        

def call_peaks(compressed_depths):
    """Searches for and adds found peaks to a list

    Args:
        compressed_depths (Dictionary): A dictionary of compressed depths in location: depth format

    Returns:
        [List]: A list of found peaks
    """
    keys = list(compressed_depths.keys())
    peak_list = []
    prev_depth = 0
    for index, key in enumerate(keys):
        current_depth = int(compressed_depths[key])
        if current_depth > prev_depth: #Finds locations where the slope is positive...
            is_max = verify_max(compressed_depths, keys, 3, keys[index], index)
            if is_max: #Checks those for being a maximum. What if I did no checking?
                peak_list.append(keys[index])
        prev_depth = current_depth
    return peak_list
    
def verify_max(compressed_depths, keys, steps, peak_key, key_index):
    """Given a peak, checks if it is a local maximum

    Args:
        compressed_depths (Dictionary): A dictionary of compressed depths in location: depth format
        keys (List): The keys for the compressed depths dictionary
        steps (int): How many steps left and write will be searched to verify a local maximum
        peak_key (string): The key to the given peak being checked
        key_index (int): The index in the keys list of the peak_key key

    Returns:
        [boolean]: A true or false statement to if the given point is a maximum or not
    """
    window_keys = generate_window(keys, key_index, steps)
    return check_max(window_keys, compressed_depths, peak_key)

def check_max(window_keys, compressed_depths, peak_key):
    """Given a list of keys, verifies that the given point(peak_key) corrisponds with the maximum
    value present in depths which those keys corrispond to

    Args:
        window_keys (List): A list of keys x steps away from a given peak
        compressed_depths (Dictionary): A dictionary of compressed depths in location: depth format
        peak_key (string): The key to the given peak being checked

    Returns:
        [bool]: A value which verifies if the given point of interest is a maximum or not
    """
    potential_max = int(compressed_depths[peak_key])
    is_max = True

    if potential_max <= 3:
        return False

    max_equals = 0

    for key in window_keys:
        key_depth = int(compressed_depths[key])
        if key_depth > potential_max:
            is_max = False
        elif key_depth == potential_max:
            max_equals += 1
    if max_equals >= 2:
        key_depth = False

    return is_max

def call_troughs(compressed_depths):
    keys = list(compressed_depths.keys())
    trough_list = []
    prev_depth = 0
    for index, key in enumerate(keys):
        current_depth = int(compressed_depths[key])
        if current_depth < prev_depth: #Finds locations where the slope is negative
            is_min = verify_min(compressed_depths, keys, 3, keys[index], index)
            if is_min: #Checks those for being a minimum. This is just the max algo flipped
                trough_list.append(keys[index])
        prev_depth = current_depth
    return trough_list

def verify_min(compressed_depths, keys, steps, peak_key, key_index):
    window_keys = generate_window(keys, key_index, steps)
    return check_min(window_keys, compressed_depths, peak_key)

def check_min(window_keys, compressed_depths, peak_key):
    potential_min = int(compressed_depths[peak_key])
    is_min = True
    for key in window_keys:
        key_depth = int(compressed_depths[key])
        if key_depth < potential_min:
            is_min = False
    return is_min
    
def generate_window(keys, key_index, steps):
    """Generates a list (window) steps distance t the left and right of a given peak 

    Args:
        keys (List): The keys for the compressed depths dictionary
        key_index (int): The index in the keys list of the peak_key key
        steps (int): How many steps left and write will be searched to verify a local maximum

    Returns:
        [list]: A list of keys that includes all keys steps away from a given location
    """
    window_keys = []
    for x in range(1, steps):
        if key_index - x >= 0:
            window_keys.append(keys[key_index - x])
    for x in range(1, steps):
        if key_index + x < len(keys):
            window_keys.append(keys[key_index + x])
    return window_keys
