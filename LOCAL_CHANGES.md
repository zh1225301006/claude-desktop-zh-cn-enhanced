# 本地增强版说明

基于 javaht/claude-desktop-zh-cn 的 2026-09-19 版本，针对 Windows Claude Desktop 2.7032.0.0 调整。

- 合并当前客户端英文资源与中文翻译，保留新增字段和格式占位符。
- 补全在线页面的侧栏、输入区、项目、作品、技能、设置及模型说明等常见界面文案。短标签只在界面控件或标题上翻译。
- 将 47 条动态文案安装到新版客户端实际使用的 ion-dist/i18n/dynamic 目录，同时保留旧 statsig 目录的兼容写入。
- 在线 DOM 翻译跳过含子元素的容器，避免覆盖按钮或弹窗中的嵌套结构。
- 重装时如果 Windows 暂时锁住 Claude.exe，恢复备份会等待后重试。

简体中文的前端、桌面和动态资源参考了 javaht 项目和 ICERainbow666/claude-desktop-zh-cn 的较新译文；保留原项目 LICENSE。未翻译的新文案会显示英文，在线服务随时可能更新文案。第三方技能说明、用户内容和模型生成内容不属于界面翻译范围。

在此目录运行 install-windows.bat，选择官方账号模式和简体中文即可安装。官方账号模式修改 Claude.exe 和 app.asar；Claude 更新后需要重装补丁。
