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
from networking_lenovo.ml2 import cnos_network_driver_ssh
from networking_lenovo.ml2 import cnos_network_driver_rest

LOG = logging.getLogger(__name__)

class LenovoNOSDriver(object):
    PROTO_SNMP = 'snmp'
    PROTO_NETCONF = 'netconf'
    PROTO_REST = 'rest'
    OS_ENOS = 'enos'
    OS_CNOS = 'cnos'

    def __init__(self):
        self.nos_switches = conf.ML2MechLenovoConfig.nos_dict

        self.drivers = {
            (self.OS_ENOS, self.PROTO_SNMP) : 
                  nos_network_driver_snmp.LenovoNOSDriverSNMP(),

            (self.OS_ENOS, self.PROTO_NETCONF) : 
                  nos_network_driver_netconf.LenovoNOSDriverNetconf(),

            (self.OS_CNOS, self.PROTO_REST) : 
                  cnos_network_driver_rest.LenovoCNOSDriverREST(),
        }


    def _get_driver(self, host):
        """ 
        Obtains the instance of the class that actually implements
        the functionality based of the configuration settings for
        protocol(SNMP, REST API, Netconf) and operating system (ENOS, CNOS)
        """

        default_protocol = self.PROTO_NETCONF
        os = self.nos_switches.get((host, 'os'), self.OS_ENOS).lower()
        if os == self.OS_CNOS:
            default_protocol = self.PROTO_REST
        protocol = self.nos_switches.get((host, 'protocol'), default_protocol).lower()

        try:
            driver = self.drivers[(os, protocol)]
        except KeyError:
            raise cexc.InvalidOSProtocol(protocol=protocol, os=os)

        return driver
        

    def delete_vlan(self, nos_host, vlan_id):
        func = self._get_driver(nos_host).delete_vlan

        return func(nos_host, vlan_id)


    def enable_vlan_on_trunk_int(self, nos_host, vlan_id, intf_type, interface):
        func = self._get_driver(nos_host).enable_vlan_on_trunk_int

        return func(nos_host, vlan_id, intf_type, interface)


    def disable_vlan_on_trunk_int(self, nos_host, vlan_id, intf_type, interface):
        func = self._get_driver(nos_host).disable_vlan_on_trunk_int

        return func(nos_host, vlan_id, intf_type, interface)


    def create_and_trunk_vlan(self, nos_host, vlan_id, vlan_name, intf_type, nos_port):
        func = self._get_driver(nos_host).create_and_trunk_vlan

        return func(nos_host, vlan_id, vlan_name, intf_type, nos_port)
