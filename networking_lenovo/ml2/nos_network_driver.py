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

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import excutils
from oslo_utils import importutils

from networking_lenovo.ml2 import config as conf
from networking_lenovo.ml2 import constants as const
from networking_lenovo.ml2 import exceptions as cexc
from networking_lenovo.ml2 import nos_db_v2
from networking_lenovo.ml2 import nos_snippets as snipp
from networking_lenovo.ml2 import nos_network_driver_netconf
from networking_lenovo.ml2 import nos_network_driver_snmp

LOG = logging.getLogger(__name__)

class LenovoNOSDriver(object):
    def __init__(self):
        self.nos_switches = conf.ML2MechLenovoConfig.nos_dict
        self.netconf = nos_network_driver_netconf.LenovoNOSDriverNetconf()
        self.snmp = nos_network_driver_snmp.LenovoNOSDriverSNMP()


    def _is_snmp(self, nos_host):
        if (nos_host, 'protocol') not in self.nos_switches:
            return False
        else:
            return (self.nos_switches[nos_host, 'protocol']).lower() == 'snmp'


    def delete_vlan(self, nos_host, vlan_id):
        func = None
        if (self._is_snmp(nos_host)):
            func = self.snmp.delete_vlan
        else:
            func = self.netconf.delete_vlan

        return func(nos_host, vlan_id)


    def enable_vlan_on_trunk_int(self, nos_host, vlan_id, intf_type, interface):
        func = None
        if (self._is_snmp(nos_host)):
            func = self.snmp.enable_vlan_on_trunk_int
        else:
            func = self.netconf.enable_vlan_on_trunk_int

        return func(nos_host, vlan_id, intf_type, interface)


    def disable_vlan_on_trunk_int(self, nos_host, vlan_id, intf_type, interface):
        func = None
        if (self._is_snmp(nos_host)):
            func = self.snmp.disable_vlan_on_trunk_int
        else:
            func = self.netconf.disable_vlan_on_trunk_int

        return func(nos_host, vlan_id, intf_type, interface)


    def create_and_trunk_vlan(self, nos_host, vlan_id, vlan_name, intf_type, nos_port):
        func = None
        if (self._is_snmp(nos_host)):
            func = self.snmp.create_and_trunk_vlan
        else:
            func = self.netconf.create_and_trunk_vlan

        return func(nos_host, vlan_id, vlan_name, intf_type, nos_port)
