# Copyright (c) 2012, Calxeda Inc.
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
# * Neither the name of Calxeda Inc. nor the names of its contributors
# may be used to endorse or promote products derived from this software
# without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDERS OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS
# OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
# TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF
# THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
# DAMAGE.


import os
import shutil
import tempfile
import unittest

from cxmanage.simg import get_simg_header
from cxmanage.tftp import InternalTftp

from cxmanage_test import random_file, TestImage

class ImageTest(unittest.TestCase):
    """ Tests involving cxmanage images

    These will rely on an internally hosted TFTP server. """

    def setUp(self):
        self.work_dir = tempfile.mkdtemp(prefix="cxmanage_test-")

        # Set up an internal server
        self.tftp = InternalTftp()

    def tearDown(self):
        shutil.rmtree(self.work_dir)

    def test_upload(self):
        """ Test image creation and upload """
        imglen = 1024
        priority = 1
        daddr = 12345

        # Create image
        filename = random_file(self.work_dir, imglen)
        contents = open(filename).read()
        image = TestImage(filename, "RAW")

        # Upload image and delete file
        image_filename = image.upload(self.tftp, priority, daddr)
        os.remove(filename)

        # Download image
        filename = "%s/%s" % (self.work_dir, image_filename)
        self.tftp.get_file(image_filename, filename)

        # Examine image
        simg = open(filename).read()
        header = get_simg_header(simg)
        self.assertEqual(header.priority, priority)
        self.assertEqual(header.imglen, imglen)
        self.assertEqual(header.daddr, daddr)
        self.assertEqual(simg[header.imgoff:], contents)

    def test_multiple_uploads(self):
        """ Test to make sure FDs are being closed """
        # Create image
        filename = random_file(self.work_dir, 1024)
        contents = open(filename).read()
        image = TestImage(filename, "RAW")

        for x in xrange(2048):
            image.upload(self.tftp, 0, 0)
