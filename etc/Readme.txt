CONTENTS OF THIS FILE
-----------------------------

* Introduction
* Requirements 
* Installation
* Usage
* Change logs
* FAQ

INTRODUCTION
------------
Neutron ML2 driver configuration generator for Lenovo switches version 1.0
 
This utility helps users generate Neutron ML2 plugin configuration for Lenovo switches.
It takes the definition of switches' IP address, connections, management protocols (NETCONF, SNMP), login credentials from a Yaml file and
generate ML2 plugin configuration block for all defined switches.

REQUIREMENTS
------------
Python >=2.7 or Python 3.x
The utility reads Lenovo switches' configuration from a Yaml data file so make sure you have Yaml parser for Python installed in your system.
You can install PyYaml from https://pypi.python.org/pypi/PyYAML or http://pyyaml.org

INSTALLATION
------------
No installation needed.

USAGE
-----
**** Show the utility built-in help page **** 
$ python3 neutronML2Gen.py -h
usage: neutronConfigGen [-h] [-f FILE] [-o OUTPUT] [-v]

optional arguments:
  -h, --help            show this help message and exit
  -f FILE, --file FILE  Load switches' information from local Yaml file
  -o OUTPUT, --output OUTPUT
                        Output Neutron configuration file. Default is neutronSw.ini
  -v, --verbose         Print output to standard output

**** Sample syntax ****
#python3 neutronML2Gen.py -f switchData.yaml -o neutronML2.ini

**** Sample Yaml file ****
# Lenovo Switch parameters
10.240.10.1:
  protocol: 
    NETCONF:
      SSH_Port: 830
      SSH_User: user1
      SSH_Password: passw0rd
    SNMP:
      SNMP_Port: 161
      SNMP_Ver: 3
      SNMP_User: adminmd5
      SNMP_Community: private
      SNMP_Authkey: key1
      SNMP_Privkey: key2
      SNMP_Auth: SHA
      SNMP_Priv: AES-128
  links:
    compute01:
      portType: single
      portNumber: 10
    compute02:
      portType: portchannel
      portNumber: 64

**** Sample ML2 configuration ****
### Configuration block for switch 10.240.10.1 ###
[ml2_mech_lenovo:10.240.10.1]
#This is to let driver know SNMP protocol will be used to communicate with this switch. If not exist, assume Netconf
protocol = SNMP

# Hostname and port used on the switch for this compute host.
compute02=portchannel:64
compute01=10
# Port number where the SSH will be running at the Switch. Default is 22 so this variable only needs to be configured if different.
ssh_port = 830
# Provide the log in information to the switch
username = user1
password = passw0rd

# Port number for SNMP
snmp_port=161

# SNMP version number, options are: 1, 2c, 3
snmp_version=3

# Community name
snmp_community=private

# SNMP user
snmp_user=adminshaaes

# SNMP Auth key and Priv key, if not exist, assume NO_AUTH and NO_PRIV
snmp_authkey=key1
snmp_privkey=key2

# SNMP v3 auth option: SHA-96.
snmp_auth = SHA

# SNMP v2 priv option: AES-128.
snmp_priv = AES-128

CHANGE LOGS
-----------
N/A


FAQ
----
N/A
