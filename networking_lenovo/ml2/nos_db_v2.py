# Copyright (c) 2013 OpenStack Foundation
# All Rights Reserved.
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
#

from oslo_log import log as logging
import sqlalchemy.orm.exc as sa_exc

import neutron.db.api as db
from networking_lenovo.ml2 import exceptions as c_exc
from networking_lenovo.ml2 import nos_models_v2


LOG = logging.getLogger(__name__)


def get_nosport_binding(port_id, vlan_id, switch_ip, instance_id):
    """Lists a nosport binding."""
    LOG.debug(_("get_nosport_binding() called"))
    return _lookup_all_nos_bindings(port_id=port_id,
                                      vlan_id=vlan_id,
                                      switch_ip=switch_ip,
                                      instance_id=instance_id)


def get_nosvlan_binding(vlan_id, switch_ip):
    """Lists a vlan and switch binding."""
    LOG.debug(_("get_nosvlan_binding() called"))
    return _lookup_all_nos_bindings(vlan_id=vlan_id, switch_ip=switch_ip)


def add_nosport_binding(port_id, vlan_id, switch_ip, instance_id, processed=False):
    """Adds a nosport binding."""
    LOG.debug(_("add_nosport_binding() called"))
    session = db.get_session()
    binding = nos_models_v2.NOSPortBinding(port_id=port_id,
                                               vlan_id=vlan_id,
                                               switch_ip=switch_ip,
                                               instance_id=instance_id,
                                               processed=processed)
    session.add(binding)
    session.flush()
    return binding


def remove_nosport_binding(port_id, vlan_id, switch_ip, instance_id):
    """Removes a nosport binding."""
    LOG.debug(_("remove_nosport_binding() called"))
    session = db.get_session()
    binding = _lookup_all_nos_bindings(session=session,
                                         vlan_id=vlan_id,
                                         switch_ip=switch_ip,
                                         port_id=port_id,
                                         instance_id=instance_id)
    for bind in binding:
        session.delete(bind)
    session.flush()
    return binding


def update_nosport_binding(port_id, new_vlan_id):
    """Updates nosport binding."""
    if not new_vlan_id:
        LOG.warning(_("update_nosport_binding called with no vlan"))
        return
    LOG.debug(_("update_nosport_binding called"))
    session = db.get_session()
    binding = _lookup_one_nos_binding(session=session, port_id=port_id)
    binding.vlan_id = new_vlan_id
    session.merge(binding)
    session.flush()
    return binding

def process_binding(port_id, vlan_id, switch_ip, instance_id):
    """Mark a binding as processed (i.e. changes have been made to
       the switch"""

    dbg_str = "process_binding() VM %s vlan %s, switch %s interface %s"
    dbg_str = dbg_str % (instance_id, vlan_id, switch_ip, port_id)
    LOG.debug(dbg_str)

    session = db.get_session()
    binding = _lookup_one_nos_binding(session=session,
                                      port_id=port_id,
                                      vlan_id=vlan_id,
                                      switch_ip=switch_ip,
                                      instance_id=instance_id,
                                      processed=False)
    binding.processed = True
    session.merge(binding)
    session.flush()
    return binding


def get_nosvm_bindings(vlan_id, instance_id):
    """Lists nosvm bindings."""
    LOG.debug(_("get_nosvm_bindings() called"))
    return _lookup_all_nos_bindings(instance_id=instance_id,
                                      vlan_id=vlan_id)


def get_port_vlan_switch_binding(port_id, vlan_id, switch_ip):
    """Lists nosvm bindings."""
    LOG.debug(_("get_port_vlan_switch_binding() called"))
    return _lookup_all_nos_bindings(port_id=port_id,
                                      switch_ip=switch_ip,
                                      vlan_id=vlan_id)


def get_port_switch_bindings(port_id, switch_ip):
    """List all vm/vlan bindings on a NOS switch port."""
    LOG.debug(_("get_port_switch_bindings() called, "
                "port:'%(port_id)s', switch:'%(switch_ip)s'"),
              {'port_id': port_id, 'switch_ip': switch_ip})
    try:
        return _lookup_all_nos_bindings(port_id=port_id,
                                          switch_ip=switch_ip)
    except c_exc.NOSPortBindingNotFound:
        pass


def _lookup_nos_bindings(query_type, session=None, **bfilter):
    """Look up 'query_type' NOS bindings matching the filter.

    :param query_type: 'all', 'one' or 'first'
    :param session: db session
    :param bfilter: filter for bindings query
    :return: bindings if query gave a result, else
             raise NOSPortBindingNotFound.
    """
    if session is None:
        session = db.get_session()
    query_method = getattr(session.query(
        nos_models_v2.NOSPortBinding).filter_by(**bfilter), query_type)
    try:
        bindings = query_method()
        if bindings:
            return bindings
    except sa_exc.NoResultFound:
        pass
    raise c_exc.NOSPortBindingNotFound(**bfilter)


def _lookup_all_nos_bindings(session=None, **bfilter):
    return _lookup_nos_bindings('all', session, **bfilter)


def _lookup_one_nos_binding(session=None, **bfilter):
    return _lookup_nos_bindings('one', session, **bfilter)


def _lookup_first_nos_binding(session=None, **bfilter):
    return _lookup_nos_bindings('first', session, **bfilter)
