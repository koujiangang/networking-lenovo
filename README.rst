
===============================
Lenovo Networking Plugin for Openstack Neutron
===============================

This site contains the Lenovo vendor code for Openstack Neutron ML2 Driver

* Free software: Apache license
* Bugs: http://bugs.launchpad.net/networking-lenovo

Overview
--------

Openstack is an open source infrastructure initiative for creating and managing large groups of virtual private servers in a cloud computing environment. Lenovo’s Networking Neutron Plugin provides a means to orchestrate VLANs on Lenovo’s physical switches. In cloud environments where VMs are hosted by physical servers, the VMs see a new virtual access layer provided by the host machine. 

This new access layer can be typically created via many mechanisms e.g. Linux Bridges or a Virtual Switches. The policies of the virtual access layer (virtual network), when set must now be coordinated with the policies set in the hardware switches. Lenovo’s Neutron Plugin helps in coordinating this behavior automatically without any intervention from the administrator.  The illustration below provides an architectural overview of how Lenovo’s ML2 Plugin and switches fits into an Openstack deployment.

.. image:: http://s6.postimg.org/3r7rsk19d/lenovo_openstack_driver.gif

User Guide
--------

The Lenovo Networking Neutron ML2 User Guide is provided to assist with installation and setup of this driver -  `Download User Guide`_. 

.. _Download User Guide: http://publib.boulder.ibm.com/infocenter/systemx/documentation/topic/com.lenovo.switchmgt.openstack_neutron_plugin.doc/openstack_neutron_plugin.html

ML2 Driver Details 
-------

More details can be found on Lenovo Openstack Neutron Wiki page: https://wiki.openstack.org/wiki/Neutron/ML2/LenovoML2Mechanism

