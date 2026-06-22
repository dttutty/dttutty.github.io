# 个人网站

本站使用 [jemdoc](https://github.com/jem/jemdoc) 生成。导航定义在 `MENU`，各栏目内容位于对应的 `.jemdoc` 文件；`jemdoc.conf` 统一注入页面头部配置和 Google tag。同名 `.html` 文件和 `jemdoc.css` 是生成结果。

## 生成页面

```bash
make build
```

官方 jemdoc 0.7.3 仍使用 Python 2，因此构建脚本固定到官方提交 `28c8a2b7c72dae7f6b9c47a31f936c089040417a`，校验下载内容后，通过固定摘要的 Python 2.7 容器运行。部署到 GitHub Pages 时只需要仓库中已经生成的静态文件，不需要 Python 或 Docker。
