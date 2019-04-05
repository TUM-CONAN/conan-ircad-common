#!/usr/bin/env python
# -*- coding: utf-8 -*-

from conans import ConanFile


class CommonConan(ConanFile):
    name = 'common'
    version = '1.0.0'
    license = 'MIT'
    description = 'Helper functions for conan'
    exports = '*'
    url = 'https://git.ircad.fr/conan/conan-common'
    build_policy = 'missing'

    def package(self):
        self.copy('common.py')

    def package_info(self):
        self.env_info.PYTHONPATH.append(self.package_folder)
