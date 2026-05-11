# 贡献指南

感谢你愿意为乐鑫技术参考手册（LaTeX 版）做出贡献！本文介绍了贡献范围、流程以及规范，以便你的贡献能够尽快通过审核并合并。


## 贡献范围

欢迎改进 TRM 正文内容或仓库说明文档！常见修改包括：

- 修改 LaTeX 源文件及配套文件，以修正或澄清技术内容。
- 改进 README、贡献指南等仓库说明文档。

若不确定某项修改是否合适，建议提交 issue 说明改动计划。


## 法律要求

在合并贡献之前，需要签署 [乐鑫贡献者协议](http://docs.espressif.com/projects/esp-idf/zh_CN/stable/contribute/contributor-agreement.html)。首次提交 PR 时，系统会自动提示签署。


## 快速开始

参与贡献的流程如下：

1. fork 本仓库
2. 从 `master` 分支创建一个新的分支
3. 按照下文规范完成修改
4. 提交 PR，并使用清晰、具体的标题

### 语言、写法与构建

本仓库的主要内容为 LaTeX (`.tex`) 及配套样式文件。请参考以下资料：

- LaTeX 基础知识：[Learn LaTeX](https://www.learnlatex.org/en/)
- 写作规范：[乐鑫风格指南](https://mos.espressif.com/)
- 本地构建：参见 [构建说明](./README_CN.md#构建说明)


### 分支命名规范

```
git checkout -b feature/add_gdma_chapter_to_esp32-c5_trm
```

1. **前缀**：分支名以 `docs/`、`bugfix/` 或 `feature/` 开头。

- `docs/`：更新构建脚本、文档模板或辅助工具时使用。
- `bugfix/`：修正文档中的错别字、缺陷或错误时使用。
- `feature/`：文档首次发布或新增功能时使用。

2. **不含空格**：用下划线代替空格。
3. **仅小写**：不要使用大写字母。
4. **每分支一件事**：例如准备新文档时，建议先为模板/脚本等结构性改动创建分支并合并，随后再为需要评审的正文内容改动另建分支。

### 提交说明规范

```
git commit -m "Chip/short name of TRM module: Add/Update/Remove..."
```

1. **关键词**：以芯片名或芯片/TRM 模块简称开头，例如 `ESP32-H2` 或 `ESP32-S3/UART`。

   > **说明**：若在单次合并请求中为多份 TRM 更新同一模块，或在一份 TRM 上同时更新多个模块，请用英文逗号分隔不同芯片或模块名（例如 `ESP32-S3, ESP32-H2/UART`）。

2. **用一行概括目的**：每个提交尽量只包含一个逻辑变更。

   > **说明**：动词使用一般现在时，且动词首字母大写。
