'''
Lenovo Openstack Neutron configuration generator: Generate Neutron driver configuration for Lenovo switches 
@author: ple@lenovo.com
History:
- Created on Jan 20, 2014
-
'''
import sys, os, traceback
try:
    import argparse
except:
    print ('[ERROR]: Python module "argparse" is not available.')
    sys.exit()

defaultOutputFile = './neutronSw.ini'

class neutronConf():
    def __init__(self):
        self.dictInput = dict()
        self.outputFile = defaultOutputFile
        self.baseConfig = '''
[ml2_mech_lenovo:{swIp}]
#This is to let driver know SNMP protocol will be used to communicate with this switch. If not exist, assume Netconf
{proto}

# Hostname and port used on the switch for this compute host.
{connections}
# Port number where the SSH will be running at the Switch. Default is 22 so this variable only needs to be configured if different.
{sshPort}
# Provide the log in information to the switch
username = {user}
password = {passwd}
'''
        self.snmpBaseConfig = '''
# Port number for SNMP
snmp_port={snmpPort}

# SNMP version number, options are: 1, 2c, 3
snmp_version={snmpVer}

# Community name
snmp_community={snmpCommunity}

# SNMP user
snmp_user={snmpUser}

# SNMP Auth key and Priv key, if not exist, assume NO_AUTH and NO_PRIV
snmp_authkey={snmpAuthkey}
snmp_privkey={snmpPrivkey}

# SNMP v3 auth options, default is MD5, options: MD5, SHA
snmp_auth={snmpAuth}

# SNMP v2 priv options, default is DES, options: DES, AES-128
snmp_priv={snmpPriv}
        '''
    def genConfig(self,outFile, verbose):
        if not os.path.isfile(outFile):
            print('[INFO]: Creating Neutron configuration file %s ...' % outFile)
        else:
            print('[INFO]: Appending configuration entries to file %s ...' % outFile)
        
        for swIp, params in self.dictInput.items():
            baseDict = self.__parseBaseConf(swIp, params)
            snmpDict = self.__parseSnmpConf(swIp, params)
            try:
                swConfig = '%s%s' % (self.baseConfig.format(**baseDict), self.snmpBaseConfig.format(**snmpDict))
                if verbose:
                    print(swConfig)
                with open(outFile,'a') as f:
                    f.write('\n### Configuration block for switch %s ###' % swIp)
                    f.write(swConfig)
            except Exception as e:
                print ('[ERROR]: Failed to generate the configuration entry. %s ' % e)
            finally:
                self.lstInput = []# Reset the data list
    
    def loadInputFromYaml(self,fileName):
        """
            Description: Load Yaml data file and generate the Neutron configuration
        """
        from yaml import load
        
        if not os.path.isfile(fileName):
            print('[ERROR]: Could not find the data file %s. Aborted.' % fileName)
        with open(fileName,'r') as f: # Open file for reading
            yamlSrc = f.read()
            try:
                self.dictInput = load(yamlSrc)
                return self.dictInput
            except Exception as e:
                print('[ERROR]: Failed to process the Yaml data file. Reason: %s' % str(e))
                print(traceback.format_exc())
    
    def __parseBaseConf(self, swIp, params):
        lstProtocol = [str(pro).lower() for pro in  params.get('protocol', {}).keys()]
        if 'snmp' in lstProtocol:
            protoCfg = 'protocol = SNMP'
        else:# NetConfig
            protoCfg = '#protocol = '
            print('[WARN]: Default protocol Netconf is usede for switch %s' % swIp)
        
        lstLink = list()
        dictLinks = params.get('links', {})
        for nodeName, link in dictLinks.items():
            portType = str(link.get('portType')).lower()
            portNo = link.get('portNumber')
            lstLink.append('%s=%s%s' % (nodeName, '%s:' % portType if portType == 'portchannel' else '', portNo))
        
        try:
            NETCONFDict = params.get('protocol').get('NETCONF',{})
        except:
            print('[WARN]: Missing protocol definition in the Yaml data file')
            sys.exit()
        
        try:
            sshRawPort = NETCONFDict.get('SSH_Port')
            sshPort = 'ssh_port = %s' % sshRawPort 
        except Exception as e:
            sshPort = '#ssh_port = '
            print('[WARN]: SSH_Port is not defined for NETCONF protocol. Default port will be used.') 
        
        try:
            sshUser = NETCONFDict.get('SSH_User')
        except:
            sshUser = ''
            print('[WARN]: SSH_User is not defined for NETCONF protocol. An empty string will be used.')
        
        try:
            sshPass = NETCONFDict.get('SSH_Password')
        except: 
            sshPass = ''
            print('[WARN]: SSH_Password is not defined for NETCONF protocol. An empty string will be used.')
        
        return {'swIp': swIp,'proto': protoCfg,'connections': '\n'.join(lstLink),'sshPort':sshPort, 'user':sshUser,'passwd':sshPass}
    
    def __parseSnmpConf(self, swIp, params):
        
        try:
            SNMPDict = params.get('protocol').get('SNMP',{})
        except:
            print('[WARN]: Missing protocol definition in the Yaml data file')
            sys.exit()
        
        snmpPort = SNMPDict.get('SNMP_Port')
        if snmpPort is None:
            snmpPort = 161
            print('[WARN]: SNMP_Port is not defined for SNMP protocol. Default port 161 will be used.')
            
        snmpVer = SNMPDict.get('SNMP_Ver')
        if snmpVer is None:
            snmpVer = 3
            print('[WARN]: SNMP_Ver is not defined for SNMP protocol. Default version 3 will be used.')
            
        snmpCom = SNMPDict.get('SNMP_Community')
        if  snmpCom is None:
            snmpCom = ''
            print('[WARN]: SNMP_Community is not defined for SNMP protocol. An empty string will be used.')
        
        snmpUser = SNMPDict.get('SNMP_User')
        if  snmpUser is None:
            snmpUser = ''
            print('[ERROR]: SNMP_User is not defined for SNMP protocol. An empty string will be used.')
                
        snmpAuthkey = SNMPDict.get('SNMP_Authkey')
        if snmpAuthkey is None:
            snmpAuthkey = ''
            print('[WARN]: SNMP_Authkey is not defined for SNMP protocol. An empty string will be used.')
        
        
        snmpPrivkey = SNMPDict.get('SNMP_Privkey')
        if  snmpPrivkey is None:
            snmpPrivkey = ''
            print('[WARN]: SNMP_Privkey is not defined for SNMP protocol. An empty string will be used.')
        
        
        snmpAuth = SNMPDict.get('SNMP_Auth')
        if snmpAuth is None:
            snmpAuth = 'MD5'
            print('[WARN]: SNMP_Auth is not defined for SNMP protocol. MD5 will be used as default')
        
        
        snmpPriv = SNMPDict.get('SNMP_Priv')
        if snmpPriv is None: 
            snmpPriv = 'DES'
            print('[WARN]: SNMP_Priv is not defined for SNMP protocol. DES will be used as default.')
        
        return {'snmpPort': snmpPort,'snmpVer': snmpVer,'snmpCommunity': snmpCom,'snmpUser':snmpUser, 'snmpAuthkey':snmpAuthkey,'snmpPrivkey':snmpPrivkey, 'snmpAuth':snmpAuth, 'snmpPriv':snmpPriv}
        
if __name__ == '__main__':
    '''
        Description: Generate Neutron driver configuration from Yaml data file
    '''
    objNeutronConf = neutronConf()
    cliParser = argparse.ArgumentParser(prog = 'neutronConfigGen')
    cliParser.add_argument('-f', '--file', help="Load switches\' information from local Yaml file ", required = False)
    cliParser.add_argument('-o', '--output', help="Output Neutron configuration file. Default is %s" % defaultOutputFile, default=defaultOutputFile)
    cliParser.add_argument('-v', '--verbose', help="Print output to standard output", action="store_true")
    try:
        objArgs = cliParser.parse_args()
        objNeutronConf.loadInputFromYaml(objArgs.file)
        objNeutronConf.genConfig(objArgs.output,objArgs.verbose)
    except Exception as e:
        print('[ERROR]: Failed to generate the configuration. Reason: %s' % str(e))