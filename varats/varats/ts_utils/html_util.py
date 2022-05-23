"""Utility module for generating html files."""

import typing as tp

__HTML_BASE_TEMPLATE = """<!DOCTYPE html>
<html>

<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width" />
  <title>{title}</title>
  <style type="text/css" media="screen">
{style}
  </style>
</head>

<body>
  <h1>{title}</h1>
  <div class="box">
{content}
  </div>
</body>

</html>
"""

CSS_COMMON = """    body {
      font-family: Arial, sans-serif;
    }
    a {
      text-decoration: none
    }"""

CSS_TABLE = """    table {
      border: none;
      border-collapse: collapse;
      border-spacing: 0;
    }
    table td,th {
      border-style: solid;
      border-width: 0;
      overflow: hidden;
      padding: 2px 10px;
      word-break: normal;
      border-color: inherit;
      text-align: left;
      vertical-align: top
    }"""

CSS_IMAGE_MATRIX = """    .box {
      display: flex;
      padding: 0 4px;
    }

    .column {
      flex: 18%;
      max-width: 18%;
      min-width: 18%;
      padding: 0 4px;
    }

    .column img {
      margin-top: 8px;
      vertical-align: middle;
      width: 100%;
    }"""


def html_page(title: str, content: str, styles: tp.List[str]) -> str:
    """
    Generate a simple HTML page.

    Args:
        title: the title of the page
        content: the content of the page
        styles: a list of CSS style declarations

    Returns:
        the HTML page as a string
    """
    return __HTML_BASE_TEMPLATE.format(
        title=title, content=content, style="\n".join(styles)
    )
