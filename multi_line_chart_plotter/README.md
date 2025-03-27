# Goal

This script plots the given CSV files in a multi-line chart. 
The files should be in the following format:

```
<one line header>
x point, y point
x point, y point
x point, y point
```

# Usage

```
pip install -r requirements.txt
./plotter.py <file> <title> <x label> <y label> <output file>
```
for example:

```shell
./plotter.py cpu_usage1.csv cpu_usage2.csv "CPU Usage Over Time" "Time (s)" "CPU Usage (%)" cpu_usage.png
```

or

```shell
./plotter.py ram_usage1.csv ram_usage2.csv "RAM Usage Over Time" "Time (s)" "RAM Usage (MB)" ram_usage.png
```
