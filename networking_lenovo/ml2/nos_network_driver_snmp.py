# Copyright 2013 OpenStack Foundation
# All rights reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
Implements a NOS-OS SNMP Client
"""

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import excutils
from oslo_utils import importutils

from networking_lenovo.ml2 import config as conf
from networking_lenovo.ml2 import constants as const
from networking_lenovo.ml2 import exceptions as cexc
from networking_lenovo.ml2 import nos_db_v2
from networking_lenovo.ml2 import nos_snippets as snipp

LOG = logging.getLogger(__name__)

from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp import error as snmp_error
from pysnmp.proto import rfc1902

SNMP_PORT = 161
SNMP_V1 = '1'
SNMP_V2C = '2c'
SNMP_V3 = '3'
SNMP_AUTH_MD5 = 'MD5'
SNMP_AUTH_SHA = 'SHA'
SNMP_PRIV_DES = 'DES'
SNMP_PRIV_AES = 'AES-128'

USM_NO_AUTH   = (1, 3, 6, 1, 6, 3, 10, 1, 1, 1)
USM_MD5_AUTH  = (1, 3, 6, 1, 6, 3, 10, 1, 1, 2) 
USM_SHA_AUTH  = (1, 3, 6, 1, 6, 3, 10, 1, 1, 3)
USM_NO_PRIV   = (1, 3, 6, 1, 6, 3, 10, 1, 2, 1)
USM_DES_PRIV  = (1, 3, 6, 1, 6, 3, 10, 1, 2, 2)
USM_AES_PRIV  = (1, 3, 6, 1, 6, 3, 10, 1, 2, 4)

cmdGen = cmdgen.CommandGenerator()
APPLY = 2
oid_enterprise = (1, 3, 6, 1, 4, 1,)
vlanNewCfgState = (26543, 2, 7, 6, 2, 1, 1, 3, 1, 4)
vlanNewCfgVlanName = (26543, 2, 7, 6, 2, 1, 1, 3, 1, 2)
vlanNewCfgDelete = (26543, 2, 7, 6, 2, 1, 1, 3, 1, 7)
vlanNewCfgAddPort = (26543, 2, 7, 6, 2, 1, 1, 3, 1, 5)
vlanNewCfgRemovePort = (26543, 2, 7, 6, 2, 1, 1, 3, 1, 6)
vlanMaxVlanID = (26543, 2, 7, 6, 2, 1, 1, 4, 0)
agPortNewCfgVlanTag = (26543, 2, 7, 6, 1, 1, 2, 3, 1, 3)
agPortNewCfgPVID = (26543, 2, 7, 6, 1, 1, 2, 3, 1, 6)
trunkGroupInfoPorts = (26543, 2, 7, 6, 2, 3, 9, 1, 1, 3)
agApplyConfiguration = (26543, 2, 7, 6, 1, 1, 1, 2, 0)

class LenovoNOSDriverSNMP(object):
    """NOS SNMP Driver Main Class."""
    def __init__(self):
        self.nos_switches = conf.ML2MechLenovoConfig.nos_dict

    def _get_auth(self, nos_host):
        if self.nos_switches[nos_host, 'snmp_version'] == SNMP_V3:
            nos_user = self.nos_switches[nos_host, 'snmp_user'] 
            nos_authkey = None
            if (nos_host, 'snmp_authkey') in self.nos_switches:
                nos_authkey = self.nos_switches[nos_host, 'snmp_authkey'] 
                if (nos_host, 'snmp_auth') in self.nos_switches:
                    nos_auth = USM_SHA_AUTH if self.nos_switches[nos_host, 'snmp_auth'] == SNMP_AUTH_MD5 else USM_MD5_AUTH
                else:
                    nos_auth = USM_MD5_AUTH
            else:
                nos_auth = USM_NO_AUTH


            nos_privkey = None
            if (nos_host, 'snmp_privkey') in self.nos_switches:
                nos_privkey = self.nos_switches[nos_host, 'snmp_privkey'] 
                if (nos_host, 'snmp_priv') in self.nos_switches:
                    nos_priv = USM_AES_PRIV if self.nos_switches[nos_host, 'snmp_priv'] == SNMP_PRIV_AES else USM_DES_PRIV
                else:
                    nos_priv = USM_DES_PRIV
            else:
                nos_priv = USM_NO_PRIV

            #print('%s %s %s %s %s' % (nos_user, nos_authkey, nos_privkey, nos_auth, nos_priv))
            return cmdgen.UsmUserData(nos_user, nos_authkey, nos_privkey, nos_auth, nos_priv)
        else:
            mp_model = 1 if self.nos_switches[nos_host, 'snmp_version'] == SNMP_V2C else 0
            return cmdgen.CommunityData(self.nos_switches[nos_host, 'snmp_community'], mpModel=mp_model)

    def _get_transport(self, nos_host):
        return cmdgen.UdpTransportTarget((nos_host, int(self.nos_switches[nos_host, 'snmp_port'])))
    
    def _set(self, nos_host, varBinds):
        try:
            results = cmdGen.setCmd(self._get_auth(nos_host),
                                   self._get_transport(nos_host),
                                   *varBinds)
        except snmp_error.PySnmpError as e:
            raise cexc.NOSSNMPFailure(operation='SET', error=e)

        err_indication, err_status, err_index, var_binds = results
        if err_indication:
            print(err_indication)
            raise cexc.NOSSNMPFailure(operation='SET', error=err_indication)
        elif err_status:
            print('%s at %s' % (
                err_status.prettyPrint(),
                err_index and var_binds[int(err_index)-1][0] or '?'
                )
            )
            """not raise exception for error_status"""
            #raise cexc.NOSSNMPFailure(operation='SET', error=err_status.prettyPrint())
    
    def _get(self, nos_host, varBinds):
        try:
            results = cmdGen.getCmd(self._get_auth(nos_host),
                                   self._get_transport(nos_host),
                                   *varBinds)
        except snmp_error.PySnmpError as e:
            raise cexc.NOSSNMPFailure(operation='GET', error=e)

        err_indication, err_status, err_index, var_binds = results
        if err_indication:
            print(err_indication)
            raise cexc.NOSSNMPFailure(operation='GET', error=err_indication)
        elif err_status:
            print('%s at %s' % (
                err_status.prettyPrint(),
                err_index and var_binds[int(err_index)-1][0] or '?'
                )
            )
            raise cexc.SNMPFailure(operation='GET', error=err_status.prettyPrint())
        
        return var_binds
    

    def _get_max_vlan_id(self, nos_host):
        varBinds = []
        snmp_oid = oid_enterprise + vlanMaxVlanID
        varBinds += snmp_oid,
        
        ret = self._get(nos_host, varBinds)
        name, val = ret[0]
        return val

    
    def _apply_config(self, nos_host):
        varBinds = []
        snmp_oid = oid_enterprise + agApplyConfiguration
        value = rfc1902.Integer(APPLY)
        varBinds += (snmp_oid, value),

        self._set(nos_host, varBinds)


    #create VLAN
    def create_vlan(self, nos_host, vlan_id, vlan_name):
        """Create a VLAN on NOS Switch given the VLAN ID and Name."""
        LOG.debug(_('create_vlan %s %d'), nos_host, vlan_id) 
        varBinds = []
        ENABLED = 2
        snmp_oid = oid_enterprise + vlanNewCfgState + (vlan_id,)
        value = rfc1902.Integer(ENABLED)
        varBinds += (snmp_oid, value),

        snmp_oid = oid_enterprise + vlanNewCfgVlanName + (vlan_id,)
        value = rfc1902.OctetString(vlan_name)
        varBinds += (snmp_oid, value),

        self._set(nos_host, varBinds)

        self._apply_config(nos_host)


    def delete_vlan(self, nos_host, vlan_id):
        """Delete a VLAN on NOS Switch given the VLAN ID."""
        LOG.debug(_('delete_vlan %s %d'), nos_host, vlan_id)
        varBinds = []
        DELETE = 2
        snmp_oid = oid_enterprise + vlanNewCfgDelete + (vlan_id,)
        value = rfc1902.Integer(DELETE)
        varBinds += (snmp_oid, value),

        self._set(nos_host, varBinds)

        self._apply_config(nos_host)

    
    def enable_vlan_on_trunk_int(self, nos_host, vlan_id, intf_type, interface):
        LOG.debug(_('enable_vlan_on_trunk_int %s %d %s:%s'), nos_host, vlan_id, intf_type, interface)
        
        trunk_init = False
        if len(nos_db_v2.get_port_switch_bindings(
                '%s:%s' % (intf_type, interface), nos_host)) == 1:
            trunk_init = True

        if intf_type == "portchannel":
            varBinds = []
            snmp_oid = oid_enterprise + trunkGroupInfoPorts + (interface,) 
            varBinds += (snmp_oid),
            ret = self._get(nos_host, varBinds)
            _n, _v = ret[0]
            portmap = _v.asNumbers()
            port_base = 0
            for byte in portmap:
                if byte != 0:
                    bit = 7
                    while bit >= 0:
                        if (byte & (1<<bit)):
                            port_num = port_base + 7 - bit
                            LOG.debug(_("interface port %d"), port_num)
                            if trunk_init is True:
                                LOG.debug(_("    switchport mode trunk"))
                                LOG.debug(_("    switchport trunk allowed vlan 1"))
                                self._switchport_mode_trunk_init(nos_host, port_num)
                            LOG.debug(_("    switchport trunk allowed vlan add %d"), vlan_id)
                            self._enable_vlan_on_port(nos_host, vlan_id, port_num)
                        bit -= 1
                port_base += 8
        else:
            port_num = int(interface)
            LOG.debug(_("interface port %d"), port_num)
            if trunk_init is True:
                LOG.debug(_("    switchport mode trunk"))
                LOG.debug(_("    switchport trunk allowed vlan 1"))
                self._switchport_mode_trunk_init(nos_host, port_num)
            LOG.debug(_("    switchport trunk allowed vlan add %d"), vlan_id)
            self._enable_vlan_on_port(nos_host, vlan_id, port_num)
        
        self._apply_config(nos_host)
        

    def _switchport_mode_trunk_init(self, nos_host, port_num):
        """Enable a port as VLAN trunk mode."""
        LOG.debug(_('_switchport_mode_trunk_init %s %d'), nos_host, port_num)

        """Change switchport to trunk mode, and set PVID = 1"""
        varBinds = []
        TAGGED = 2
        snmp_oid = oid_enterprise + agPortNewCfgVlanTag + (port_num,)
        value = rfc1902.Integer(TAGGED)
        varBinds += (snmp_oid, value),

        snmp_oid = oid_enterprise + agPortNewCfgPVID + (port_num,)
        value = rfc1902.Integer32(1)
        varBinds += (snmp_oid, value),

        self._set(nos_host, varBinds)

        """Remove all other VLAN except 1 for the first time config this port"""
        max_vlan_id = self._get_max_vlan_id(nos_host)
        vlans = range(2, max_vlan_id+1)
        varBinds = []
        for vid in vlans:
            snmp_oid = oid_enterprise + vlanNewCfgRemovePort + (vid,)
            value = rfc1902.Gauge32(port_num)
            varBinds += (snmp_oid, value),
            if vid%20 == 0:
                self._set(nos_host, varBinds)
                varBinds = []
        
        self._set(nos_host, varBinds)

 
    def _enable_vlan_on_port(self, nos_host, vlan_id, port_num):
        """Enable a VLAN on a port interface."""
        LOG.debug(_('_enable_vlan_on_port %s %d %d'), nos_host, vlan_id, port_num)

        varBinds = []
        snmp_oid = oid_enterprise + vlanNewCfgAddPort + (vlan_id,)
        value = rfc1902.Gauge32(port_num)
        varBinds += (snmp_oid, value),

        self._set(nos_host, varBinds)

#    def enable_vlan_on_trunk_int(self, nos_host, vlan_id, intf_type, interface):
#        """Enable a VLAN on a trunk interface."""
#        LOG.debug(_('enable_vlan_on_trunk_int %s %d %s'), nos_host, vlan_id, interface)
#
#        """Change switchport to trunk mode, and add vlan"""
#        varBinds = []
#        TAGGED = 2
#        snmp_oid = oid_enterprise + agPortNewCfgVlanTag + (interface,)
#        value = rfc1902.Integer(TAGGED)
#        varBinds += (snmp_oid, value),
#
#        snmp_oid = oid_enterprise + agPortNewCfgPVID + (interface,)
#        value = rfc1902.Integer32(1)
#        varBinds += (snmp_oid, value),
#
#        snmp_oid = oid_enterprise + vlanNewCfgAddPort + (vlan_id,)
#        value = rfc1902.Gauge32(interface)
#        varBinds += (snmp_oid, value),
#
#        value = rfc1902.Integer(APPLY)
#        varBinds += (agApplyConfiguration, value),
#
#        self._set(nos_host, varBinds)
#
#        if len(nos_db_v2.get_port_switch_bindings(
#                '%s:%s' % (intf_type, interface), nos_host)) == 1:
#            """Remove all other VLAN except 1 for the first time config this port"""
#            max_vlan_id = self._get_max_vlan_id(nos_host)
#            vlans = range(2, max_vlan_id+1)
#            varBinds = []
#            for vid in vlans:
#                if vid != vlan_id:
#                    snmp_oid = oid_enterprise + vlanNewCfgRemovePort + (vid,)
#                    value = rfc1902.Gauge32(interface)
#                    varBinds += (snmp_oid, value),
#                if vid%20 == 0:
#                    self._set(nos_host, varBinds)
#                    varBinds = []
#                    
#            
#            value = rfc1902.Integer(APPLY)
#            varBinds += (agApplyConfiguration, value),
#            self._set(nos_host, varBinds)
#            
#        else:
#            snmp_oid = oid_enterprise + vlanNewCfgAddPort + (vlan_id,)
#            value = rfc1902.Gauge32(interface)
#            varBinds += (snmp_oid, value),
#
#            value = rfc1902.Integer(APPLY)
#            varBinds += (agApplyConfiguration, value),
#            self._set(nos_host, varBinds)
#    

    def disable_vlan_on_trunk_int(self, nos_host, vlan_id, intf_type, interface):
        LOG.debug(_('disable_vlan_on_trunk_int %s %d %s'), nos_host, vlan_id, interface)
        if intf_type == "portchannel":
            varBinds = []
            snmp_oid = oid_enterprise + trunkGroupInfoPorts + (interface,) 
            varBinds += (snmp_oid),
            ret = self._get(nos_host, varBinds)
            _n, _v = ret[0]
            portmap = _v.asNumbers()
            port_base = 0
            for byte in portmap:
                if byte != 0:
                    bit = 7
                    while bit >= 0:
                        if (byte & (1<<bit)):
                            port_num = port_base + 7 - bit
                            LOG.debug(_("interface port %d"), port_num)
                            LOG.debug(_("    switchport trunk allowed vlan remove %d"), vlan_id)
                            self._disable_vlan_on_port(nos_host, vlan_id, port_num)
                        bit -= 1
                port_base += 8
        else:
            port_num = int(interface)
            LOG.debug(_("interface port %d"), port_num)
            LOG.debug(_("    switchport trunk allowed vlan remove %d"), vlan_id)
            self._disable_vlan_on_port(nos_host, vlan_id, port_num)
        
        self._apply_config(nos_host)

    
    def _disable_vlan_on_port(self, nos_host, vlan_id, port_num):
        """Disable a VLAN on a port interface."""
        LOG.debug(_('_disable_vlan_on_port %s %d %d'), nos_host, vlan_id, port_num)
        varBinds = []

        snmp_oid = oid_enterprise + vlanNewCfgRemovePort + (vlan_id,)
        value = rfc1902.Gauge32(port_num)
        varBinds += (snmp_oid, value),

        self._set(nos_host, varBinds)


    def create_and_trunk_vlan(self, nos_host, vlan_id, vlan_name, intf_type, interface):
        LOG.debug(_('create_and_trunk_vlan %s %d %s'), nos_host, vlan_id, interface)
        self.create_vlan(nos_host, vlan_id, vlan_name)
        if interface:
            self.enable_vlan_on_trunk_int(nos_host, vlan_id, intf_type, interface)
