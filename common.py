#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from conans import tools
from fnmatch import fnmatch


def get_c_flags(**kwargs):
    if kwargs.get('is_posix', tools.os_info.is_posix):
        if kwargs.get('is_macos', tools.os_info.is_macos):
            # Our old macos CI is done on a old E5620 Intel(R) Xeon(R) CPU, which doesn't support AVX and f16c
            # CPU with 64-bit extensions, MMX, SSE, SSE2, SSE3, SSSE3, SSE4.1, SSE4.2,
            # POPCNT, AES and PCLMUL instruction set support.
            return '-march=westmere -mtune=intel -mfpmath=sse -arch x86_64 -mmacosx-version-min=10.14 -DGL_SILENCE_DEPRECATION'
        else:
            # CPU with 64-bit extensions, MMX, SSE, SSE2, SSE3, SSSE3, SSE4.1, SSE4.2,
            # POPCNT, AVX, AES, PCLMUL, FSGSBASE, RDRND and F16C instruction set support.
        return '/favor:blend /fp:precise /Qfast_transcendentals /arch:AVX /MP /bigobj /EHsc /D_ENABLE_EXTENDED_ALIGNED_STORAGE'
    else:
        return ''


def get_cxx_flags(**kwargs):
    return get_c_flags(**kwargs)


def get_c_flags_release(**kwargs):
    if kwargs.get('is_posix', tools.os_info.is_posix):
        return get_c_flags(**kwargs) + ' -O3 -fomit-frame-pointer -DNDEBUG'
    elif kwargs.get('is_windows', tools.os_info.is_windows):
        return get_c_flags(**kwargs) + ' /O2 /Ob2 /MD /DNDEBUG'
    else:
        return ''


def get_cxx_flags_release(**kwargs):
    return get_c_flags_release(**kwargs)


def get_c_flags_debug(**kwargs):
    if kwargs.get('is_posix', tools.os_info.is_posix):
        return get_c_flags(**kwargs) + ' -Og -g -D_DEBUG'
    elif kwargs.get('is_windows', tools.os_info.is_windows):
        return get_c_flags(**kwargs) + ' /Ox /Oy- /Ob1 /Z7 /MDd /D_DEBUG'
    else:
        return ''


def get_cxx_flags_debug(**kwargs):
    return get_c_flags_release(**kwargs)


def get_c_flags_relwithdebinfo(**kwargs):
    if kwargs.get('is_posix', tools.os_info.is_posix):
        return get_c_flags(**kwargs) + ' -O3 -g -DNDEBUG'
    elif kwargs.get('is_windows', tools.os_info.is_windows):
        return get_c_flags_release(**kwargs) + ' /Z7'
    else:
        return ''


def get_cxx_flags_relwithdebinfo(**kwargs):
    return get_c_flags_relwithdebinfo(**kwargs)


def get_full_c_flags(**kwargs):
    build_type = kwargs.get('build_type', 'debug').lower()

    if build_type == 'debug':
        return get_c_flags_debug(**kwargs)
    elif build_type == 'release':
        return get_c_flags_release(**kwargs)
    elif build_type == 'relwithdebinfo':
        return get_c_flags_relwithdebinfo(**kwargs)
    else:
        return ''


def get_full_cxx_flags(**kwargs):
    return get_full_c_flags(**kwargs)


def get_cuda_version():
    return ['9.2', '10.0', '10.1', 'None']


def get_cuda_arch():
    return ['3.0', '3.5', '5.0', '5.2', '6.1']


def fix_conan_dependency_path(conanfile, file_path, package_name):
    try:
        tools.replace_in_file(
            file_path,
            conanfile.deps_cpp_info[package_name].rootpath.replace('\\', '/'),
            "${CONAN_" + package_name.upper() + "_ROOT}",
            strict=False
        )
    except Exception:
        conanfile.output.info("Ignoring {0}...".format(package_name))


def fix_conan_path(conanfile, root, wildcard):
    for path, subdirs, names in os.walk(root):
        for name in names:
            if fnmatch(name, wildcard):
                wildcard_file = os.path.join(path, name)

                tools.replace_in_file(
                    wildcard_file,
                    conanfile.package_folder.replace('\\', '/'),
                    '${CONAN_' + conanfile.name.upper() + '_ROOT}',
                    strict=False
                )

                for requirement in conanfile.requires:
                    fix_conan_dependency_path(conanfile, wildcard_file, requirement)
