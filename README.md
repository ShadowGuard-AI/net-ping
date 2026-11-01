```markdown
# net-ping
Sends ICMP echo requests to a given host and reports response times. - Focused on Basic network operations

## Install
`git clone https://github.com/ShadowStrikeHQ/net-ping`

## Usage
`./net-ping [params]`

## Parameters
- `-h`: Host to ping
- `-c`: Number of pings
- `--log`: Optional log file; the run's lines are written to the named file as well as the console

## Notes
- Sending ICMP echo requests needs raw socket access: run as root or grant the CAP_NET_RAW capability. Without that access the tool prints a line naming the privilege it needs and exits 1.
- A run that receives replies exits 0. A run with no responses, or a host that cannot be resolved, prints a failure line and exits 1.
- No third-party packages are required: the tool uses only the Python standard library.

## License
Copyright (c) CY83R-3X71NC710N
```