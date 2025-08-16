# launcher.py
from __future__ import annotations
import os, sys, json, time, shutil, zipfile, subprocess, traceback, re
from typing import List, Dict, Any, Optional
from pathlib import Path

# ----------------------------- 依赖检测 -----------------------------
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False
    class _Fore:  # type: ignore
        RED = GREEN = YELLOW = CYAN = ""
    Fore = _Fore()
    Style = type("_Style", (), {"RESET_ALL": ""})()

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(x, **kw):  # type: ignore
        return x

# ----------------------------- 工具函数 -----------------------------
def log(msg: str, level: str = "INFO"):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    log_file = Path(VSCodeManager.get_vsenv_dir()) / "launcher.log"
    try:
        with log_file.open("a", encoding="utf-8") as f:
            f.write(f"[{ts}] {level}: {msg}\n")
    except Exception:
        # 如果连目录都不存在就静默忽略
        pass

def print_color(txt: str, color: Any = ""):
    """带颜色打印，无依赖时退化"""
    print(f"{color}{txt}")

def spin(text: str, seconds: float):
    """简易转圈等待"""
    if seconds < 0.3:
        time.sleep(seconds)
        return
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧"]
    end_time = time.time() + seconds
    idx = 0
    while time.time() < end_time:
        print(f"\r{text} {frames[idx % len(frames)]}", end="", flush=True)
        time.sleep(0.1)
        idx += 1
    print("\r" + " " * (len(text) + 4) + "\r", end="")

def safe_input(prompt: str) -> str:
    """捕获 Ctrl+C，使菜单可回退"""
    try:
        return input(prompt).strip()
    except KeyboardInterrupt:
        print_color("\n操作已取消，返回主菜单。", Fore.YELLOW)
        return ""

# ----------------------------- 核心类 -----------------------------
class VSCodeManager:
    VSEnv = Path.home() / ".vsenv"

    @staticmethod
    def get_vsenv_dir() -> str:
        return str(VSCodeManager.VSEnv)

    @staticmethod
    def list_envs() -> List[str]:
        if not VSCodeManager.VSEnv.exists():
            return []
        return sorted(
            {
                d.relative_to(VSCodeManager.VSEnv).parts[0]
                for d in VSCodeManager.VSEnv.rglob("vscode")
                if d.is_dir()
            }
        )

    # ------------------- 创建环境 -------------------
    @staticmethod
    def create_vscode():
        print_color("=== 创建 VSCode 环境 ===", Fore.CYAN)
        zip_path = None
        # 自动扫描当前目录下的 zip
        zips = list(Path.cwd().glob("VSCode*.zip"))
        if zips:
            print_color("检测到以下离线包：", Fore.YELLOW)
            for i, p in enumerate(zips, 1):
                print(f"{i}. {p.name}")
            choice = safe_input("请选择序号或直接输入路径 (Enter 跳过): ")
            if choice.isdigit() and 1 <= int(choice) <= len(zips):
                zip_path = zips[int(choice) - 1]
            elif choice and Path(choice).exists():
                zip_path = Path(choice)
        if zip_path is None:
            zip_path = Path(safe_input("请输入离线包路径(可拖拽): ").strip('"'))
        if not zip_path.exists():
            print_color("文件不存在！", Fore.RED)
            safe_input("按回车返回...")
            return
        env_name = ""
        while not env_name or re.search(r"\s", env_name):
            env_name = safe_input("环境名称(英文无空格): ")
            if not env_name:
                print_color("名称不能为空", Fore.RED)
        target = VSCodeManager.VSEnv / env_name
        if target.exists():
            print_color("环境已存在！", Fore.RED)
            safe_input("按回车返回...")
            return

        try:
            print_color("正在解压，请稍候...", Fore.GREEN)
            with zipfile.ZipFile(zip_path) as zf:
                members = zf.namelist()
                root = members[0].split("/")[0]
                has_nesting = all(m.startswith(root + "/") for m in members)
                for m in tqdm(members, desc="解压"):
                    zf.extract(m, path=target)
                vscode_src = target / root if has_nesting else target
                vscode_dst = target / "vscode"
                if vscode_src != vscode_dst:
                    vscode_src.rename(vscode_dst)
            print_color("✅ 环境创建完成！", Fore.GREEN)
            log(f"Created env {env_name}")
        except Exception as e:
            print_color(f"创建失败：{e}", Fore.RED)
            log(traceback.format_exc(), "ERROR")
        safe_input("按回车返回...")

    # ------------------- 启动环境 -------------------
    @staticmethod
    def open_vscode():
        envs = VSCodeManager.list_envs()
        if not envs:
            print_color("没有可用环境，请先创建", Fore.YELLOW)
            safe_input("按回车返回...")
            return
        print_color("=== 选择环境 ===", Fore.CYAN)
        for i, e in enumerate(envs, 1):
            print(f"{i}. {e}")
        choice = safe_input("输入序号或名称: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(envs):
            env = envs[int(choice) - 1]
        elif choice in envs:
            env = choice
        else:
            print_color("无效选择", Fore.RED)
            safe_input("按回车返回...")
            return

        # 读取上次配置
        cfg_file = VSCodeManager.VSEnv / "last_options.json"
        last: Dict[str, Any] = {}
        if cfg_file.exists():
            last = json.loads(cfg_file.read_text(encoding="utf-8"))
        print_color("\n=== 启动选项 (留空=使用上次/默认) ===", Fore.CYAN)
        opts: Dict[str, Any] = {}
        for k, text, default in [
            ("--host", "随机主机名", last.get("--host", False)),
            ("--mac", "随机MAC", last.get("--mac", False)),
            ("--proxy", "代理地址", last.get("--proxy", "")),
            ("--sandbox", "沙箱模式(none/sandbox/appcontainer/wsb)", last.get("--sandbox", "none")),
            ("--augment", "Augment 支持", last.get("--augment", False)),
        ]:
            val = safe_input(f"{text} [{default}]: ").strip()
            if not val:
                val = default
            if k == "--sandbox":
                if val != "none":
                    opts[k] = val
            elif k == "--proxy":
                if val:
                    opts[k] = val
            else:
                opts[k] = val == "y" or (isinstance(default, bool) and val == "")
        # 保存本次配置
        cfg_file.write_text(json.dumps(opts, ensure_ascii=False, indent=2))
        cmd = ["vsenv", "start", env]
        for k, v in opts.items():
            if v is True:
                cmd.append(k)
            elif v:
                cmd.extend([k, v])
        try:
            print_color("正在启动...", Fore.GREEN)
            spin("启动中", 1)
            subprocess.run(cmd, check=True)
            log(f"Started {env} with {opts}")
        except subprocess.CalledProcessError:
            print_color("启动失败，请检查 vsenv 是否正确安装", Fore.RED)
            log(traceback.format_exc(), "ERROR")
            safe_input("按回车返回...")

    # ------------------- 删除环境 -------------------
    @staticmethod
    def remove_vscode():
        envs = VSCodeManager.list_envs()
        if not envs:
            print_color("没有环境可删除", Fore.YELLOW)
            safe_input("按回车返回...")
            return
        print_color("=== 删除环境 ===", Fore.CYAN)
        for i, e in enumerate(envs, 1):
            print(f"{i}. {e}")
        choice = safe_input("输入序号或名称: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(envs):
            env = envs[int(choice) - 1]
        elif choice in envs:
            env = choice
        else:
            print_color("无效选择", Fore.RED)
            safe_input("按回车返回...")
            return
        if safe_input(f"确认删除 {env} 吗？(y/N): ").lower() == "y":
            try:
                target = VSCodeManager.VSEnv / env
                shutil.rmtree(target)
                print_color("✅ 已删除", Fore.GREEN)
                log(f"Removed env {env}")
            except Exception as e:
                print_color(f"删除失败：{e}", Fore.RED)
                log(traceback.format_exc(), "ERROR")
        else:
            print_color("已取消", Fore.YELLOW)
        safe_input("按回车返回...")

    # ------------------- 注册 / 注销 / 重置 -------------------
    @staticmethod
    def _simple_cmd(action: str, msg: str):
        try:
            subprocess.run(["vsenv", action], check=True)
            print_color(msg, Fore.GREEN)
            log(f"{action} executed")
        except:
            print_color("执行失败，请检查 vsenv 是否安装", Fore.RED)
            log(traceback.format_exc(), "ERROR")
        safe_input("按回车返回...")

    @staticmethod
    def regist_vscode():
        VSCodeManager._simple_cmd("regist", "已注册环境")

    @staticmethod
    def logoff_vscode():
        VSCodeManager._simple_cmd("logoff", "已注销当前环境")

    @staticmethod
    def reset_vscode():
        VSCodeManager._simple_cmd("rest", "已重置 VSCode 环境")

# ----------------------------- 主循环 -----------------------------
def main():
    menu = {
        "1": ("显示所有环境", VSCodeManager.list_envs),
        "2": ("创建环境", VSCodeManager.create_vscode),
        "3": ("启动环境", VSCodeManager.open_vscode),
        "4": ("删除环境", VSCodeManager.remove_vscode),
        "5": ("注册环境", VSCodeManager.regist_vscode),
        "6": ("注销环境", VSCodeManager.logoff_vscode),
        "7": ("重置环境", VSCodeManager.reset_vscode),
        "8": ("退出", None),
    }
    while True:
        print_color("\n======== LiteVSenvLauncher ========", Fore.CYAN + Style.BRIGHT)
        for k, (desc, _) in menu.items():
            print(f"{k}. {desc}")
        choice = safe_input("请选择: ").strip()
        if choice == "8":
            print_color("Bye~", Fore.GREEN)
            break
        if choice in menu:
            try:
                func = menu[choice][1]
                if func:
                    func()
            except Exception as e:
                print_color(f"发生错误：{e}", Fore.RED)
                log(traceback.format_exc(), "ERROR")
        else:
            print_color("请输入 1-8", Fore.YELLOW)

if __name__ == "__main__":
    main()