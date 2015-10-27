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
ML2 Mechanism Driver for Lenovo NOS platforms.
"""
from oslo_config import cfg
from oslo_log import log as logging

from neutron.common import constants as n_const
from neutron.extensions import portbindings
from neutron.plugins.common import constants as p_const
from neutron.plugins.ml2 import driver_api as api

from networking_lenovo.ml2 import config as conf
from networking_lenovo.ml2 import exceptions as excep
from networking_lenovo.ml2 import nos_db_v2 as nxos_db
from networking_lenovo.ml2 import nos_network_driver

LOG = logging.getLogger(__name__)


class LenovoNOSMechanismDriver(api.MechanismDriver):

    """Lenovo NOS ML2 Mechanism Driver."""

    def initialize(self):
        # Create ML2 device dictionary from ml2_conf.ini entries.
        conf.ML2MechLenovoConfig()

        # Extract configuration parameters from the configuration file.
        self._nos_switches = conf.ML2MechLenovoConfig.nos_dict
        LOG.debug(_("nos_switches found = %s"), self._nos_switches)

        self.driver = nos_network_driver.LenovoNOSDriver()

    def _valid_network_segment(self, segment):
        return (cfg.CONF.ml2_lenovo.managed_physical_network is None or
                cfg.CONF.ml2_lenovo.managed_physical_network ==
                segment[api.PHYSICAL_NETWORK])

    def _get_vlanid(self, segment):
        if (segment and segment[api.NETWORK_TYPE] == p_const.TYPE_VLAN and
            self._valid_network_segment(segment)):
            return segment.get(api.SEGMENTATION_ID)

    def _is_deviceowner_compute(self, port):
        return port['device_owner'].startswith('compute')

    def _is_status_active(self, port):
        return port['status'] == n_const.PORT_STATUS_ACTIVE

    def _get_switch_info(self, host_id):
        host_connections = []
        for switch_ip, attr in self._nos_switches:
            if str(attr) == str(host_id):
                for port_id in (
                    self._nos_switches[switch_ip, attr].split(',')):
                    if ':' in port_id:
                        intf_type, port = port_id.split(':')
                    else:
#                        intf_type, port = 'ethernet', port_id
                        intf_type, port = 'port', port_id
                    host_connections.append((switch_ip, intf_type, port))

        if host_connections:
            return host_connections
        else:
            raise excep.NOSComputeHostNotConfigured(host=host_id)

    def _configure_nxos_db(self, vlan_id, device_id, host_id):
        """Create the nos database entry.

        Called during update precommit port event.
        """
        host_connections = self._get_switch_info(host_id)
        for switch_ip, intf_type, nos_port in host_connections:
            port_id = '%s:%s' % (intf_type, nos_port)
            nxos_db.add_nosport_binding(port_id, str(vlan_id), switch_ip,
                                          device_id)

    def _configure_switch_entry(self, vlan_id, device_id, host_id):
        """Create a nos switch entry.

        if needed, create a VLAN in the appropriate switch/port and
        configure the appropriate interfaces for this VLAN.

        Called during update postcommit port event.
        """
        vlan_name = cfg.CONF.ml2_lenovo.vlan_name_prefix + str(vlan_id)
        host_connections = self._get_switch_info(host_id)

        # (nos_port,switch_ip) will be unique in each iteration.
        # But switch_ip will repeat if host has >1 connection to same switch.
        # So track which switch_ips already have vlan created in this loop.
        vlan_already_created = []
        for switch_ip, intf_type, nos_port in host_connections:

            # The VLAN needs to be created on the switch if no other
            # instance has been placed in this VLAN on a different host
            # attached to this switch.  Search the existing bindings in the
            # database.  If all the instance_id in the database match the
            # current device_id, then create the VLAN, but only once per
            # switch_ip.  Otherwise, just trunk.
            all_bindings = nxos_db.get_nosvlan_binding(vlan_id, switch_ip)
            previous_bindings = [row for row in all_bindings
                    if row.instance_id != device_id]
            if previous_bindings or (switch_ip in vlan_already_created):
                LOG.debug("NOS: trunk vlan %s"), vlan_name
                self.driver.enable_vlan_on_trunk_int(switch_ip, vlan_id,
                                                     intf_type, nos_port)
            else:
                vlan_already_created.append(switch_ip)
                LOG.debug("NOS: create & trunk vlan %s"), vlan_name
                self.driver.create_and_trunk_vlan(
                    switch_ip, vlan_id, vlan_name, intf_type, nos_port)

    def _delete_nxos_db(self, vlan_id, device_id, host_id):
        """Delete the nos database entry.

        Called during delete precommit port event.
        """
        try:
            rows = nxos_db.get_nosvm_bindings(vlan_id, device_id)
            for row in rows:
                nxos_db.remove_nosport_binding(
                    row.port_id, row.vlan_id, row.switch_ip, row.instance_id)
        except excep.NOSPortBindingNotFound:
            return

    def _delete_switch_entry(self, vlan_id, device_id, host_id):
        """Delete the nos switch entry.

        By accessing the current db entries determine if switch
        configuration can be removed.

        Called during update postcommit port event.
        """
        host_connections = self._get_switch_info(host_id)

        # (nos_port,switch_ip) will be unique in each iteration.
        # But switch_ip will repeat if host has >1 connection to same switch.
        # So track which switch_ips already have vlan removed in this loop.
        vlan_already_removed = []
        for switch_ip, intf_type, nos_port in host_connections:

            # if there are no remaining db entries using this vlan on this
            # nos switch port then remove vlan from the switchport trunk.
            port_id = '%s:%s' % (intf_type, nos_port)
            try:
                nxos_db.get_port_vlan_switch_binding(port_id, vlan_id,
                                                     switch_ip)
            except excep.NOSPortBindingNotFound:
                self.driver.disable_vlan_on_trunk_int(switch_ip, vlan_id,
                                                      intf_type, nos_port)

                # if there are no remaining db entries using this vlan on this
                # nos switch then remove the vlan.
                try:
                    nxos_db.get_nosvlan_binding(vlan_id, switch_ip)
                except excep.NOSPortBindingNotFound:

                    # Do not perform a second time on same switch
                    if switch_ip not in vlan_already_removed:
                        self.driver.delete_vlan(switch_ip, vlan_id)
                        vlan_already_removed.append(switch_ip)

    def _is_vm_migration(self, context):
        if not context.top_bound_segment and context.original_top_bound_segment:
            return context.host != context.original_host

    def _port_action(self, port, segment, func):
        """Verify configuration and then process event."""
        device_id = port.get('device_id')
        host_id = port.get(portbindings.HOST_ID)
        vlan_id = self._get_vlanid(segment)

        if vlan_id and device_id and host_id:
            func(vlan_id, device_id, host_id)
        else:
            fields = "vlan_id " if not vlan_id else ""
            fields += "device_id " if not device_id else ""
            fields += "host_id" if not host_id else ""
            raise excep.NOSMissingRequiredFields(fields=fields)

    def update_port_precommit(self, context):
        """Update port pre-database transaction commit event."""

        # if VM migration is occurring then remove previous database entry
        # else process update event.
        if self._is_vm_migration(context):
            self._port_action(context.original,
                              context.original_top_bound_segment,
                              self._delete_nxos_db)
        else:
            if (self._is_deviceowner_compute(context.current) and
                self._is_status_active(context.current)):
                self._port_action(context.current,
                                  context.top_bound_segment,
                                  self._configure_nxos_db)

    def update_port_postcommit(self, context):
        """Update port non-database commit event."""

        # if VM migration is occurring then remove previous nos switch entry
        # else process update event.
        if self._is_vm_migration(context):
            self._port_action(context.original,
                              context.original_top_bound_segment,
                              self._delete_switch_entry)
        else:
            if (self._is_deviceowner_compute(context.current) and
                self._is_status_active(context.current)):
                self._port_action(context.current,
                                  context.top_bound_segment,
                                  self._configure_switch_entry)

    def delete_port_precommit(self, context):
        """Delete port pre-database commit event."""
        if self._is_deviceowner_compute(context.current):
            self._port_action(context.current,
                              context.top_bound_segment,
                              self._delete_nxos_db)

    def delete_port_postcommit(self, context):
        """Delete port non-database commit event."""
        if self._is_deviceowner_compute(context.current):
            self._port_action(context.current,
                              context.top_bound_segment,
                              self._delete_switch_entry)
