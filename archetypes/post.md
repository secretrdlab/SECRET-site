---
title: "{{ replace .File.ContentBaseName "_" " " | title }}"
date: {{ .Date }}
summary: One-sentence summary shown in the post list.
draft: false
---

Write the post here. Put images in this same folder and reference them by file name:

![Description of the photo](photo.jpg)
