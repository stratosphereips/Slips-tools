import csv
import time
import subprocess
import re

def get_rpi_temperature():
    try:
        # Run vcgencmd to get temperature
        temp_output = subprocess.check_output(['vcgencmd', 'measure_temp']).decode()
        # Extract temperature value using regex
        temp = float(re.search(r'temp=([\d\.]+)', temp_output).group(1))
        return temp
    except Exception as e:
        print(f"Error reading temperature: {e}")
        return None

def log_temperature():
    # Open CSV file in append mode
    with open('rpi_temperature_log.csv', 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        # Write header if file is empty
        if csvfile.tell() == 0:
            writer.writerow(['Time Elapsed (Minutes)', 'Temperature (Celsius)'])
        
        start_time = time.time()
        
        while True:
            # Calculate elapsed time in minutes
            elapsed_minutes = (time.time() - start_time) / 60.0
            # Get current temperature
            temperature = get_rpi_temperature()
            
            if temperature is not None:
                # Write to CSV
                writer.writerow([f"{elapsed_minutes:.2f}", f"{temperature:.2f}"])
                csvfile.flush()  # Ensure data is written immediately
                print(f"Logged: {elapsed_minutes:.2f} minutes, {temperature:.2f}°C")
            
            # Wait for 5 minutes (300 seconds)
            time.sleep(300)

if __name__ == "__main__":
    try:
        log_temperature()
    except KeyboardInterrupt:
        print("\nLogging stopped by user")
