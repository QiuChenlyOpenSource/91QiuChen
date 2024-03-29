import json
import os
import plistlib
import subprocess
import shutil
from pathlib import Path
import time


def read_input(prompt):
    return input(prompt).strip().lower()


def parse_app_info(app_base_locate, app_info_file):
    with open(app_info_file, "rb") as f:
        app_info = plistlib.load(f)
    app_info = {
        "appBaseLocate": app_base_locate,
        "CFBundleIdentifier": app_info.get("CFBundleIdentifier"),
        "CFBundleVersion": app_info.get("CFBundleVersion", ""),
        "CFBundleShortVersionString": app_info.get("CFBundleShortVersionString", ""),
        "CFBundleName": app_info.get("CFBundleExecutable", ""),
        "CFBundleExecutable": app_info.get("CFBundleExecutable", ""),
    }
    return app_info


def scan_apps():
    appList = []
    base_dirs = ["/Applications", "/Applications/Setapp"]

    for base_dir in base_dirs:
        if not os.path.exists(base_dir):
            continue
        lst = os.listdir(base_dir)
        for app in lst:
            app_info_file = os.path.join(base_dir, app, "Contents", "Info.plist")
            if not os.path.exists(app_info_file):
                continue
            try:
                appList.append(parse_app_info(base_dir + "/" + app, app_info_file))
                # print("检查本地App:", app_info_file)
            except Exception:
                continue

    return appList


def check_compatible(
    compatible_version_code,
    compatible_version_subcode,
    app_version_code,
    app_subversion_code,
):
    if compatible_version_code is None and compatible_version_subcode is None:
        return True

    if compatible_version_code:
        for code in compatible_version_code:
            if app_version_code == code:
                return True

    if compatible_version_subcode:
        for code in compatible_version_subcode:
            if app_subversion_code == code:
                return True

    return False


def main():
    try:
        with open("config.json", "r") as f:
            config = json.load(f)

        base_public_config = config["basePublicConfig"]
        app_list = config["AppList"]
        proc_version = config["Version"]

        print("  ___  _        ____ _                _  ")
        print(" / _ \\(_)_   _ / ___| |_   ___ _ __ | |_   _ ")
        print("| | | | | | | | |  | '_ \\ / _ \\ '_ \\| | | | |")
        print("| |_| | | |_| | |__| | | |  __/ | | | | |_| |")
        print(" \\__\\_\\_\\__,_|\\____|_| |_|\\___|_| |_|_|\\__, |")
        print("                                        |___/")
        print(f"自动注入版本号: {proc_version}")
        print("Original Design By QiuChenly(github.com/qiuchenly), Py ver. by X1a0He")
        print("注入时请根据提示输入'y' 或者按下回车键跳过这一项。")

        start_time = time.time()
        install_apps = scan_apps()
        end_time = time.time()
        elapsed_time = end_time - start_time
        print("扫描本地App耗时: {:.2f}s".format(elapsed_time))
        app_Lst = []
        for app in app_list:
            package_name = app["packageName"]
            if isinstance(package_name, list):
                for name in package_name:
                    tmp = app.copy()
                    tmp["packageName"] = name
                    app_Lst.append(tmp)
            else:
                app_Lst.append(app)

        for app in app_Lst:
            package_name = app.get("packageName")
            app_base_locate = app.get("appBaseLocate")
            bridge_file = app.get("bridgeFile")
            inject_file = app.get("injectFile")
            support_version = app.get("supportVersion")
            support_subversion = app.get("supportSubVersion")
            extra_shell = app.get("extraShell")
            need_copy_to_app_dir = app.get("needCopyToAppDir")
            deep_sign_app = app.get("deepSignApp")
            disable_library_validate = app.get("disableLibraryValidate")
            entitlements = app.get("entitlements")
            no_sign_target = app.get("noSignTarget")
            no_deep = app.get("noDeep")
            tccutil = app.get("tccutil")
            useOptool = app.get("useOptool")
            auto_handle_setapp = app.get("autoHandleSetapp")

            local_app = [
                local_app
                for local_app in install_apps
                if local_app["CFBundleIdentifier"] == package_name
            ]

            if not local_app and (
                app_base_locate is None or not os.path.isdir(app_base_locate)
            ):
                continue

            if not local_app:
                # print("[🔔] 此App包不是常见类型结构，请注意当前App注入的路径是 {appBaseLocate}".format(appBaseLocate=app_base_locate))
                # print("读取的是 {appBaseLocate}/Contents/Info.plist".format(appBaseLocate=app_base_locate))
                local_app.append(
                    parse_app_info(
                        app_base_locate,
                        os.path.join(app_base_locate, "Contents", "Info.plist"),
                    )
                )

            local_app = local_app[0]
            if app_base_locate is None:
                app_base_locate = local_app["appBaseLocate"]

            if bridge_file is None:
                bridge_file = base_public_config.get("bridgeFile", bridge_file)

            if auto_handle_setapp is not None:
                bridge_file = "/Contents/MacOS/"
                executableAppName = local_app["CFBundleExecutable"]
                inject_file = os.path.basename(
                    app_base_locate + bridge_file + executableAppName
                )
                print(
                    f"======== Setapp下一个App的处理结果如下 [{app_base_locate}] [{bridge_file}] [{inject_file}]"
                )

            if not check_compatible(
                support_version,
                support_subversion,
                local_app["CFBundleShortVersionString"],
                local_app["CFBundleVersion"],
            ):
                print(
                    f"[😅] [{local_app['CFBundleName']}] - [{local_app['CFBundleShortVersionString']}] - [{local_app['CFBundleIdentifier']}]不是受支持的版本，跳过注入😋。"
                )
                continue

            print(
                f"[🤔] [{local_app['CFBundleName']}] - [{local_app['CFBundleShortVersionString']}] 是受支持的版本，是否需要注入？y/n(默认n)"
            )
            action = read_input("").strip().lower()
            if action != "y":
                continue
            print(f"开始注入App: {package_name}")

            subprocess.run(["xattr", "-cr", app_base_locate])

            # dest = os.path.join(app_base_locate, bridge_file, inject_file)
            dest = rf"{app_base_locate}{bridge_file}{inject_file}"
            backup = rf"{dest}_backup"

            if os.path.exists(backup):
                print("备份的原始文件已经存在,需要直接用这个文件注入吗？y/n(默认y)")
                action = read_input("").strip().lower()
                if action == "n":
                    os.remove(backup)
                    shutil.copy(dest, backup)
            else:
                shutil.copy(dest, backup)

            current = Path(__file__).resolve()

            sh = f"chmod +x {current.parent}/tool/insert_dylib && chmod +x {current.parent}/tool/optool"
            subprocess.run(sh, shell=True)

            sh = (
                f"sudo {current.parent}/tool/optool install -p '{current.parent}/tool/Rel_QiuChenly.dylib' -t '{dest}'"
                if useOptool is not None
                else f"sudo {current.parent}/tool/insert_dylib '{current.parent}/tool/Rel_QiuChenly.dylib' '{backup}' '{dest}'"
            )

            if need_copy_to_app_dir:
                source_dylib = f"{current.parent}/tool/Rel_QiuChenly.dylib"
                destination_dylib = (
                    f"'{app_base_locate}{bridge_file}Rel_QiuChenly.dylib'"
                )
                subprocess.run(f"cp {source_dylib} {destination_dylib}", shell=True)
                # shutil.copy(source_dylib, destination_dylib)
                insert_command = rf"sudo cp '{dest}' /tmp/app && sudo {current.parent}/tool/optool install -p {destination_dylib} -t /tmp/app --resign && sudo cp /tmp/app '{dest}'"
                sh = (
                    insert_command
                    if useOptool
                    else rf"sudo {current.parent}/tool/insert_dylib {destination_dylib} '{backup}' '{dest}'"
                )

            subprocess.run(sh, shell=True)

            sign_prefix = "codesign -f -s - --timestamp=none --all-architectures"

            if no_deep is None:
                print("Need Deep Sign.")
                sign_prefix += " --deep"

            if entitlements is not None:
                sign_prefix += f" --entitlements {current.parent}/tool/{entitlements}"

            if no_sign_target is None:
                print("开始签名...")
                subprocess.run(f"{sign_prefix} '{dest}'", shell=True)

            if disable_library_validate is not None:
                subprocess.run(
                    "sudo defaults write /Library/Preferences/com.apple.security.libraryvalidation.plist DisableLibraryValidation -bool true",
                    shell=True,
                )

            if extra_shell is not None:
                subprocess.run(
                    f"sudo sh {current.parent}/tool/{extra_shell}", shell=True
                )

            if deep_sign_app:
                subprocess.run(f"{sign_prefix} '{app_base_locate}'", shell=True)

            subprocess.run(f"sudo xattr -cr '{dest}'", shell=True)

            if tccutil is not None:
                # print("处理 tccutil reset All")
                subprocess.run(
                    f"tccutil reset All {local_app['CFBundleIdentifier']}", shell=True
                )

            print("App处理完成。")
    except KeyboardInterrupt:
        print("\n用户手动退出程序,祝你使用愉快,再见.")


if __name__ == "__main__":
    main()
