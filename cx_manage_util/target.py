#!/bin/env python

import socket, time

from pyipmi import make_bmc, IpmiError
from pyipmi.bmc import LanBMC

class Target:
    """ Contains info for a single target. A target consists of a hostname,
    an username, and a password. """

    def __init__(self, address, username, password):
        self.address = address
        self.username = username
        self.password = password
        self.bmc = make_bmc(LanBMC, hostname=address,
                username=username, password=password)

    def get_fabric_ipinfo(self, tftp, filename):
        """ Send an IPMI get_fabric_ipinfo command to this target

        Note that this method puts the ip_info file on the TFTP server
        but does not retrieve it locally. """
        tftp_address = self._get_tftp_address(tftp)
        self.bmc.get_fabric_ipinfo(filename, tftp_address)

    def power_command(self, command):
        """ Send an IPMI power command to this target """
        try:
            self.bmc.handle.chassis_control(mode=command)
        except IpmiError:
            raise ValueError("Failed to send power command")

    def power_status(self):
        """ Return power status reported by IPMI """
        try:
            if self.bmc.handle.chassis_status().power_on:
                return "on"
            else:
                return "off"
        except IpmiError:
            raise ValueError("Failed to retrieve power status")

    def update_firmware(self, tftp, image_type,
            filename, slot_arg, skip_reset=False):
        """ Update firmware on this target. """
        tftp_address = self._get_tftp_address(tftp)

        # Get all available slots
        results = self.bmc.get_firmware_info()[:-1]
        if not results:
            raise ValueError("Failed to retrieve firmware info")
        try:
            # Image type is an int
            slots = [x.slot for x in results[:-1] if
                    int(x.type.split()[0]) == int(image_type)]
        except ValueError:
            # Image type is a string
            slots = [x.slot for x in results[:-1] if
                    x.type.split()[1][1:-1] == image_type.upper()]

        # Select slots
        if slot_arg == "PRIMARY":
            if len(slots) < 1:
                raise ValueError("No primary slot found on host")
            slots = slots[:1]
        elif slot_arg == "SECONDARY":
            if len(slots) < 2:
                raise ValueError("No secondary slot found on host")
            slots = slots[1:2]
        elif slot_arg == "ALL":
            pass
        else:
            raise ValueError("Invalid slot argument")

        for slot in slots:
            # Send firmware update command
            result = self.bmc.update_firmware(filename,
                    slot, image_type, tftp_address)
            handle = result.tftp_handle_id

            # Wait for update to finish
            time.sleep(1)
            status = self.bmc.get_firmware_status(handle).status
            while status == "In progress":
                time.sleep(1)
                status = self.bmc.get_firmware_status(handle).status

            # Activate firmware on completion
            if status == "Complete":
                # Verify crc
                if not self.bmc.check_firmware(slot).error:
                    self.bmc.activate_firmware(slot)
                else:
                    raise ValueError("Node reported crc32 check failure")
            else:
                raise ValueError("Node reported transfer failure")

        if image_type == "SOC_ELF" and not skip_reset:
            self.mc_reset()

    def mc_reset(self):
        """ Send an IPMI MC reset command to the target """
        try:
            self.bmc.mc_reset("cold")
        except IpmiError:
            raise ValueError("Failed to send MC reset command")

    def _get_tftp_address(self, tftp):
        """ Get the TFTP server address
        Returns a string in ip:port format """
        # Get address
        if tftp.is_internal() and tftp.get_address() == None:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((self.address, 0))
            address = s.getsockname()[0]
            s.close()
        else:
            address = tftp.get_address()

        # Get port
        port = tftp.get_port()

        # Return in address:port form
        return "%s:%i" % (address, port)