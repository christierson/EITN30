import pandas as pd
import matplotlib.pyplot as plt

# Read the performance metrics from the CSV file
data = pd.read_csv('performance_metrics.csv')

# Plot bandwidth
def plot_bandwidth():
    plt.figure(figsize=(10, 6))
    plt.plot(data['Intended Size (bytes)'], data['Measured Bandwidth (bytes/sec)'], marker='o', linestyle='-', color='b', label='Measured Bandwidth')
    plt.title('Payload Size vs Measured Bandwidth')
    plt.xlabel('Payload Size (bytes)')
    plt.ylabel('Measured Bandwidth (bytes/sec)')
    plt.grid(True)
    plt.legend()
    plt.savefig('bandwidth_plot.png')
    plt.show()

# Plot latency
def plot_latency():
    plt.figure(figsize=(10, 6))
    plt.plot(data['Intended Size (bytes)'], data['Latency (s)'], marker='x', linestyle='--', color='r', label='Latency')
    plt.title('Payload Size vs Latency')
    plt.xlabel('Payload Size (bytes)')
    plt.ylabel('Latency (seconds)')
    plt.grid(True)
    plt.legend()
    plt.savefig('latency_plot.png')
    plt.show()

# Execute plotting functions
plot_bandwidth()
plot_latency()