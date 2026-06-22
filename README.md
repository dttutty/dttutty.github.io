# 个人网站

本站使用 [jemdoc](https://github.com/jem/jemdoc) 生成。可编辑内容集中在 `index.jemdoc`，`index.html` 和 `jemdoc.css` 是生成结果。

## 生成页面

```bash
make build
```

官方 jemdoc 0.7.3 仍使用 Python 2，因此构建脚本固定到官方提交 `28c8a2b7c72dae7f6b9c47a31f936c089040417a`，校验下载内容后，通过固定摘要的 Python 2.7 容器运行。部署到 GitHub Pages 时只需要仓库中已经生成的静态文件，不需要 Python 或 Docker。
