FROM 192.168.24.1:8787/rhosp13/openstack-neutron-server:13.0-58
USER root
RUN yum install -y wget

#add and install repo
WORKDIR /tmp
RUN wget https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
ADD epel-release-latest-7.noarch.rpm /usr/local/
RUN rpm -ivh /usr/local/epel-release-latest-7.noarch.rpm

RUN yum install -y python-pip
RUN pip install ncclient==0.4.2
RUN pip install pysnmp

RUN yum install git -y
RUN if [ -d "/tmp/networking-lenovo" ]; then rm -rf /tmp/networking-lenovo; fi
RUN git clone https://github.com/lenovo-network/networking-lenovo.git -b vxlan /tmp/networking-lenovo
WORKDIR /tmp/networking-lenovo
RUN python setup.py install
RUN sed 's/^ *mechanism_drivers *= */&lenovo,/g' -i /etc/neutron/plugins/ml2/ml2_conf.ini
#RUN neutron-db-manage --config-file /etc/neutron/neutron.conf --config-file /etc/neutron/plugins/ml2/ml2_conf.ini upgrade head
#RUN service neutron-server restart
USER neutron
