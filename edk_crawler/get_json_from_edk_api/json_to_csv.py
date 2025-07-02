import json
import csv
import time

# Function to clean and format the Markdown text for CSV
def clean_markdown(text):
    # Replace line breaks with a space
    text = text.replace('\n', ' ').replace('\r', '')
    # Enclose the text in double quotes to handle commas and other special characters
    return f'"{text}"'

# Function to convert JSON to CSV
def json_to_csv(json_file, csv_file):
    # Read the JSON data
    with open(json_file, 'r', encoding='utf-8') as f:
        job_data = json.load(f)

    # Check if job_data is not empty
    if not job_data:
        print("No job data found in the JSON file.")
        return

    # Get the keys from the first job entry to use as CSV headers
    headers = job_data[0].keys()

    # Write to CSV file
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        print(f"Start writing data from {json_file} to {csv_file}...")
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()  # Write the header
        
        # Clean and format each job entry before writing
        for job in job_data:
            # Clean the description and other fields as needed
            job['description'] = clean_markdown(job['description'])
            writer.writerow(job)  # Write the job data

    print(f"Data successfully written to {csv_file}")

# Specify the input JSON file and output CSV file
json_file = 'edk_job_1000.json'  # Change this to your JSON file path
csv_file = 'edk_jobs_1000.csv'      # Desired output CSV file name

# Call the function to convert JSON to CSV
start_time = time.time()
json_to_csv(json_file, csv_file)
end_time = time.time()

print(f"Programm did run for {(end_time - start_time):.6f} seconds")
