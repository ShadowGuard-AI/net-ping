import socket
import argparse
import logging
import time
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def setup_argparse():
    """
    Sets up the argument parser for the command-line interface.

    Returns:
        argparse.ArgumentParser: Configured argument parser.
    """
    parser = argparse.ArgumentParser(
        description='net-ping: Sends ICMP echo requests to a given host and reports response times.'
    )
    parser.add_argument(
        'host',
        type=str,
        help='The hostname or IP address of the target to ping.'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=1,
        help='Timeout in seconds for each ping (default: 1 second).'
    )
    parser.add_argument(
        '--count',
        type=int,
        default=4,
        help='Number of ICMP echo requests to send (default: 4).'
    )
    parser.add_argument(
        '--log',
        type=str,
        default=None,
        help='Optional log file to save the output.'
    )
    return parser

def send_ping(host: str, timeout: int) -> Optional[float]:
    """
    Sends a single ICMP echo request to the specified host.

    Args:
        host (str): The hostname or IP address to ping.
        timeout (int): Timeout in seconds for the request.

    Returns:
        Optional[float]: Response time in milliseconds, or None if the request times out.
    """
    try:
        # Resolve the host address
        target_ip = socket.gethostbyname(host)
        logging.debug(f'Resolved {host} to {target_ip}')
        
        # Create a socket
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            message = b'ping'
            start_time = time.time()
            sock.sendto(message, (target_ip, 1))
            sock.recvfrom(1024)
            end_time = time.time()
        
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
        return response_time
    except socket.gaierror:
        logging.error(f'Failed to resolve host: {host}')
        return None
    except socket.timeout:
        logging.warning(f'Ping to {host} timed out.')
        return None
    except Exception as e:
        logging.error(f'An error occurred during ping: {e}')
        return None

def main():
    """
    Main function to execute the net-ping tool.
    """
    parser = setup_argparse()
    args = parser.parse_args()

    if args.log:
        logging.basicConfig(filename=args.log, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    logging.info(f'Starting ping to {args.host} with {args.count} requests and {args.timeout}s timeout.')

    successful_pings = 0
    total_time = 0

    for i in range(args.count):
        logging.info(f'Sending ping {i + 1} to {args.host}...')
        response_time = send_ping(args.host, args.timeout)

        if response_time is not None:
            logging.info(f'Ping {i + 1}: Response time = {response_time:.2f} ms')
            successful_pings += 1
            total_time += response_time
        else:
            logging.info(f'Ping {i + 1}: No response.')

    if successful_pings > 0:
        average_time = total_time / successful_pings
        logging.info(f'Ping statistics for {args.host}:')
        logging.info(f'  Packets: Sent = {args.count}, Received = {successful_pings}, Lost = {args.count - successful_pings}')
        logging.info(f'  Average response time = {average_time:.2f} ms')
    else:
        logging.info(f'No responses received from {args.host}.')

if __name__ == '__main__':
    main()