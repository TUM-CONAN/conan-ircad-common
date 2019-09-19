#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil

from conans import tools
from fnmatch import fnmatch
from pathlib import Path


def get_c_flags(**kwargs):
    if kwargs.get('is_posix', tools.os_info.is_posix):
        if kwargs.get('is_macos', tools.os_info.is_macos):
            # Our old macos CI is done on a old E5620 Intel(R) Xeon(R) CPU, which doesn't support AVX and f16c
            # CPU with 64-bit extensions, MMX, SSE, SSE2, SSE3, SSSE3, SSE4.1, SSE4.2,
            # POPCNT, AES and PCLMUL instruction set support.
            flags = '-march=westmere'
            flags += ' -mtune=intel'
            flags += ' -mfpmath=sse'
            flags += ' -arch x86_64'
            flags += ' -mmacosx-version-min=10.14'
            flags += ' -DGL_SILENCE_DEPRECATION'
            return flags
        else:
            # CPU with 64-bit extensions, MMX, SSE, SSE2, SSE3, SSSE3, SSE4.1, SSE4.2,
            # POPCNT, AVX, AES, PCLMUL, FSGSBASE instruction set support.
            flags = '-march=sandybridge'
            flags += ' -mtune=generic'
            flags += ' -mfpmath=sse'
            return flags
    else:
        # Windows flags..
        flags = '/favor:blend'
        flags += ' /fp:precise'
        flags += ' /Qfast_transcendentals'
        flags += ' /MP'
        flags += ' /bigobj'
        flags += ' /EHsc'
        flags += ' /D_ENABLE_EXTENDED_ALIGNED_STORAGE'
        return flags


def get_cxx_flags(**kwargs):
    return get_c_flags(**kwargs)


def get_c_flags_release(**kwargs):
    if kwargs.get('is_posix', tools.os_info.is_posix):
        return '-O3 -fomit-frame-pointer -DNDEBUG'
    elif kwargs.get('is_windows', tools.os_info.is_windows):
        return '/O2 /Ob2 /MD /DNDEBUG'
    else:
        return ''


def get_cxx_flags_release(**kwargs):
    return get_c_flags_release(**kwargs)


def get_c_flags_debug(**kwargs):
    if kwargs.get('is_posix', tools.os_info.is_posix):
        return '-Og -g -D_DEBUG'
    elif kwargs.get('is_windows', tools.os_info.is_windows):
        return '/Ox /Oy- /Ob1 /Z7 /MDd /D_DEBUG'
    else:
        return ''


def get_cxx_flags_debug(**kwargs):
    return get_c_flags_debug(**kwargs)


def get_c_flags_relwithdebinfo(**kwargs):
    if kwargs.get('is_posix', tools.os_info.is_posix):
        return '-O3 -g -DNDEBUG'
    elif kwargs.get('is_windows', tools.os_info.is_windows):
        return get_c_flags_release(**kwargs) + ' /Z7'
    else:
        return ''


def get_cxx_flags_relwithdebinfo(**kwargs):
    return get_c_flags_relwithdebinfo(**kwargs)


def get_full_c_flags(**kwargs):
    c_flags = get_c_flags(**kwargs)
    build_type = str(kwargs.get('build_type', 'debug')).lower()

    if build_type == 'debug':
        c_flags += ' ' + get_c_flags_debug(**kwargs)
    elif build_type == 'release':
        c_flags += ' ' + get_c_flags_release(**kwargs)
    elif build_type == 'relwithdebinfo':
        c_flags += ' ' + get_c_flags_relwithdebinfo(**kwargs)

    return c_flags


def get_full_cxx_flags(**kwargs):
    return get_full_c_flags(**kwargs)


def generate_cmake_wrapper(**kwargs):
    # Get the cmake wrapper path
    cmakelists_path = kwargs.get('cmakelists_path', 'CMakeLists.txt')
    cmakelists_exists = Path(cmakelists_path).is_file()

    # If there is an existing CMakeLists.txt, we must rename it
    if cmakelists_exists:
        shutil.move(cmakelists_path, cmakelists_path + '.upstream')

    # Write the file content
    with open(cmakelists_path, 'w') as cmake_wrapper:
        cmake_wrapper.write('cmake_minimum_required(VERSION 3.0)\n')
        cmake_wrapper.write('project(cmake_wrapper)\n')
        cmake_wrapper.write('include(conanbuildinfo.cmake)\n')
        cmake_wrapper.write('conan_basic_setup()\n')

        # Add common flags
        cmake_wrapper.write(
            'add_compile_options(' + get_cxx_flags() + ')\n'
        )

        # Get build type, defaulting to debug
        build_type = str(kwargs.get('build_type', 'debug')).lower()

        if build_type == 'release':
            # Add release flags
            cmake_wrapper.write(
                'add_compile_options(' + get_cxx_flags_release() + ')\n'
            )
        elif build_type == 'debug':
            # Add debug flags
            debug_flags = get_cxx_flags_debug()
            cmake_wrapper.write(
                'add_compile_options(' + debug_flags + ')\n'
            )

            # Special case on windows, which doesn't support mixing /Ox with /RTC1
            if tools.os_info.is_windows and (
                '/O1' in debug_flags or '/O2' in debug_flags or '/Ox' in debug_flags
            ):
                cmake_wrapper.write(
                    'set(CMAKE_C_FLAGS_DEBUG_INIT ' + debug_flags + ')\n'
                )
                cmake_wrapper.write(
                    'set(CMAKE_CXX_FLAGS_DEBUG_INIT ' + debug_flags + ')\n'
                )
                cmake_wrapper.write(
                    'string(REGEX REPLACE "/RTC[1csu]+" "" CMAKE_C_FLAGS_DEBUG "${CMAKE_C_FLAGS_DEBUG}")\n'
                )
                cmake_wrapper.write(
                    'string(REGEX REPLACE "/RTC[1csu]+" "" CMAKE_CXX_FLAGS_DEBUG "${CMAKE_CXX_FLAGS_DEBUG}")\n'
                )
        elif build_type == 'relwithdebinfo':
            # Add relwithdebinfo flags
            cmake_wrapper.write(
                'add_compile_options(' + get_cxx_flags_relwithdebinfo() + ')\n'
            )

        # Write additional options
        additional_options = kwargs.get('additional_options', None)
        if additional_options:
            cmake_wrapper.write(additional_options + '\n')

        # Write the original subdirectory / include
        if cmakelists_exists:
            cmake_wrapper.write('include("CMakeLists.txt.upstream")\n')
        else:
            source_subfolder = kwargs.get('source_subfolder', 'source_subfolder')
            cmake_wrapper.write('add_subdirectory("' + source_subfolder + '")\n')


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
                    fix_conan_dependency_path(
                        conanfile, wildcard_file, requirement)
