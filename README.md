# Lei Zhao's website

Academic Pages / Jekyll site for <https://dttutty.com>.

## Content

- `_config.yml`: profile, social links, and site settings.
- `_data/navigation.yml`: top navigation.
- `_pages/about.md`: all main content on the home page.
- `_publications/`: publication and manuscript data, sorted by `order` on the home page.
- `cv.pdf` and `img/`: résumé and existing images.

## Local preview

With Ruby 3.2, Ruby development headers, a C/C++ compiler, and Bundler installed:

```sh
bundle install
bundle exec jekyll serve --host 127.0.0.1 --url http://127.0.0.1:4000
```

Open <http://127.0.0.1:4000>. Build without serving with `bundle exec jekyll build`.

## GitHub Pages

Set **Settings → Pages → Build and deployment → Source** to **GitHub Actions**.
The workflow in `.github/workflows/pages.yml` builds pull requests and deploys pushes to `main`.
Keep the custom domain set to `dttutty.com`; `CNAME` is included in the output.

Based on [Academic Pages](https://github.com/academicpages/academicpages.github.io), using its bundled layouts and styles under the [MIT license](LICENSE).
