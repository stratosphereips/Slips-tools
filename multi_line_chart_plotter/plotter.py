#!python

import sys
import pandas as pd
import matplotlib.pyplot as plt

def plot_csv(files, title, x_label, y_label, output_file):
    plt.figure(figsize=(10, 5))
    
    for file in files:
        df = pd.read_csv(file, skiprows=1, header=None)
        
        if df.shape[1] < 2:
            print(f"Error: CSV file {file} must have at least two columns.")
            sys.exit(1)
        
        x = df.iloc[:, 0]
        y = df.iloc[:, 1]
        
        plt.plot(x, y, label=f"{file}")
    
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.title(title)
    plt.legend()
    plt.grid()
    
    plt.savefig(output_file)
    print(f"Plot saved as {output_file}")
    plt.show()

if __name__ == "__main__":
    if len(sys.argv) < 6:
        print("Usage: ./plotter.py <file1> [<file2> ...] <title> <x label> <y label> <output file>")
        sys.exit(1)
    
    *files, title, x_label, y_label, output_file = sys.argv[1:]
    plot_csv(files, title, x_label, y_label, output_file)
