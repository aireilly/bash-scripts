#!/usr/bin/bash

if [ $# = 0 ]; then
echo "Error: you need to provide the filename and output filename as input params in sublime build system"
else

asciidoctor -a toc -a toclevels=4 -a allow-uri-read -a sectanchors -a product-title="OpenShift Container Platform" -a product-version="4.14" -a sno="single-node OpenShift" -a sno-caps="Single-node OpenShift" -a cgu-operator-first="Topology Aware Lifecycle Manager (TALM)" -a cgu-operator-full="Topology Aware Lifecycle Manager" -a cgu-operator="TALM" -a redfish-operator="Bare Metal Event Relay" -a rh-rhacm-first="Red Hat Advanced Cluster Management (RHACM)" -a rh-rhacm="RHACM" -a ztp="GitOps ZTP" -a ztp-first="GitOps zero touch provisioning (ZTP)" -a op-system-first="Red Hat Enterprise Linux CoreOS (RHCOS)" -a op-system="RHCOS" -a rds="telco preview RDS" -a rds-caps="Telco Preview RDS" -a rds-first="Telco preview RDS" -a imagesdir="images" -a icons="font" $1
google-chrome $2
sleep 10
rm -f $2
fi
