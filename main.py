import socket
import argparse
import logging
import os
import struct
import sys
import time
from typing import Optional

ICMP_ECHO_REQUEST = 8
ICMP_ECHO_REPLY = 0
ICMP_PAYLOAD = b"net-ping"


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


def icmp_checksum(data: bytes) -> int:
    """Computes the Internet checksum over data, per RFC 1071."""
    if len(data) % 2:
        data += b'\x00'
    total = sum(struct.unpack('!%dH' % (len(data) // 2), data))
    total = (total >> 16) + (total & 0xFFFF)
    total += total >> 16
    return (~total) & 0xFFFF


def build_echo_request(identifier: int, sequence: int) -> bytes:
    """Builds an ICMP echo request packet (type 8) with a valid checksum."""
    header = struct.pack('!BBHHH', ICMP_ECHO_REQUEST, 0, 0, identifier, sequence)
    checksum = icmp_checksum(header + ICMP_PAYLOAD)
    header = struct.pack('!BBHHH', ICMP_ECHO_REQUEST, 0, checksum, identifier, sequence)
    return header + ICMP_PAYLOAD


def parse_echo_reply(packet: bytes, identifier: int, sequence: int) -> bool:
    """Returns True when packet is an ICMP echo reply matching identifier and sequence."""
    if not packet:
        return False
    ip_header_len = (packet[0] & 0x0F) * 4
    if ip_header_len < 20 or len(packet) < ip_header_len + 8:
        return False
    icmp_packet = packet[ip_header_len:]
    reply_type, _code, _checksum, reply_id, reply_seq = struct.unpack('!BBHHH', icmp_packet[:8])
    return reply_type == ICMP_ECHO_REPLY and reply_id == identifier and reply_seq == sequence


def send_ping(host: str, timeout: int, sequence: int = 1) -> Optional[float]:
    """
    Sends a single ICMP echo request to the specified host and times the reply.

    Args:
        host (str): The hostname or IP address to ping.
        timeout (int): Timeout in seconds for the request.
        sequence (int): Sequence number for this echo request.

    Returns:
        Optional[float]: Response time in milliseconds, or None if no matching
        echo reply arrives before the timeout.

    Raises:
        PermissionError: When the process may not open a raw ICMP socket.
    """
    # The name is resolved again on every call, so a run of four pings
    # does four lookups and could in principle hit different addresses
    # if the name rotates. The identifier stays the pid for all of them;
    # the sequence number is what tells my replies apart.
    target_ip = socket.gethostbyname(host)
    identifier = os.getpid() & 0xFFFF
    packet = build_echo_request(identifier, sequence)
    with socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP) as sock:
        sock.settimeout(timeout)
        start_time = time.time()
        sock.sendto(packet, (target_ip, 0))
        # Packets that are not my reply are dropped and the wait goes
        # on against the original deadline. I recompute the remaining
        # time each round instead of giving each recv a fresh timeout,
        # so unrelated ICMP traffic cannot stretch one ping past the
        # timeout the user asked for.
        while True:
            remaining = timeout - (time.time() - start_time)
            if remaining <= 0:
                raise socket.timeout('timed out')
            sock.settimeout(remaining)
            data, _addr = sock.recvfrom(2048)
            if parse_echo_reply(data, identifier, sequence):
                end_time = time.time()
                return (end_time - start_time) * 1000


def main():
    """
    Main function to execute the net-ping tool.
    """
    parser = setup_argparse()
    args = parser.parse_args()

    handlers = [logging.StreamHandler()]
    if args.log:
        handlers.append(logging.FileHandler(args.log))
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=handlers, force=True)

    logging.info(f'Starting ping to {args.host} with {args.count} requests and {args.timeout}s timeout.')

    successful_pings = 0
    total_time = 0

    # There is no pause between pings. Each one starts as soon as the
    # previous reply or timeout lands, so a fast host gets the whole
    # count back to back instead of one per second like system ping.
    for i in range(args.count):
        logging.info(f'Sending ping {i + 1} to {args.host}...')
        try:
            response_time = send_ping(args.host, args.timeout, sequence=i + 1)
        except PermissionError:
            logging.error('net-ping needs raw socket access to send ICMP echo requests: run as root or grant the CAP_NET_RAW capability.')
            sys.exit(1)
        except socket.gaierror:
            logging.error(f'Failed to resolve host: {args.host}')
            sys.exit(1)
        except socket.timeout:
            logging.warning(f'Ping to {args.host} timed out.')
            response_time = None
        except Exception as e:
            logging.error(f'An error occurred during ping: {e}')
            response_time = None

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
        logging.error(f'Ping failed: no responses received from {args.host}.')
        sys.exit(1)


if __name__ == '__main__':
    main()
