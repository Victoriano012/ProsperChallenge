import re
from collections import defaultdict
import statistics


def parse_log_metrics(log_file_path="logs.log"):
    """
    Parses a log file to extract and calculate timing metrics for different services.

    Args:
        log_file_path (str): The path to the log file.

    Returns:
        dict: A dictionary containing the parsed metrics.
    """
    # Regex to capture service name and metric value from log lines
    ttfb_pattern = re.compile(r"(\w+#\d+)\s+TTFB:\s+([\d.]+)")
    processing_time_pattern = re.compile(r"(\w+#\d+)\s+processing time:\s+([\d.]+)")

    metrics = defaultdict(lambda: defaultdict(list))

    try:
        with open(log_file_path, "r") as f:
            for line in f:
                ttfb_match = ttfb_pattern.search(line)
                if ttfb_match:
                    service, value = ttfb_match.groups()
                    metrics[service]["TTFB"].append(float(value))

                processing_time_match = processing_time_pattern.search(line)
                if processing_time_match:
                    service, value = processing_time_match.groups()
                    metrics[service]["processing_time"].append(float(value))
    except FileNotFoundError:
        print(f"Error: Log file not found at '{log_file_path}'")
        return None

    return metrics


def print_metrics_summary(metrics):
    """
    Prints a formatted summary of the collected metrics.

    Args:
        metrics (dict): The metrics dictionary from parse_log_metrics.
    """
    if not metrics:
        print("No metrics found in the log file.")
        return

    print("📊 Log Metrics Summary 📊")
    print("=" * 50)

    for service, service_metrics in sorted(metrics.items()):
        print(f"\nService: {service}")
        print("-" * 30)
        for metric_name, values in sorted(service_metrics.items()):
            if values:
                print(f"  Metric: {metric_name}")
                print(f"    Count: {len(values)}")
                print(f"    Total: {sum(values):.4f}s")
                print(f"    Avg:   {statistics.mean(values):.4f}s")
                print(f"    Min:   {min(values):.4f}s")
                print(f"    Max:   {max(values):.4f}s")
    print("\n" + "=" * 50)


if __name__ == "__main__":
    log_metrics = parse_log_metrics()
    if log_metrics:
        print_metrics_summary(log_metrics)
