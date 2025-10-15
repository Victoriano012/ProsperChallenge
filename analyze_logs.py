import re
from collections import defaultdict
import statistics
from datetime import datetime


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


def analyze_log_blocks(log_file_path="logs.log"):
    """
    Analyzes log blocks from 'End of Turn' to 'Bot started speaking'
    and prints detailed metrics for each block.

    Args:
        log_file_path (str): The path to the log file.
    """
    # Regex to capture timestamps and specific log events
    log_line_pattern = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})")
    start_block_pattern = re.compile(r"End of Turn result: EndOfTurnState\.COMPLETE")
    end_block_pattern = re.compile(r"Bot started speaking")
    ttfb_pattern = re.compile(r"(\w+#\d+)\s+TTFB:\s+([\d.-]+)")
    processing_time_pattern = re.compile(r"(\w+#\d+)\s+processing time:\s+([\d.-]+)")

    in_block = False
    block_count = 0
    current_block = {}

    print("\n🔎 Block-by-Block Analysis 🔎")
    print("=" * 50)

    try:
        with open(log_file_path, "r") as f:
            for line in f:
                time_match = log_line_pattern.match(line)
                if not time_match:
                    continue

                timestamp_str = time_match.group(1)
                timestamp = datetime.fromisoformat(timestamp_str)

                # --- Start of a new block ---
                if start_block_pattern.search(line) and not in_block:
                    in_block = True
                    block_count += 1
                    current_block = {
                        "start_time": timestamp,
                        "metrics": [],
                    }

                # --- Inside a block, collect metrics ---
                if in_block:
                    ttfb_match = ttfb_pattern.search(line)
                    if ttfb_match:
                        service, value = ttfb_match.groups()
                        current_block["metrics"].append(("TTFB", service, float(value)))

                    processing_time_match = processing_time_pattern.search(line)
                    if processing_time_match:
                        service, value = processing_time_match.groups()
                        current_block["metrics"].append(
                            ("processing_time", service, float(value))
                        )
                else:
                    ttfb_match = ttfb_pattern.search(line)
                    if ttfb_match:
                        service, value = ttfb_match.groups()
                        print(f"    - {service:<22} TTFB: {value}s")

                    processing_time_match = processing_time_pattern.search(line)
                    if processing_time_match:
                        service, value = processing_time_match.groups()
                        print(f"    - {service:<22} processing time: {value}s")

                # --- End of the block ---
                if end_block_pattern.search(line) and in_block:
                    in_block = False
                    current_block["end_time"] = timestamp

                    # --- Print summary for the completed block ---
                    print(f"\n--- Block #{block_count} ---")

                    # Calculate total time and sums
                    total_duration = (
                        current_block["end_time"] - current_block["start_time"]
                    ).total_seconds()
                    sum_ttfb = sum(
                        v
                        for m, s, v in current_block["metrics"]
                        if m == "TTFB" and v > 0
                    )
                    sum_processing = sum(
                        v
                        for m, s, v in current_block["metrics"]
                        if m == "processing_time" and v > 0
                    )

                    print(f"  Total Block Time: {total_duration:.4f}s")
                    print(f"  Sum of TTFB:      {sum_ttfb:.4f}s")
                    print(f"  Sum of Proc Time: {sum_processing:.4f}s")
                    print("  Individual Metrics:")

                    if not current_block["metrics"]:
                        print("    No metrics found in this block.")
                    else:
                        for metric_name, service, value in current_block["metrics"]:
                            # Ignore negative TTFB values which can appear due to timing artifacts
                            if metric_name == "TTFB" and value < 0:
                                continue
                            print(
                                f"    - {service:<22} {metric_name:<15}: {value:.4f}s"
                            )

                    current_block = {}  # Reset for next block
                    print()

    except FileNotFoundError:
        print(f"Error: Log file not found at '{log_file_path}'")
        return

    print("\n" + "=" * 50)


if __name__ == "__main__":
    log_metrics = parse_log_metrics()
    if log_metrics:
        print_metrics_summary(log_metrics)

    analyze_log_blocks()
