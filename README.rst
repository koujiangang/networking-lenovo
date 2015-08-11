
===============================
Lenovo Networking Plugin for Openstack Neutron
===============================

Networking Lenovo contains the Lenovo vendor code for Openstack Neutron

* Free software: Apache license
* Documentation: http://docs.openstack.org/developer/networking-lenovo
* Source: http://git.openstack.org/cgit/stackforge/networking-lenovo
* Bugs: http://bugs.launchpad.net/networking-lenovo

Overview
--------

Openstack is an open source infrastructure initiative for creating and managing large groups of virtual private servers in a cloud computing environment. Lenovo’s Networking Neutron Plugin provides a means to orchestrate VLANs on Lenovo’s physical switches. In cloud environments where VMs are hosted by physical servers, the VMs see a new virtual access layer provided by the host machine. 

This new access layer can be typically created via many mechanisms e.g. Linux Bridges or a Virtual Switches. The policies of the virtual access layer (virtual network), when set must now be coordinated with the policies set in the hardware switches. Lenovo’s Neutron Plugin helps in coordinating this behavior automatically without any intervention from the administrator.  The illustration below provides an architectural overview of how Lenovo’s ML2 Plugin and switches fits into an Openstack deployment.

.. image:: http://s6.postimg.org/3r7rsk19d/lenovo_openstack_driver.gif

User Guide
--------

The Lenovo Networking Openstack User Guide is provided to assist with installation and setup of this plugin here  `Download User Guide`_. 

.. _Download User Guide: http://s000.tinyupload.com/index.php?file_id=78198809758653746047/



* TODO

