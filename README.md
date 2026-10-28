# TXT 分类管理器

一款按项目分类管理、查看与编辑文本文件的 Windows 桌面小工具。基于 Python 3 + PySide6 开发，可打包为单文件 exe，免安装运行。

## 功能

- **项目分组**：左侧按项目名称展示文件，项目可折叠、拖拽排序、全部折叠 / 全部展开
- **项目管理**：「设置 → 项目管理」可新建、重命名、删除项目，调整顺序，设置是否在左侧显示、是否显示文件字段
- **添加文件**：项目名右侧「＋」可添加已有文件（支持任意文件类型，也支持多选）或新建文件并指定保存路径
- **搜索**：左侧搜索框按关键字过滤项目名与文件名，命中的项目自动展开
- **自动保存**：右侧编辑区修改后 700ms 自动保存回原文件，`Ctrl+S` 立即保存，切换文件或关闭程序时也会落盘
- **编码识别**：自动识别 UTF-8 / UTF-8 BOM / GB18030 / UTF-16，并按原编码写回，避免文件乱码
- **非文本文件只读**：选择 pdf、图片、Office、压缩包等非文本文件时，右侧只显示文件信息且不可编辑
- **操作日志**：顶部「操作日志」可搜索、刷新、清空历史操作记录
- **系统设置**：可开启 / 关闭开机自启动与操作日志记录
- **状态记忆**：窗口大小、分栏比例、上次打开的文件、项目顺序与折叠状态均自动恢复

## 直接使用

双击 `TXT分类管理器.exe` 即可运行，无需安装 Python 或依赖。

## 从源码运行

```powershell
cd TxtProjectManager
python -m venv .venv
.\.venv\Scripts\pip.exe install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
.\.venv\Scripts\python.exe app.py
```

`requirements.txt` 仅包含 `PySide6-Essentials` 与 `PyInstaller`。

## 打包 exe

```powershell
cd TxtProjectManager
.\build.ps1
```

脚本会优先使用 `.venv` 环境，自动生成图标（`assets\app.ico`），并用 PyInstaller 以 `--onefile --windowed` 方式输出到 `dist\TXT分类管理器.exe`。

> 注意：`build.ps1` 为 UTF-8 with BOM 编码，便于 Windows PowerShell 5 正确解析中文。

## 目录结构

```
TxtProjectManager/
├── app.py                 # 程序入口、全局异常捕获
├── make_icon.py           # 生成应用图标
├── build.ps1              # 打包脚本
├── requirements.txt
├── core/
│   ├── paths.py           # 数据目录、配置与日志路径
│   ├── store.py           # JSON 配置读写（项目 / 文件 / 界面状态）
│   ├── activity_log.py    # 操作日志（JSONL）
│   ├── autostart.py       # 开机自启动（注册表）
│   ├── textfile.py        # 编码识别、文本判定、读写
│   └── utils.py           # 文件信息、资源管理器定位
└── ui/
    ├── theme.py           # 全局样式
    ├── widgets.py         # 通用组件与图标绘制
    ├── branding.py        # 应用图标绘制
    ├── sidebar.py         # 左侧项目 / 文件树
    ├── editor.py          # 右侧编辑器（行号、自动保存）
    ├── settings.py        # 项目管理 / 系统设置
    ├── log_dialog.py      # 操作日志查看
    └── main_window.py     # 主窗口与信号接线
```

## 数据与日志位置

- 配置文件：`%APPDATA%\TxtClassifyManager\config.json`
- 操作日志：`%APPDATA%\TxtClassifyManager\logs\operations.jsonl`
- 异常日志：`%APPDATA%\TxtClassifyManager\error.log`

删除 `%APPDATA%\TxtClassifyManager` 目录即可恢复到首次使用状态。被管理的 txt 文件本身仍保存在原位置，程序不会移动或复制它们。

## 常用操作

| 操作 | 方式 |
| --- | --- |
| 新建项目 | 左侧左上角「＋」 |
| 给项目加文件 | 项目名右侧「＋」→ 选择已有文件 / 新建文件 |
| 调整项目顺序 | 拖拽项目卡片，或在设置页拖动表格行 |
| 全部折叠 / 展开 | 左侧顶部双箭头图标 |
| 搜索项目或文件 | 左侧搜索框 |
| 隐藏项目 | 设置 → 项目管理 → 取消「是否显示」 |
| 立即保存 | `Ctrl+S` |
| 查看操作日志 | 顶部「操作日志」 |
