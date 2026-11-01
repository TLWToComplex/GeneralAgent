---
name: agent-browser
description: "Use this skill to browse the web, search for information, or interact with websites. Trigger whenever the user asks to 'search', 'browse', 'visit', 'check a website', or find real-time information online."
---

# Agent Browser

A CLI tool for browser automation designed for AI agents.

## Core Workflow

1.  **Open a page**: `agent-browser open <url>`
2.  **Inspect the page**: `agent-browser snapshot` (returns text representation with interactive elements marked as `@e1`, `@e2`, etc.)
3.  **Interact**: Use the reference IDs from the snapshot to click or type.
    *   `agent-browser click @e1`
    *   `agent-browser type @e2 "search query"`
    *   `agent-browser press Enter`
4.  **Extract**: Read the text content from the snapshot.

## Command Reference

| Command | Description | Example |
| :--- | :--- | :--- |
| `agent-browser open <url>` | Navigate to a URL | `agent-browser open https://google.com` |
| `agent-browser snapshot` | Get a text-based snapshot of the current page with interactive element IDs | `agent-browser snapshot` |
| `agent-browser click <id>` | Click an element by its ID | `agent-browser click @e12` |
| `agent-browser type <id> <text>` | Type text into an input field | `agent-browser type @e5 "hello world"` |
| `agent-browser press <key>` | Press a keyboard key | `agent-browser press Enter` |
| `agent-browser back` | Go back to the previous page | `agent-browser back` |
| `agent-browser screenshot <file>` | Save a screenshot to a file | `agent-browser screenshot page.png` |

## Tips for the Agent

*   **Always snapshot after navigation**: After opening a URL or clicking a link, run `snapshot` to see the new state.
*   **Use IDs**: The snapshot will show elements like `[12] @e12 Button: Submit`. Use `@e12` to interact with it.
*   **Search**: To search Google/Bing, open the URL, find the search box ID, type the query, and press Enter.
*   **Screenshots**: If you take a screenshot, provide the download link to the user using the format `[screenshot.png](http://localhost:8101/api/files/screenshot.png)`.

---

## Dependencies

⚠️ **重要提示：离线环境** ⚠️

本沙盒运行在**无互联网访问的离线环境**中。
所有依赖项已在 Docker 镜像中**预安装**，可直接使用。

**禁止执行以下操作：**
-  不要运行 `npm install`、`pip install`、`apt-get install` 等安装命令
-  不要尝试下载或更新任何软件包
-  不要执行需要网络连接的操作（除了浏览网页本身）

### 已预装的工具（可直接使用）
- ✅ **agent-browser** - 浏览器自动化工具，通过 `agent-browser` 命令使用
- ✅ **Playwright** - 浏览器引擎，已预装 Chromium 浏览器

### 验证工具是否存在（可选，快速）
如需验证工具是否可用，请使用以下**快速命令**（无需网络）：
```bash
which agent-browser          # 返回路径表示存在 (< 0.1秒)
agent-browser --version      # 本地检查 (< 1秒)
```

**禁止使用需要网络的检查命令：**
-  `npm install -g agent-browser` (需要网络)
-  `npx agent-browser install` (需要网络)

**注意：**
- 虽然沙盒是离线环境，但 `agent-browser` 可以访问外部网站进行浏览
- 只是不要尝试安装或更新工具本身
