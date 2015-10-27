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
Implements a NOS-OS NETCONF over SSHv2 API Client
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


class LenovoNOSDriverNetconf(object):
    """NOS Driver Main Class."""
    def __init__(self):
        self.ncclient = None
        self.nos_switches = conf.ML2MechLenovoConfig.nos_dict
        self.connections = {}


    def _import_ncclient(self):
        """Import the NETCONF client (ncclient) module.

        The ncclient module is not installed as part of the normal Neutron
        distributions. It is imported dynamically in this module so that
        the import can be mocked, allowing unit testing without requiring
        the installation of ncclient.

        """
        return importutils.import_module('ncclient.manager')


    def _edit_config(self, nos_host, target='running', config='',
                     allowed_exc_strs=None):
        """Modify switch config for a target config type.

        :param nos_host: IP address of switch to configure
        :param target: Target config type
        :param config: Configuration string in XML format
        :param allowed_exc_strs: Exceptions which have any of these strings
                                 as a subset of their exception message
                                 (str(exception)) can be ignored

        :raises: NOSConfigFailed

        """
        if not allowed_exc_strs:
            allowed_exc_strs = []
        mgr = self._nos_connect(nos_host)
        try:
            mgr.edit_config(target=target, config=config, format='text')
        except Exception as e:
            for exc_str in allowed_exc_strs:
                if exc_str in str(e):
                    break
            else:
                # Raise a Neutron exception. Include a description of
                # the original ncclient exception.
                raise cexc.NOSConfigFailed(config=config, exc=e)


    def _nos_connect(self, nos_host):
        """Make SSH connection to the NOS Switch."""
        if getattr(self.connections.get(nos_host), 'connected', None):
            return self.connections[nos_host]

        if not self.ncclient:
            self.ncclient = self._import_ncclient()
        nos_ssh_port = int(self.nos_switches[nos_host, 'ssh_port'])
        nos_user = self.nos_switches[nos_host, const.USERNAME]
        nos_password = self.nos_switches[nos_host, const.PASSWORD]
        try:
            try:
                # With new ncclient version, we can pass device_params...
                man = self.ncclient.connect(host=nos_host,
                                            port=nos_ssh_port,
                                            username=nos_user,
                                            password=nos_password,
					    hostkey_verify=False)
                #                           device_params={"name": "nos"})
            except TypeError:
                # ... but if that causes an error, we appear to have the old
                # ncclient installed, which doesn't understand this parameter.
                man = self.ncclient.connect(host=nos_host,
                                            port=nos_ssh_port,
                                            username=nos_user,
                                            password=nos_password)
        except Exception as e:
            # Raise a Neutron exception. Include a description of
            # the original ncclient exception.
            raise cexc.NOSConnectFailed(nos_host=nos_host, exc=e)

        self.connections[nos_host] = man
        return self.connections[nos_host]


    def _create_xml_snippet(self, customized_config):
        """Create XML snippet.

        Creates the Proper XML structure for the NOS Switch Configuration.
        """
        conf_xml_snippet = snipp.EXEC_CONF_SNIPPET % (customized_config)
        return conf_xml_snippet


    def _create_vlan(self, nos_host, vlanid, vlanname):
        """Create a VLAN on NOS Switch given the VLAN ID and Name."""
	try:
            confstr = self._create_xml_snippet(
                snipp.CMD_VLAN_CONF_SNIPPET % (vlanid, vlanname))
            LOG.debug(_("NOSDriver: %s"), confstr)
            self._edit_config(nos_host, target='running', config=confstr)
	except cexc.NOSConfigFailed:
	    with excutils.save_and_reraise_exception():
                self.delete_vlan(nos_host, vlanid)
		

        # Enable VLAN active and no-shutdown states. Some versions of
        # NOS switch do not allow state changes for the extended VLAN
        # range (1006-4094), but these errors can be ignored (default
        # values are appropriate).
        try:
            confstr = self._create_xml_snippet(snipp.CMD_VLAN_NO_SHUTDOWN_SNIPPET % vlanid)
            self._edit_config( nos_host, target='running', config=confstr)
        except cexc.NOSConfigFailed:
            with excutils.save_and_reraise_exception():
                self.delete_vlan(nos_host, vlanid)


    def delete_vlan(self, nos_host, vlanid):
        """Delete a VLAN on NOS Switch given the VLAN ID."""
        confstr = snipp.CMD_NO_VLAN_CONF_SNIPPET % vlanid
        confstr = self._create_xml_snippet(confstr)
        self._edit_config(nos_host, target='running', config=confstr)


    def enable_vlan_on_trunk_int(self, nos_host, vlanid, intf_type,
                                 interface):
        """Enable a VLAN on a trunk interface."""
        # If more than one VLAN is configured on this interface then
        # include the 'add' keyword.
        if len(nos_db_v2.get_port_switch_bindings(
                '%s:%s' % (intf_type, interface), nos_host)) == 1:
            snippet = snipp.CMD_INT_VLAN_SNIPPET
        else:
            snippet = snipp.CMD_INT_VLAN_ADD_SNIPPET

        confstr = snippet % (intf_type, interface, vlanid)
        confstr = self._create_xml_snippet(confstr)
        LOG.debug(_("NOSDriver: %s"), confstr)
        self._edit_config(nos_host, target='running', config=confstr)


    def disable_vlan_on_trunk_int(self, nos_host, vlanid, intf_type, interface):
        """Disable a VLAN on a trunk interface."""
        confstr = (snipp.CMD_NO_VLAN_INT_SNIPPET %
                   (intf_type, interface, vlanid))
        confstr = self._create_xml_snippet(confstr)
        LOG.debug(_("NOSDriver: %s"), confstr)
        self._edit_config(nos_host, target='running', config=confstr)


    def create_and_trunk_vlan(self, nos_host, vlan_id, vlan_name, intf_type, nos_port):
        """Create VLAN and trunk it on the specified ports."""
        self._create_vlan(nos_host, vlan_id, vlan_name)
        LOG.debug(_("NOSDriver created VLAN: %s"), vlan_id)
        if nos_port:
            self.enable_vlan_on_trunk_int(nos_host, vlan_id, intf_type,
                                          nos_port)
