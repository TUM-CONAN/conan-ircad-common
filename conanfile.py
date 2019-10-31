#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os

from conans import ConanFile


class CommonConan(ConanFile):
    name = 'common'
    upstream_version = '1.0.2'
    package_revision = ''
    version = "{0}{1}".format(upstream_version, package_revision)

    exports = [
        'common.py'
    ]

    description = 'Helper functions for conan'
    url = 'https://git.ircad.fr/conan/conan-common'
    build_policy = 'missing'

    def configure(self):
        if 'CI' not in os.environ:
            os.environ["CONAN_SYSREQUIRES_MODE"] = "verify"

    def package(self):
        self.copy('common.py')

    def package_info(self):
        self.env_info.PYTHONPATH.append(self.package_folder)
