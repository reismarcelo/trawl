# Trawl - Capture CLI commands and search for configurable patterns

## Installation

Trawl requires Python 3.8 or newer. This can be verified by pasting the following to a terminal window:
```
% python3 -c "import sys;assert sys.version_info>(3,8)" && echo "ALL GOOD"
```

If 'ALL GOOD' is printed it means Python requirements are met. If not, download and install the latest 3.x version at Python.org (https://www.python.org/downloads/).

Go to the trawl directory and create a virtual environment
```
% cd trawl
% python3 -m venv venv
```

Activate the virtual environment:
```
% source venv/bin/activate
(venv) %
```
- Note that the prompt is updated with the virtual environment name (venv), indicating that the virtual environment is active.
    
Upgrade built-in virtual environment packages:
```
(venv) % pip install --upgrade pip setuptools
```

Install trawl:
```
(venv) % pip install --upgrade .
```

Validate that trawl is installed:
```
(venv) % trawl --version
Trawl Version 1.0
```

## Running

A yaml spec file is used to define target devices and commands to execute. There is an example of this file under examples/trawl_spec.yml.

You can use the -h (or --help) to navigate across the contextual help.
```
(venv) % trawl --help 
usage: trawl [-h] [--version] {apply,preview,schema} ...

Trawl - Capture cli commands and search for configurable patterns

options:
  -h, --help            show this help message and exit
  --version             show program's version number and exit

commands:
  {apply,preview,schema}
    apply               apply commands as per spec file
    preview             preview commands as per spec file
    schema              generate spec file JSON schema
    

(venv) % trawl apply -h 
usage: trawl apply [-h] [-u <user>] [-p <password>] [-f <filename>] [-s <filename>]

options:
  -h, --help            show this help message and exit
  -u <user>, --user <user>
                        username, can also be defined via TRAWL_USER environment variable. If neither is provided prompt for username.
  -p <password>, --password <password>
                        password, can also be defined via TRAWL_PASSWORD environment variable. If neither is provided prompt for password.
  -f <filename>, --file <filename>
                        spec file containing instructions to execute (default: trawl_spec.yml)
  -s <filename>, --save <filename>
                        save output from commands to file (default: output_20230213.txt)

```

The preview option can be used to validate all actions without connecting to any device:
```
(venv) % trawl preview
INFO: [Preview][r1] Starting session to 10.85.58.240
INFO: [Preview][r1] Sending 'show log'
INFO: [Preview][r1] Check command output for pattern '%PKT_INFRA-LINK'
INFO: [Preview][r1] Closed session
INFO: [Preview][r2] Starting session to 10.85.58.239
INFO: [Preview][r2] Sending 'show log'
INFO: [Preview][r2] Check command output for pattern '%PKT_INFRA-LINK'
INFO: [Preview][r2] Closed session
```

The apply option execute the instructions determined by the spec file:
```
(venv) % trawl apply   
Device username: cisco
Device password: 
INFO: [r1] Starting session to 10.85.58.240
INFO: Connected (version 2.0, client Cisco-2.0)
INFO: Authentication (password) successful!
INFO: [r1] Sending 'show log'
INFO: [r1] Pattern '%PKT_INFRA-LINK' did not match
INFO: [r1] Closed session
INFO: [r2] Starting session to 10.85.58.239
INFO: Connected (version 2.0, client Cisco-2.0)
INFO: Authentication (password) successful!
INFO: [r2] Sending 'show log'
INFO: [r2] Pattern '%PKT_INFRA-LINK' matched 317 times, first match: %PKT_INFRA-LINK
INFO: [r2] Closed session
WARNING: Pattern matches found in the output from r2
INFO: Saved output from commands to 'output_20230213.txt'
```

The schema option generates a JSON schema describing all options available in the spec file:
```
(venv) % trawl schema
INFO: Saved spec file schema as 'spec_file_schema.json'
```
