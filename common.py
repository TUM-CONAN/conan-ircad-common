#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil
import re

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
        flags += ' /arch:AVX'
        flags += ' /MP'
        flags += ' /bigobj'
        flags += ' /EHsc'
        flags += ' /D_ENABLE_EXTENDED_ALIGNED_STORAGE'
        return flags


def get_cxx_flags(**kwargs):
    return get_c_flags(**kwargs)


def get_release_c_flags(**kwargs):
    if kwargs.get('is_posix', tools.os_info.is_posix):
        return '-O3 -fomit-frame-pointer -DNDEBUG'
    elif kwargs.get('is_windows', tools.os_info.is_windows):
        return '/O2 /Ob2 /MD /DNDEBUG'
    else:
        return ''


def get_release_cxx_flags(**kwargs):
    return get_release_c_flags(**kwargs)


def get_debug_c_flags(**kwargs):
    if kwargs.get('is_posix', tools.os_info.is_posix):
        return '-Og -g -D_DEBUG'
    elif kwargs.get('is_windows', tools.os_info.is_windows):
        return '/Ox /Oy- /Ob1 /Z7 /MDd /D_DEBUG'
    else:
        return ''


def get_debug_cxx_flags(**kwargs):
    return get_debug_c_flags(**kwargs)


def get_relwithdebinfo_c_flags(**kwargs):
    if kwargs.get('is_posix', tools.os_info.is_posix):
        return '-O3 -g -DNDEBUG'
    elif kwargs.get('is_windows', tools.os_info.is_windows):
        return get_release_c_flags(**kwargs) + ' /Z7'
    else:
        return ''


def get_relwithdebinfo_cxx_flags(**kwargs):
    return get_relwithdebinfo_c_flags(**kwargs)


def get_thorough_debug_c_flags(**kwargs):
    if kwargs.get('is_posix', tools.os_info.is_posix):
        return '-O0 -g3 -D_DEBUG'
    elif kwargs.get('is_windows', tools.os_info.is_windows):
        return '/Od /Ob0 /RTC1 /sdl /Z7 /MDd /D_DEBUG'
    else:
        return ''


def get_thorough_debug_cxx_flags(**kwargs):
    return get_thorough_debug_c_flags(**kwargs)


def get_full_c_flags(**kwargs):
    c_flags = get_c_flags(**kwargs)
    build_type = str(kwargs.get('build_type', 'debug')).lower()

    if build_type == 'debug':
        c_flags += ' ' + get_debug_c_flags(**kwargs)
    elif build_type == 'release':
        c_flags += ' ' + get_release_c_flags(**kwargs)
    elif build_type == 'relwithdebinfo':
        c_flags += ' ' + get_relwithdebinfo_c_flags(**kwargs)

    return c_flags


def get_full_cxx_flags(**kwargs):
    return get_full_c_flags(**kwargs)


def generate_cmake_wrapper(**kwargs):
    # Get the cmake wrapper path
    cmakelists_path = kwargs.get('cmakelists_path', 'CMakeLists.txt')
    cmakelists_exists = Path(cmakelists_path).is_file()

    # If there is an existing CMakeLists.txt, because of some strange package like libsgm, we must rename it
    if cmakelists_exists:
        shutil.move(cmakelists_path, cmakelists_path + '.upstream')

    # Write the file content
    with open(cmakelists_path, 'w') as cmake_wrapper:
        cmake_wrapper.write('cmake_minimum_required(VERSION 3.15)\n')

        # New policies management. It must be done before 'project(cmake_wrapper)'
        new_policies = kwargs.get('new_policies', None)
        if new_policies:
            for new_policy in new_policies:
                cmake_wrapper.write("cmake_policy(SET {0} NEW)\n".format(new_policy))

        # Old policies management. It must be done before 'project(cmake_wrapper)'
        old_policies = kwargs.get('old_policies', None)
        if old_policies:
            for old_policy in old_policies:
                cmake_wrapper.write("cmake_policy(SET {0} OLD)\n".format(old_policy))

        cmake_wrapper.write('project(cmake_wrapper)\n')
        cmake_wrapper.write(
            'if(EXISTS "${CMAKE_BINARY_DIR}/conanbuildinfo.cmake")\n'
        )
        cmake_wrapper.write(
            '   include(${CMAKE_BINARY_DIR}/conanbuildinfo.cmake)\n'
        )
        cmake_wrapper.write(
            'elseif(EXISTS "${CMAKE_BINARY_DIR}/../conanbuildinfo.cmake")\n'
        )
        cmake_wrapper.write(
            '   include(${CMAKE_BINARY_DIR}/../conanbuildinfo.cmake)\n'
        )
        cmake_wrapper.write(
            'elseif(EXISTS "${CMAKE_BINARY_DIR}/../../conanbuildinfo.cmake")\n'
        )
        cmake_wrapper.write(
            '   include(${CMAKE_BINARY_DIR}/../../conanbuildinfo.cmake)\n'
        )
        cmake_wrapper.write(
            'elseif(EXISTS "${CMAKE_BINARY_DIR}/../../../conanbuildinfo.cmake")\n'
        )
        cmake_wrapper.write(
            '   include(${CMAKE_BINARY_DIR}/../../../conanbuildinfo.cmake)\n'
        )
        cmake_wrapper.write('endif()\n')
        cmake_wrapper.write('conan_basic_setup()\n')

        # Add common flags
        cmake_wrapper.write(
            'add_compile_options(' + get_cxx_flags() + ')\n'
        )

        # Disable warnings and error because of warnings
        cmake_wrapper.write(
            'add_compile_options("$<$<CXX_COMPILER_ID:MSVC>:/W0;/WX->")\n'
        )

        cmake_wrapper.write(
            'add_compile_options("$<$<CXX_COMPILER_ID:GNU,Clang,AppleClang>:-w;-Wno-error>")\n'
        )

        # Get build type, defaulting to debug
        build_type = str(kwargs.get('build_type', 'debug')).lower()

        if build_type == 'release':
            # Add release flags
            cmake_wrapper.write(
                'add_compile_options(' + get_release_cxx_flags() + ')\n'
            )
        elif build_type == 'debug':
            # Add debug flags
            debug_flags = get_debug_cxx_flags()
            cmake_wrapper.write(
                'add_compile_options(' + debug_flags + ')\n'
            )

            # Special case on windows, which doesn't support mixing /Ox with /RTC1
            if tools.os_info.is_windows and (
                '/O1' in debug_flags or '/O2' in debug_flags or '/Ox' in debug_flags
            ):
                cmake_wrapper.write(
                    'string(REGEX REPLACE "/RTC[1csu]+" "" CMAKE_C_FLAGS_DEBUG "${CMAKE_C_FLAGS_DEBUG}")\n'
                )
                cmake_wrapper.write(
                    'string(REGEX REPLACE "/RTC[1csu]+" "" CMAKE_CXX_FLAGS_DEBUG "${CMAKE_CXX_FLAGS_DEBUG}")\n'
                )
        elif build_type == 'relwithdebinfo':
            # Add relwithdebinfo flags
            cmake_wrapper.write(
                'add_compile_options(' + get_relwithdebinfo_cxx_flags() + ')\n'
            )

        # Write CUDA specific code
        setup_cuda = kwargs.get('setup_cuda', False)

        if setup_cuda:
            cmake_wrapper.write(
                'find_package(CUDA)\n'
            )

            cmake_wrapper.write(
                'CUDA_SELECT_NVCC_ARCH_FLAGS(ARCH_FLAGS ' + ' '.join(get_cuda_arch()) + ')\n'
            )

            cmake_wrapper.write(
                'LIST(APPEND CUDA_NVCC_FLAGS ${ARCH_FLAGS})\n'
            )

            # Propagate host CXX flags
            host_cxx_flags = ",\\\""
            host_cxx_flags += get_full_cxx_flags(build_type=build_type).replace(' ', "\\\",\\\"")
            host_cxx_flags += "\\\""

            cmake_wrapper.write(
                'LIST(APPEND CUDA_NVCC_FLAGS -Xcompiler ' + host_cxx_flags + ')\n'
            )

        # Write additional options
        additional_options = kwargs.get('additional_options', None)
        if additional_options:
            cmake_wrapper.write(additional_options + '\n')

        # Write the original subdirectory / include
        if cmakelists_exists:
            cmake_wrapper.write('include("CMakeLists.txt.upstream")\n')
        else:
            source_subfolder = kwargs.get(
                'source_subfolder', 'source_subfolder'
            )
            cmake_wrapper.write(
                'add_subdirectory("' + source_subfolder + '")\n'
            )


def get_cuda_version():
    return ['9.2', '10.0', '10.1', 'None']


def get_cuda_arch():
    return ['3.0', '3.5', '3.7', '5.0', '5.2', '6.0', '6.1', '7.0', '7.5']


def __fix_conan_dependency_path(conanfile, file_path, package_name):
    try:
        tools.replace_in_file(
            file_path,
            conanfile.deps_cpp_info[package_name].rootpath.replace('\\', '/'),
            "${CONAN_" + package_name.upper() + "_ROOT}",
            strict=False
        )
    except Exception:
        conanfile.output.info("Ignoring {0}...".format(package_name))


def __cmake_fix_macos_sdk_path(conanfile, file_path):
    try:
        # Read in the file
        with open(file_path, 'r') as file:
            file_data = file.read()

        if file_data:
            # Replace the target string
            pattern = (r';/Applications/Xcode\.app/Contents/Developer'
                       r'/Platforms/MacOSX\.platform/Developer/SDKs/MacOSX\d\d\.\d\d\.sdk/usr/include')

            # Match sdk path
            file_data = re.sub(pattern, '', file_data, re.M)

            # Write the file out again
            with open(file_path, 'w') as file:
                file.write(file_data)

    except Exception:
        conanfile.output.info(
            "Skipping macOS SDK fix on {0}...".format(file_path)
        )


def fix_conan_path(
    conanfile,
    root,
    wildcard,
    build_folder=None
):
    # Normalization
    package_folder = conanfile.package_folder.replace('\\', '/')

    if build_folder:
        build_folder = build_folder.replace('\\', '/')

    conan_root = '${CONAN_' + conanfile.name.upper() + '_ROOT}'

    # Recursive walk
    for path, subdirs, names in os.walk(root):
        for name in names:
            if fnmatch(name, wildcard):
                wildcard_file = os.path.join(path, name)

                # Fix package_folder paths
                tools.replace_in_file(
                    wildcard_file, package_folder, conan_root, strict=False
                )

                # Fix build folder paths
                if build_folder:
                    tools.replace_in_file(
                        wildcard_file, build_folder, conan_root, strict=False
                    )

                # Fix specific macOS SDK paths
                if tools.os_info.is_macos:
                    __cmake_fix_macos_sdk_path(
                        conanfile, wildcard_file
                    )

                # Fix dependencies paths
                for requirement in conanfile.requires:
                    __fix_conan_dependency_path(
                        conanfile, wildcard_file, requirement
                    )
