# 乐鑫技术参考手册（LaTeX 版）

本仓库包含用于开发与构建乐鑫技术参考手册 (TRM) 的 LaTeX 源文件及辅助脚本。

目前，除 ESP8266 外，各芯片的 TRM 源文件均部署于此。

> **说明**：仓库中的源代码可能领先于已发布的 PDF 版本。PDF 定期发布，因此最近合并的改动可能不会立即反映在公开 PDF 中。


## 目录

- [构建说明](#构建说明)
   - [快速入门](#快速入门)
   - [本地构建](#本地构建)
   - [在 Dev Container 中构建](#在-dev-container-中构建)
   - [构建产物](#构建产物)
   - [不使用专有字体构建](#不使用专有字体构建)
- [常见构建问题与排查](#常见构建问题与排查)
   - [minted 宏包错误](#minted-宏包错误)
   - [配方终止错误](#配方终止错误)
   - [缺少字体错误](#缺少字体错误)
   - [ghostscript 初始化错误](#ghostscript-初始化错误)
- [pre-commit 钩子](#pre-commit-钩子)
   - [功能](#功能)
   - [安装与使用](#安装与使用)
- [许可](#许可)
- [反馈与贡献](#反馈与贡献)


## 构建说明

### 快速入门

你可以使用本仓库提供的 Visual Studio Code Dev Container 构建 TRM PDF，也可以在本地安装 TeX Live 后构建（在 macOS/Windows 上通常更快）。请根据系统环境选择合适的方式。

#### 使用任一方式的前提条件

1. 安装 [Visual Studio Code](https://code.visualstudio.com/Download)。

   在终端中用 VS Code 快速打开仓库目录，可运行：

   ```sh
   cd <repo-folder>
   code .
   ```

2. 在 VS Code 中安装以下扩展：
   - [Dev Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
   - [LaTeX Workshop](https://marketplace.visualstudio.com/items?itemName=James-Yu.latex-workshop)

#### 推荐：VS Code Dev Container

使用 Dev Container 可以获得可复用的构建环境，其中已预装 TeX Live 等依赖。

1. 安装 [Docker Desktop](https://www.docker.com/)。
2. 在 VS Code 中打开本仓库，选择 `在容器中重新打开`。

   首次运行拉取镜像可能需要几分钟时间，后续打开速度将会更快。

   每次打开带有开发容器配置的文件夹时，VS Code 会提示是否在容器中重新打开仓库，接受提示并等待完成即可。若错过通知，可点击左下角的 `><` 图标，执行 `在容器中重新打开`。

#### 可选：本地安装 TeX Live

若希望在本地构建，请为当前操作系统安装 TeX Live：

- macOS：MacTeX — https://tug.org/mactex/
- Windows/Linux：TeX Live — https://tug.org/texlive/

注意完整版 TeX Live 体积较大（数 GB）。

### 在 Dev Container 中构建

1. 在 Dev Container 中重新打开仓库。参见 [推荐：VS Code Dev Container](#推荐vs-code-dev-container)。
2. 在容器内使用与 [本地构建](#本地构建) 相同的 LaTeX Workshop 构建操作。

### 本地构建

1. 打开任意模块的 `.tex` 根文件，一般为各芯片目录下的 `ESP32-XX-main__EN.tex` / `...__CN.tex`。
2. 点击顶部标签栏右侧的绿色构建三角 `▷`。
3. 在底部状态栏左侧查看构建状态：构建中会显示 `Build`；结束后会显示 `✓`（成功）或 `✕`（失败）。
4. 点击构建三角旁的书本图标，可在编辑器中打开生成的 PDF。

关于快捷键、构建配方与配置项的更多说明，见 [LaTeX Workshop Wiki](https://github.com/James-Yu/LaTeX-Workshop/wiki)。

### 构建产物

每个模块构建后会在相应目录下生成 `out/` 子目录，内含 PDF、日志及其他产物。该行为用于保持源目录整洁，可在 `.vscode/settings.json` 中配置。

要查看构建产物与日志，可点击左侧边栏的 `TEX` 图标，再选择 `查看日志消息` > `查看 LaTeX 编译日志`。

### 不使用专有字体构建

TRM 源文件使用的官方专有字体无法开源。

文档构建的入口脚本是 `build_with_fetched_fonts.py`。`.vscode/settings.json` 引用了该脚本，因此使用 LaTeX Workshop 本地构建时会自动调用。

为便于外部用户构建，构建脚本包含回退机制：官方字体不可用时，自动切换到替代字体（TeX Gyre Heros 或 Helvetica）。

此时 PDF 仍可成功编译且内容正确，但版式外观可能与已发布版本存在差异。

示例日志：

```sh
[Pre-build] ⚠️ Failed to set the Overleaf project. Cannot fetch official fonts.
[Pre-build] Fallback fonts configured in preamble-shared.sty.
[Pre-build] ⚠️ The compiled PDF will look different from the public version.
```

日志查看方式见 [构建产物](#构建产物) 一节。


## 常见构建问题与排查

### minted 宏包错误

编译项目时可能出现如下错误：

```
/Users/../esp-technical-reference-manual-latex/ESP32-S3/ESP32-S3-main__EN.tex:21: Package minted Error: You must have `pygmentize' installed to use this package.
```

若使用本地 TeX Live 时遇到该问题，请在终端执行 `pygmentize -V`，检查是否已安装 Python 包 `pygments`：

```
pygmentize -V
Pygments version 2.13.0, (c) 2006-2022 by Georg Brandl, Matthäus Chajdas and contributors.
```

若提示 `command not found: pygmentize`，请执行 `pip3 install pygments` 安装该依赖。

**Windows** 用户若在 PowerShell 中无法识别 `pip3`，可先安装 [Python](https://www.python.org/downloads/)，再运行 `python -m pip install pygments`。安装后可能还需将可执行文件所在目录加入 `$PATH`，路径类似 `C:\Users\username\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\LocalCache\local-packages\Python311\Scripts`。关于向 `$PATH` 添加可执行路径，参见 [配方终止错误](#配方终止错误)。

本仓库自带的 [Docker](.devcontainer/Dockerfile) 开发容器已包含上述依赖。


### 配方终止错误

编译时还可能出现：

```
LaTeX fatal error: spawn latexmk ENOENT, . PID: undefined.
```

出现该问题时，请将 TeX 可执行文件所在目录加入 `$PATH` 环境变量。

**macOS** 用户可在主目录下的配置文件中用文本编辑器添加上述路径。Bash 用户可在 `.bashrc` 中加入 `export PATH="/Library/TeX/texbin/:$PATH"`；Zsh 用户在 `.zshrc` 中加入 `export PATH="/Library/TeX/texbin/:$PATH"`。

**Windows** 用户可打开 `开始` 菜单，搜索 `环境变量`，进入 `编辑系统环境变量` > `环境变量`。在 `用户变量` 中点击 `新建`，变量名填 `TeX`，变量值填包含 TeX 可执行文件的目录（例如 `C:\texlive\2022\bin\win32`）。点击 `确定` 保存。

然后重启 VS Code 再尝试编译。


### 缺少字体错误

在 PC 上安装 TeX Live 时可能遇到缺少字体的报错，请按提示安装缺失字体。

**Windows** 用户若遇到类似错误：

```
c:/texlive/2022/texmf-dist/tex/latex/ctex/fontset/ctex-fontset-windows.def:101: Package fontspec Error: The font "SimHei" cannot be found.
```

请在系统 `可选功能` 中安装 `简体中文补充字体`。详见 [The font "SimHei" cannot be found](https://github.com/sjtug/SJTUThesis/issues/564)。


### ghostscript 初始化错误

使用 XeLaTeX 编译 PDF 时可能出现：

```
GPL Ghostscript 9.55.0: Can't find initialization file gs_init.ps.
xdvipdfmx:fatal: pdf_link_obj(): passed invalid object.
```

原因是 ghostscript 找不到所需的初始化文件 `gs_init.ps`。可将环境变量 `GS_LIB` 永久设置为包含 `gs_init.ps` 的目录。

**如何查找 `gs_init.ps` 路径**

在终端执行：

```
find /usr -name gs_init.ps 2>/dev/null
```

输出类似：

```
/usr/local/Cellar/ghostscript/9.53.3_1/share/ghostscript/9.55.0/Resource/Init/gs_init.ps
```

请复制包含 `gs_init.ps` 的目录路径（即到 `/Init` 为止的路径）。

**设置 `GS_LIB` 环境变量**

将 `GS_LIB` 设为上述路径。

Zsh：

```
echo 'export GS_LIB=/usr/local/Cellar/ghostscript/9.53.3_1/share/ghostscript/9.55.0/Resource/Init' >> ~/.zshrc
source ~/.zshrc
```

Bash：

```
echo 'export GS_LIB=/usr/local/Cellar/ghostscript/9.53.3_1/share/ghostscript/9.55.0/Resource/Init' >> ~/.bashrc
source ~/.bashrc
```

请替换为本机实际路径。重启 VS Code 再尝试编译。


## Pre-Commit 钩子

### 功能

`pre-commit` 钩子能够避免提交敏感信息或与仓库无关的内容，在开发中尽早暴露问题。本仓库中包含的检查包括：

- 检测并移除 `.tex` 文件中的待办注释或整段注释代码。
- 检测并移除专有或二进制类型文件（例如 `.csv`、`.docx`、`.odg`、`.zip`）。
- 使用 codespell 在多种文件类型中检测并修正常见拼写问题。
- 在提交前对暂存文件本地运行，也会在 CI 中运行。

### 安装与使用

1. 安装 `pre-commit`：
   ```sh
   pip install pre-commit
   ```

2. 在本仓库中启用钩子：
   ```sh
   pre-commit install
   ```

3. 日常使用：
   ```sh
   git add <files>
   git commit -m "Your message"
   ```

   若某钩子修改了暂存文件，将中止本次提交；请审核变更后重新 `git add` 提交。

   示例日志：

   ```sh
   Check todo notes or commented code.......................................Failed
   - hook id: check-todo-notes-commented-code
   - exit code: 1
   - files were modified by this hook

   processing file ESP8684/07-RESCLK__CN.tex
   Todo notes removed from line 2: \todoreminder{test}
   processing file ESP8684/07-RESCLK__EN.tex
   Commented code removed from line 2: %Test

   Check proprietary files..................................................Failed
   - hook id: check-proprietary-files
   - exit code: 1
   - files were modified by this hook

   Proprietary files detected and deleted:
      test.csv
      test.odg

   codespell................................................................Failed
   - hook id: check-proprietary-files
   - files were modified by this hook

   FIXED: README.md
   ```

4. 忽略特定检查项：
- 若要允许提交特定的待办标记或注释片段，请将其写入 `./tools/check_todo_notes_commented_code/ignored_todo_notes_commented_code.txt`。

  请记住提交该文件，以便依赖同一配置的 CI 检查能够通过。

- 若要允许提交特定拼写，请在 `.codespellrc` 的 `ignore-words-list` 中添加词条。


## 许可

本仓库采用多种许可协议：

- 所有脚本使用 [Apache License 2.0](./LICENSE-APACHE)。
- 所有文档内容使用 [署名—相同方式共享 4.0 协议国际版 (CC-BY-SA 4.0)](./LICENSE-CC-BY-SA)。


## 反馈与贡献

乐鑫文档团队欢迎社区开发者改进与完善技术参考手册！

若有见解、更新或建议，可通过以下方式参与：

- 点击任意 [文档页面](https://documentation.espressif.com/esp32_technical_reference_manual_cn.pdf) 底部 `反馈文档意见` 图标留言。
- 通过 [GitHub Issues](https://github.com/espressif/esp-technical-reference-manual-latex/issues) 报告问题。
- 直接提交 [Pull Request（PR）](https://github.com/espressif/esp-technical-reference-manual-latex/pulls) 修复。
    > 提交 PR 时请遵循 [贡献指南](./CONTRIBUTING_CN.md)。
