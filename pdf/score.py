#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: cc
# @Date  :2020-12-14

import json
import pdfkit

from jinja2 import Environment, FileSystemLoader

from PyPDF2 import PdfFileReader, PdfFileMerger

env = Environment(loader=FileSystemLoader('./'))
template = env.get_template('index.html')
with open("result.html", 'w') as fout:
    html_content = template.render(**{'num': 12})
    pdfkit.from_string(html_content, 'out.pdf')

pdf_files = ('out.pdf', 'chachong.pdf')
result_pdf = PdfFileMerger()
for pdf in pdf_files:
    with open(pdf, 'rb') as fp:
        pdf_reader = PdfFileReader(fp)
        result_pdf.append(pdf_reader, import_bookmarks=True)

result_pdf.write('result.pdf')
result_pdf.close()
