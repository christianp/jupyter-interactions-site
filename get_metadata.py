import codecs
import json
import os.path
import re
import sys
import inspect

import jmespath

def handle_svg(data):
    source = ''.join(data)
    return source

def handle_png(data):
    return '<img src="data:image/png;base64,{}">'.format(data)

image_handlers = {
    'image/svg+xml': handle_svg,
    'image/png': handle_png,
}

def truncate(text, length=30):
    text = str(text)
    if len(text)>length-4:
        return text[:length-4]+' ...'
    else:
        return text

class Field(object):
    is_valid = False
    notebook = None

    def __init__(self, name, path, validator=None, *args, **kwargs):
        self.__init_args = args
        self.__init_kwargs = kwargs
        self.name = name
        self.path = path
        self.extra_validator = validator

    def bind(self,notebook):
        f2 = type(self)(self.name,self.path,validator=self.extra_validator,*self.__init_args,**self.__init_kwargs)
        f2.notebook = notebook
        return f2

    def __str__(self):
        try:
            v = self.value
            return 'Field {}: {}'.format(self.name, truncate(v))
        except FieldInvalidException as e:
            return 'Field {} (invalid): {}'.format(self.name, e)

    def __repr__(self):
        return str(self)

    @property
    def value(self):

        try:
            v = self.load()
            v = self.clean(v)
            if self.extra_validator:
                v = self.extra_validator(v)
            return v
        except FieldInvalidException as e:
            e.field = self
            raise e

    def load(self):
        """
            Load the raw value for this field from the notebook
        """
        return jmespath.search(self.path, self.notebook.data)

    def clean(self, v):
        """
            Validate and process the value loaded from the notebook
        """
        return v

class MultilineField(Field):
    def load(self):
        lines = super(MultilineField, self).load()
        try:
            return ''.join(lines)
        except TypeError:
            raise FieldInvalidException(lines, "{} is {}, not an iterable".format(self.path,type(lines)))

class FieldWithHeaderMixin(object):
    re_header = re.compile('^(#+)\s+(.*)$', re.MULTILINE)

    def __init__(self, *args, **kwargs):
        super(FieldWithHeaderMixin, self).__init__(*args, **kwargs)
        self.header_level = kwargs.get('header_level', 1)
        self.return_header = kwargs.get('return_header', False)

    def clean(self, v):
        v = super(FieldWithHeaderMixin, self).clean(v)

        header_level_md = '#'*self.header_level

        m = self.re_header.match(v)
        if not m:
            raise FieldInvalidException(v, "must begin with a header", suggestion = '# {}'.format(v))
        if len(m.group(1)) != self.header_level:
            raise FieldInvalidException(v,
                "header level must be {}".format(header_level_md), 
                suggestion='{} {}'.format(header_level_md, m.group(2))
            )

        if self.return_header:
            text = m.group(2)
            if not text:
                raise FieldInvalidException(v, "header is empty", suggestion = '{} xxx'.format(header_level_md))
            return m.group(2)
        else:
            return v[m.end()+1:]

class SingleLineHeaderField(FieldWithHeaderMixin, Field):
    pass

class ListFieldMixin(object):
    re_list_item = re.compile(r'^[-*]\s+(.*)$', re.MULTILINE)

    def clean(self, v):
        v = super(ListFieldMixin, self).clean(v)
        return self.re_list_item.findall(v)

class ListFieldWithHeader(ListFieldMixin, FieldWithHeaderMixin, MultilineField):
    pass

class CommaSeparatedListFieldMixin(object):
    def clean(self, v):
        v = super(FieldCommaSeparatedListMixin, self).clean(v)
        return v.split(',')

class ImageField(Field):
    def clean(self, v):
        for output in v:
            mime_types = [k for k in output if k in image_handlers]
            if len(mime_types):
                mime_type = mime_types[0]
                image_data = output[mime_type]
                image_tag = image_handlers[mime_type](image_data)
                return {
                    'mime_type': mime_type,
                    'image_data': image_data,
                    'html': image_tag,
                }
        raise FieldInvalidException(v,'none of the supported image types present: {}'.format(', '.join(image_handlers.keys())))

def author_validator(text):
    re_author = re.compile(r'^Author:\s+(.*)$')
    m = re_author.match(text)
    if not m:
        raise FieldInvalidException(v, "wrong format", suggestion="Author: {}".format(text))
    else:
        return m.group(1)

def indent(text,level='\t'):
    return '\n'.join(level+line for line in text.split('\n'))

class FieldInvalidException(Exception):
    def __init__(self, value, message, suggestion='', field=None):
        self.value = value
        self.message = message
        self.suggestion = suggestion
        self.field = field

    def __str__(self):
        s = "{} is invalid: {}".format(self.field.name, self.message)
        if self.suggestion:
            s += "\nTry:\n\t{}\nCurrent value:\n{}".format(self.suggestion, indent(self.value))
        return s

class NotebookInvalidException(Exception):
    """Exception class for Notebook class"""
    def __init__(self, errors, notebook):
        self.notebook = notebook
        self.errors = errors

    def __str__(self):
        return 'Notebook "{}" is invalid:\n{}'.format(self.notebook.filename, '\n'.join('* {}'.format(e) for e in self.errors))

class Notebook(object):
    title = SingleLineHeaderField('title', 'cells[0].source[0]', header_level=1, return_header=True)
    author = SingleLineHeaderField('author', 'cells[1].source[0]', header_level=2, return_header=True, validator=author_validator)
    description = MultilineField('description', 'cells[2].source')
    references = ListFieldWithHeader('references', 'cells[4].source', header_level=3)
    keywords = ListFieldWithHeader('keywords', 'cells[5].source', header_level=3)
    requirements = ListFieldWithHeader('requirements', 'cells[6].source', header_level=3)
    image = ImageField('image', 'cells[].outputs[].data')

    """Represent Notebook"""
    def __init__(self, filename, file_dir="."):
        """Init Notebook class.

        :param filename: Name of the Jupyter Notebook file.
        :param file_path: TODO
        :returns: None
        :rtype: None

        """
        self.filename = filename
        self.data = json.loads(
            codecs.open(
                os.path.join(file_dir, filename),
                encoding='utf-8'
            ).read()
        )

        self.make_fields()

    def get_fields(self):
        for member, value in inspect.getmembers(self):
            if isinstance(value, Field):
                yield value

    def make_fields(self):
        for field in self.get_fields():
            setattr(self,field.name, field.bind(self))

    def get_image(self):
        """Get the image to use as thumbnail.

        :returns: None
        :rtype: None

        """
        for output in jmespath.search('cells[].outputs[].data', self.data):
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

        errors = []

        for field in self.get_fields():
            try:
                field.value
            except FieldInvalidException as e:
                try:
                    str(e)
                except Exception:
                    print(field.name)
                errors.append(e)

        if len(errors):
            raise NotebookInvalidException(errors, self)

        return True

    def is_valid(self):
        try:
            self.validate()
            return True
        except NotebookInvalidException:
            return False

    def errors(self):
        try:
            self.validate()
            return ''
        except NotebookInvalidException as e:
            return str(e)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        nb = Notebook(sys.argv[1])
        if nb.is_valid():
            print("valid")
    else:
        print("Missing file")
