import json
import re
import jmespath
import codecs
from markdown_mistune import markdown2html_mistune

def handle_svg(data):
    source = ''.join(data)
    return source

def handle_png(data):
    return '<img src="data:image/png;base64,{}">'.format(data)

image_handlers = {
    'image/svg+xml': handle_svg,
    'image/png': handle_png,
}

class NotebookInvalidException(Exception):
    def __init__(self,message,notebook):
        self.notebook = notebook
        self.message = message

    def __str__(self):
        return 'Notebook "{}" is invalid: {}'.format(self.notebook.filename, self.message)

class Notebook(object):
    def __init__(self,file_path,filename):
        self.filename = filename
        self.data = json.loads(codecs.open(file_path,encoding='utf-8').read())
        self.get_metadata()
        self.get_image()
        try:
            self.validate()
            self.valid = True
        except NotebookInvalidException:
            self.valid = False

    def get_metadata(self):
        re_title = re.compile(r'^#\s+(.*)$',re.MULTILINE)
        re_author = re.compile(r'^##\s+Author:\s+(.*)$',re.MULTILINE)

        title_text = jmespath.search('cells[0].source[0]',self.data)
        if title_text:
            m = re_title.search(title_text)
            if m:
                self.title = m.group(1)

        author_text = jmespath.search('cells[1].source[0]',self.data)
        m = re_author.search(author_text)
        if m:
            self.author = m.group(1)

        description_text = ''.join(jmespath.search('cells[2].source',self.data))
        self.description = markdown2html_mistune(description_text)

    def get_image(self):
        for output in jmespath.search('cells[].outputs[].data',self.data):
            mime_types = [k for k in output if k in image_handlers]
            if len(mime_types):
                mime_type = mime_types[0]
                image_data = output[mime_type]
                image_tag = image_handlers[mime_type](image_data)
                self.image = {
                    'mime_type': mime_type,
                    'image_data': image_data,
                    'html': image_tag,
                }
                return

    def validate(self):
        if not hasattr(self,'image'):
            raise NotebookInvalidException("No image",self)


if __name__ == '__main__':
    notebook = Notebook('Divisors of a positive integers.ipynb')
    print(notebook)
