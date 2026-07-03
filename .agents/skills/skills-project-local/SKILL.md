---
name: skills-项目目录
description: 当用户需要安装 skills 时，同时安装到全局目录和项目目录，这样既能去其他项目用，也能在 VSCode 文件树中看到。
---

# Skills 项目目录

用户希望 skills 同时安装在全局和项目目录。

## 触发条件

当用户说"安装 skill"、"add skill"、"装一个 skill"、"帮我装 xxx skill"等内容时使用。

## 安装规则

1. 先执行 `npx skills add <skill> -g -y` 安装到全局
2. 再执行 `npx skills add <skill> -y` 安装到项目目录
3. 安装完成后确认两边都存在：
   - 项目：`.agents/skills/<skill-name>/`
   - 全局：`~/.agents/skills/<skill-name>/`
4. 告知用户两个位置
