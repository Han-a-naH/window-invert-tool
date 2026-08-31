# 窗口区域颜色反转工具

Windows 10/11 的轻量级托盘工具。运行 `run_window_invert.bat`（或直接执行
`pythonw window_invert.py`）后，右下角托盘图标会提供：

## 直接使用

普通用户无需安装 Python。请从 [Releases](https://github.com/Han-a-naH/window-invert-tool/releases)
下载 `WindowInvert.exe`，双击即可运行。程序是便携版，不会修改目标窗口，也不需要安装向导。

## 功能

- **选择/取消反相窗口**：列出当前可见的顶层窗口。每次打开子菜单后点击一个窗口即可切换勾选状态，重新打开菜单可继续选择其他窗口；再次点击已勾选窗口即可取消。
- **开启/关闭反相**：暂停或恢复当前窗口的反相。
- **渲染速度**：可选择 15、30 或 60 FPS，在流畅度和资源占用之间调整。
- **退出**：关闭覆盖层并退出。

工具使用系统 `PrintWindow` 将目标渲染到离屏位图，再用 GDI `NOTSRCCOPY` 进行实时反相，
不向目标窗口注入代码；
覆盖层为不可激活、鼠标穿透窗口。多个目标窗口会共享同一份全局 Z 序：上层目标优先显示，
下层目标只反相未被其他窗口（包括其他已选目标）遮挡的部分，因此重叠区域不会被重复反相。
窗口移动、缩放、最小化、关闭和多显示器坐标会在后台自动更新；目标窗口关闭后会自动从选择中移除。

源代码只依赖 Python 3.9+ 标准库，无需安装第三方包；直接下载 exe 的用户无需安装 Python。

## 从源码运行或构建

开发者可以直接使用 Python 3.9+ 运行：

```powershell
pythonw window_invert.py
```

在 Windows 上构建单文件 exe：

```powershell
.\build_windows.ps1
```

构建结果位于 `dist\WindowInvert.exe`。项目使用 MIT License，详见 `LICENSE`。
