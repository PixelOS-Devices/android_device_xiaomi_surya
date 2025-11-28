#!/usr/bin/env -S PYTHONPATH=../../../tools/extract-utils python3
#
# SPDX-FileCopyrightText: 2024 The LineageOS Project
# SPDX-License-Identifier: Apache-2.0
#

from extract_utils.fixups_blob import (
    BlobFixupCtx,
    File,
    blob_fixup,
    blob_fixups_user_type,
)
from extract_utils.fixups_lib import (
    lib_fixups,
    lib_fixups_user_type,
)
from extract_utils.main import (
    ExtractUtils,
    ExtractUtilsModule,
)
from extract_utils.tools import (
    llvm_objdump_path,
)
from extract_utils.utils import (
    run_cmd,
)

namespace_imports = [
    'device/xiaomi/surya',
    'hardware/qcom-caf/sm8150',
    'hardware/qcom-caf/wlan',
    'hardware/xiaomi',
    'vendor/qcom/opensource/commonsys/display',
    'vendor/qcom/opensource/commonsys-intf/display',
    'vendor/qcom/opensource/dataservices',
    'vendor/qcom/opensource/display',
    'vendor/xiaomi/surya',
]


def blob_fixup_graphic_buffer_size(
    ctx: BlobFixupCtx,
    file: File,
    file_path: str,
    *args,
    **kwargs,
):
    for line in run_cmd(
        [
            llvm_objdump_path,
            '--disassemble-all',
            file_path,
        ]
    ).splitlines():
        line = line.split(maxsplit=5)
        if len(line) != 6:
            continue

        # The size of GraphicBuffer changed from 0x100 to 0xd30
        offset, _, instruction, register, value, _ = line
        if instruction == 'mov' and register[:-1] == 'w0' and value == '#0x100':
            with open(file_path, 'rb+') as f:
                f.seek(int(offset[:-1], 16))
                f.write(b'\x00\xa6\x81\x52')  # AArch64 mov w0, #0xd30


def lib_fixup_vendor_suffix(lib: str, partition: str, *args, **kwargs):
    return f'{lib}_{partition}' if partition == 'vendor' else None


lib_fixups: lib_fixups_user_type = {
    **lib_fixups,
    (
        'com.qualcomm.qti.dpm.api@1.0',
        'libmmosal',
        'vendor.qti.hardware.fm@1.0',
        'vendor.qti.imsrtpservice@3.0',
        'vendor.qti.hardware.wifidisplaysession@1.0',
    ): lib_fixup_vendor_suffix,
}


blob_fixups: blob_fixups_user_type = {
    'system/framework/WfdCommon.jar': blob_fixup()
        .apktool_patch('blob-patches/WfdCommon.patch'),
    'system_ext/priv-app/MiuiCamera/MiuiCamera.apk': blob_fixup()
        .apktool_patch('blob-patches/MiuiCamera'),
    # Replace the S-era Surface vtable connect() call with ANativeWindow perform(NATIVE_WINDOW_API_CONNECT, NATIVE_WINDOW_API_CPU)
    ('system_ext/lib64/libcamera_algoup_jni.xiaomi.so', 'system_ext/lib64/libcamera_mianode_jni.xiaomi.so'): blob_fixup()
        .sig_replace('a8 02 40 f9 e2 03 00 91 41 00 80 52 e0 03 15 aa 08 a9 40 f9 e3 03 1f 2a 00 01 3f d6', 'a0 42 00 91 08 4c 40 f9 a1 01 80 52 42 00 80 52 00 01 3f d6 1f 20 03 d5 1f 20 03 d5'),
    'system_ext/lib64/libwfdservice.so': blob_fixup()
        .replace_needed('android.media.audio.common.types-V4-cpp.so', 'android.media.audio.common.types-V5-cpp.so'),
    'vendor/lib64/libdpps.so': blob_fixup()
        .replace_needed('libtinyxml2.so', 'libtinyxml2-v34.so'),
    ('vendor/lib64/mediadrm/libwvdrmengine.so', 'vendor/lib64/libwvhidl.so'): blob_fixup()
        .add_needed('libcrypto_shim.so'),
    'vendor/etc/init/init.batterysecret.rc': blob_fixup()
        .regex_replace(r'\s+seclabel u:r:batterysecret:s0', ''),
    'vendor/etc/init/init.mi_thermald.rc': blob_fixup()
        .regex_replace(' +seclabel u:r:mi_thermald:s0\n', ''),
    'vendor/lib64/camera/components/com.qti.node.watermark.so': blob_fixup()
        .add_needed('libpiex_shim.so'),
    'vendor/lib64/camera/components/com.vidhance.node.eis.so': blob_fixup()
        .call(blob_fixup_graphic_buffer_size),
    ('vendor/lib64/hw/camera.qcom.so', 'vendor/lib64/libFaceDetectpp-0.5.2.so', 'vendor/lib64/libfacedet.so'): blob_fixup()
        .binary_regex_replace(b'libmegface.so', b'libfacedet.so')
        .binary_regex_replace(b'libMegviiFacepp-0.5.2.so', b'libFaceDetectpp-0.5.2.so')
        .binary_regex_replace(b'megviifacepp_0_5_2_model', b'facedetectpp_0_5_2_model'),
    # Don't mark the front and rear cameras as conflicting, AOSP cameraserver refuses to open both for dual video
    'vendor/lib64/hw/com.qti.chi.override.so': blob_fixup()
        .sig_replace('fb 33 40 f9 f4 2b 40 f9 1b 12 00 b4 f4 11 00 b4', 'fb 33 40 f9 f4 2b 40 f9 90 00 00 14 f4 11 00 b4'),
    ('vendor/lib64/libalAILDC.so', 'vendor/lib64/libalLDC.so', 'vendor/lib64/libalhLDC.so'): blob_fixup()
        .clear_symbol_version('AHardwareBuffer_allocate')
        .clear_symbol_version('AHardwareBuffer_describe')
        .clear_symbol_version('AHardwareBuffer_lock')
        .clear_symbol_version('AHardwareBuffer_release')
        .clear_symbol_version('AHardwareBuffer_unlock'),
    'vendor/lib64/libalRnBRT_GL_GBWRAPPER.so': blob_fixup()
        .add_needed('libui_shim.so'),
    'vendor/lib64/libgoodixhwfingerprint.so': blob_fixup()
        .replace_needed('libvendor.goodix.hardware.biometrics.fingerprint@2.1.so', 'vendor.goodix.hardware.biometrics.fingerprint@2.1.so'),
    ('vendor/lib64/libVDSuperPhotoAPI.so', 'vendor/lib64/libhvx_interface.so', 'vendor/lib64/libmialgo_rfs.so'): blob_fixup()
        .clear_symbol_version('remote_handle_close')
        .clear_symbol_version('remote_handle_invoke')
        .clear_symbol_version('remote_handle_open')
        .clear_symbol_version('remote_register_buf_attr'),
}  # fmt: skip

module = ExtractUtilsModule(
    'surya',
    'xiaomi',
    blob_fixups=blob_fixups,
    lib_fixups=lib_fixups,
    namespace_imports=namespace_imports,
)

if __name__ == '__main__':
    utils = ExtractUtils.device(module)
    utils.run()
