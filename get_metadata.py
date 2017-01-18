import json
import re
import jmespath
import codecs

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

    def get_field_regex(self,path,regex):
        text = jmespath.search(path,self.data)
        if text:
            m = regex.search(text)
            if m:
                return m.group(1)

    def get_field_all(self,path):
        lines = jmespath.search(path,self.data)
        if lines:
            return ''.join(lines)

    def get_field_with_header(self,header):
        re_header = re.compile('^###\s+(.*)$',re.MULTILINE)
        for lines in jmespath.search('cells[*].source',self.data):
            text = ''.join(lines)
            m = re_header.match(text)
            if m and m.group(1)==header:
                return text

    def get_field_markdown_list(self,header,regex):
        text = self.get_field_with_header(header)
        if text:
            return regex.findall(text)
        else:
            return []

    def get_field_comma_separated_list(self,header):
        text = self.get_field_with_header(header)
        if text:
            return sum((l.split(',') for l in text.split('\n')[1:]),[])
        else:
            return []

    def get_metadata(self):
        print(self.filename)
        re_title = re.compile(r'^#\s+(.*)$',re.MULTILINE)
        re_author = re.compile(r'^##\s+Author:\s+(.*)$',re.MULTILINE)

        self.title = self.get_field_regex('cells[0].source[0]',re_title)
        self.author = self.get_field_regex('cells[1].source[0]',re_author)

        self.description = self.get_field_all('cells[2].source')

        re_lineitem = re.compile(r'^\*\s+(.*)$',re.MULTILINE)
        self.references = self.get_field_markdown_list('References',re_lineitem)

        self.keywords = self.get_field_comma_separated_list('Keywords')
        self.requirements = self.get_field_comma_separated_list('Requirements')

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
