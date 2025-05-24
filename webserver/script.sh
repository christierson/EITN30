#!/bin/bash

# File to save the metrics
OUTPUT_FILE="performance_metrics.csv"
PYTHON_SCRIPT="plot_performance.py"
VENV_DIR="venv"

# Write the header to the CSV file
echo "Intended Size (bytes),DNS Lookup (s),Connect (s),Start Transfer (s),Total Time (s),Size Downloaded (bytes),Measured Bandwidth (bytes/sec),Latency (s)" > $OUTPUT_FILE

# Range of sizes to test
START_SIZE=100
END_SIZE=1000
STEP_SIZE=100

# Function to make the request and save the metrics
measure_performance() {
    SIZE=$1
    METRICS=$(curl -o /dev/null -s -w \
        "%{time_namelookup},%{time_connect},%{time_starttransfer},%{time_total},%{size_download}\n" \
        http://localhost:8080/$SIZE)
    
    # Extract individual metrics
    DNS_LOOKUP=$(echo $METRICS | cut -d ',' -f 1)
    CONNECT=$(echo $METRICS | cut -d ',' -f 2)
    START_TRANSFER=$(echo $METRICS | cut -d ',' -f 3)
    TOTAL_TIME=$(echo $METRICS | cut -d ',' -f 4)
    SIZE_DOWNLOADED=$(echo $METRICS | cut -d ',' -f 5)
    
    # Calculate measured bandwidth
    if (( $(echo "$TOTAL_TIME > 0" | bc -l) )); then
        MEASURED_BANDWIDTH=$(echo "$SIZE_DOWNLOADED / $TOTAL_TIME" | bc -l)
    else
        MEASURED_BANDWIDTH=0
    fi

    # Calculate latency (time from connect to start transfer)
    LATENCY=$(echo "$START_TRANSFER - $CONNECT" | bc -l)

    # Append metrics to the CSV file
    echo "$SIZE,$DNS_LOOKUP,$CONNECT,$START_TRANSFER,$TOTAL_TIME,$SIZE_DOWNLOADED,$MEASURED_BANDWIDTH,$LATENCY" >> $OUTPUT_FILE
}

# Sweep over the range of sizes
for (( SIZE=$START_SIZE; SIZE<=$END_SIZE; SIZE+=$STEP_SIZE )); do
    measure_performance $SIZE
done

echo "Performance metrics saved to $OUTPUT_FILE"

# Create a virtual environment
python3 -m venv $VENV_DIR

# Activate the virtual environment
source $VENV_DIR/bin/activate

# Install required Python packages
pip install matplotlib pandas

# Run the Python script to generate the plot
python $PYTHON_SCRIPT

# Deactivate the virtual environment
deactivate

echo "Plot generated and saved as performance_plot.png"