import codecs
import json
import re
import sys

import jmespath

RE_TITLE = r'^#\s+(.*)$'
RE_AUTHOR =r'^##\s+Author:\s+(.*)$'  # TODO Support more than one author

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
    """Exception class for Notebook class"""
    def __init__(self,message,notebook):
        self.notebook = notebook
        self.message = message

    def __str__(self):
        return 'Notebook "{}" is invalid: {}'.format(self.notebook.filename, self.message)

class Notebook(object):
    """Represent Notebook"""
    def __init__(self,filename, file_path="."):
        """Init Notebook class.

        :param filename: Name of the Jupyter Notebook file.
        :param file_path: TODO
        :returns: None
        :rtype: None

        """
        self.filename = filename
        self.data = json.loads(codecs.open(file_path,encoding='utf-8').read())
        self.get_metadata()
        self.get_image()
        self.valid = True if self.validate() else False

    def get_field_regex(self,path,regex):
        """Retrieve information based on JSON path and regular expression.

        :param path: JSON path.
        :param regex: Regular expression.
        :returns: Information find on the JSON path matching the regular expression.
        :rtype: str

        """
        text = jmespath.search(path,self.data)
        if text:
            m = regex.search(text)
            if m:
                return m.group(1)

    def get_field_all(self,path):
        """Retrieve information based on JSON.

        :param path: JSON path.
        :returns: Information find on the JSON path.
        :rtype: str

        """
        lines = jmespath.search(path,self.data)
        if lines:
            return ''.join(lines)

    def get_field_with_header(self,header):
        """Retrieve information from one header

        :param header: Header name.
        :returns: Information under the wanted header.
        :rtype: str

        """
        re_header = re.compile('^###\s+(.*)$',re.MULTILINE)
        for lines in jmespath.search('cells[*].source',self.data):
            text = ''.join(lines)
            m = re_header.match(text)
            if m and m.group(1)==header:
                return text

    def get_field_markdown_list(self,header,regex):
        """Return list text from markdown cell.

        :param header: Header name.
        :param regex: Regular expression.
        :returns: List as text.
        :rtype: str

        """
        text = self.get_field_with_header(header)
        if text:
            return regex.findall(text)
        else:
            return []

    def get_field_comma_separated_list(self,header):
        """Information as comma separated list

        :param header: Header name.
        :returns: List.
        :rtype: list

        """
        text = self.get_field_with_header(header)
        if text:
            return sum((l.split(',') for l in text.split('\n')[1:]),[])
        else:
            return []

    def get_metadata(self):
        """Retrieve the metadata from the demo.

        :returns: None
        :rtype: None

        """
        print("Processing {}".format(self.filename))

        re_title = re.compile(RE_TITLE, re.MULTILINE)
        self.title = self.get_field_regex('cells[0].source[0]',re_title)
        
        re_author = re.compile(RE_AUTHOR, re.MULTILINE)
        self.author = self.get_field_regex('cells[1].source[0]',re_author)

        self.description = self.get_field_all('cells[2].source')

        re_lineitem = re.compile(r'^\*\s+(.*)$',re.MULTILINE)
        self.references = self.get_field_markdown_list('References',re_lineitem)

        self.keywords = self.get_field_comma_separated_list('Keywords')
        self.requirements = self.get_field_comma_separated_list('Requirements')

    def get_image(self):
        """Get the image to use as thumbnail.

        :returns: None
        :rtype: None

        """
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
        """Validate the notebook.

        :returns: None
        :rtype: None

        """
        if not hasattr(self,'image'):
            raise NotebookInvalidException("No image",self)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        Notebook(sys.argv[1])
    else:
        print("Missing file")
