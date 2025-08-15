import os
import zipfile
import shutil
import subprocess
from typing import List, Optional

class VSCodeManager:
    """VSCode环境管理器类"""
    
    @staticmethod
    def clear_screen() -> None:
        """清屏"""
        os.system("cls" if os.name == "nt" else "clear")

    @staticmethod
    def get_vsenv_dir() -> str:
        """获取.vsenv目录路径"""
        return os.path.join(os.path.expanduser("~"), ".vsenv")

    @staticmethod
    def find_vscode_in_vsenv() -> List[str]:
        """
        在用户文件夹下的.vsenv目录中查找所有含有vscode文件夹的目录
        
        返回:
            List[str]: 包含所有含有vscode文件夹的目录路径列表
        """
        vsenv_dir = VSCodeManager.get_vsenv_dir()
        
        if not os.path.isdir(vsenv_dir):
            print(f"用户文件夹下不存在.vsenv目录: {vsenv_dir}")
            return []
        
        return [dirpath for dirpath, dirnames, _ in os.walk(vsenv_dir) 
                if 'vscode' in dirnames]

    @staticmethod
    def view_all_vscode() -> None:
        """显示所有VSCode环境的名称"""
        print("========| 所有环境 |========")
        print("环境名")
        
        # 获取所有包含vscode的目录路径
        vscode_dirs = VSCodeManager.find_vscode_in_vsenv()
        
        if not vscode_dirs:
            print("没有找到任何VSCode环境")
            input("\n按回车键继续...")
            return
        
        # 提取并显示环境名称
        vsenv_dir = VSCodeManager.get_vsenv_dir()
        for dir_path in vscode_dirs:
            # 获取.vsenv目录后的相对路径
            rel_path = os.path.relpath(dir_path, vsenv_dir)
            # 分割路径并获取第一级目录名（环境名称）
            env_name = rel_path.split(os.sep)[0]
            print(env_name)
        
        input("\n按回车键继续...")

    @staticmethod
    def create_vscode() -> None:
        """创建新的VSCode环境"""
        while True:
            package_name = input("请输入离线包名称(如VSCode-win32-x64-XXX.zip): ").strip()
            if not package_name:
                print("错误：包名称不能为空！")
                continue
            
            if not package_name.lower().endswith('.zip'):
                print("错误：只支持.zip格式的离线包！")
                continue
            
            env_name = input("请输入环境名称(最好是英文): ").strip()
            if not env_name:
                print("错误：环境名称不能为空！")
                continue
            
            # 检查环境是否已存在
            if os.path.exists(os.path.join(VSCodeManager.get_vsenv_dir(), env_name)):
                print(f"错误：环境 '{env_name}' 已存在！")
                continue
            
            break

        # 创建环境
        try:
            # 使用subprocess运行命令并捕获输出
            subprocess.run(
                ["vsenv", "create", env_name],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # 准备目标目录
            target_dir = os.path.join(VSCodeManager.get_vsenv_dir(), env_name, "vscode")
            os.makedirs(target_dir, exist_ok=True)
            
            # 处理离线包
            source_path = os.path.join(os.getcwd(), package_name)
            if not os.path.exists(source_path):
                print(f"错误：找不到离线包 {source_path}")
                return
            
            print(f"正在解压 {package_name}...")
            with zipfile.ZipFile(source_path, 'r') as zip_ref:
                zip_ref.extractall(target_dir)
            
            print("VSCode环境创建成功！")
            
        except subprocess.CalledProcessError:
            print("错误：创建环境失败")
        except Exception as e:
            print(f"创建环境时发生错误: {str(e)}")
        
        input("\n按回车键继续...")

    @staticmethod
    def open_vscode() -> None:
        """打开VSCode环境"""
        env_name = input("请输入环境名称: ").strip()
        if env_name:
            # 使用subprocess运行命令并捕获输出
            try:
                subprocess.run(
                    ["vsenv", "start", env_name],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except subprocess.CalledProcessError:
                print("错误：启动环境失败")
        else:
            print("错误：环境名称不能为空！")
        input("\n按回车键继续...")

    @staticmethod
    def remove_vscode() -> None:
        """删除VSCode环境"""
        env_name = input("请输入环境名称: ").strip()
        if not env_name:
            print("错误：环境名称不能为空！")
            input("\n按回车键继续...")
            return
        
        # 确认删除
        confirm = input(f"确定要删除环境 '{env_name}' 吗？(y/N): ").strip().lower()
        if confirm == 'y':
            try:
                # 使用subprocess运行命令并捕获输出
                subprocess.run(
                    ["vsenv", "remove", env_name],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                print("环境已删除")
            except subprocess.CalledProcessError:
                print("错误：删除环境失败")
        else:
            print("取消删除")
        
        input("\n按回车键继续...")

def show_menu() -> None:
    """显示主菜单"""
    print("========| LiteVSenvLauncher |========")
    print("1. 显示所有的VSCode环境")
    print("2. 创建VSCode环境")
    print("3. 开启VSCode环境")
    print("4. 删除VSCode环境")
    print("5. 退出")

def get_user_choice() -> Optional[int]:
    """获取用户选择"""
    try:
        choice = int(input("请输入序号(1~5): "))
        if 1 <= choice <= 5:
            return choice
        print("错误：请输入1-5之间的数字！")
    except ValueError:
        print("错误：请输入有效的数字！")
    return None

def main() -> None:
    """主程序"""
    actions = {
        1: VSCodeManager.view_all_vscode,
        2: VSCodeManager.create_vscode,
        3: VSCodeManager.open_vscode,
        4: VSCodeManager.remove_vscode,
    }
    
    while True:
        VSCodeManager.clear_screen()
        show_menu()
        
        choice = get_user_choice()
        if choice is None:
            input("按回车键继续...")
            continue
            
        if choice == 5:
            print("感谢使用，再见！")
            break
            
        try:
            actions[choice]()
        except Exception as e:
            print(f"发生错误: {str(e)}")
            input("按回车键继续...")

if __name__ == "__main__":
    main()
