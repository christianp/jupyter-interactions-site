import os
import jinja2
import shutil
from get_metadata import Notebook
from distutils.dir_util import copy_tree
import yaml
import codecs
import argparse

class Site(object):
    def __init__(self,build_path='build',template_path='templates',static_path='static',site_context={}):
        self.build_path = build_path
        try:
            os.mkdir(self.build_path)
        except FileExistsError:
            pass

        self.static_path = static_path

        self.site_context = site_context

        self.template_path = template_path
        self.env = jinja2.Environment(loader=jinja2.FileSystemLoader(self.template_path))

    def make_file(self,template_name,destination,context):
        template = self.env.get_template(template_name)
        ctx = {}
        ctx.update({'site':self.site_context})
        ctx.update(context)
        codecs.open(os.path.join(self.build_path,destination),'w',encoding='utf-8').write(template.render(ctx))

    def copy_static(self):
        copy_tree(self.static_path, os.path.join(self.build_path,'static'))

    def build(self):
        self.copy_static()

class NotebookSite(Site):
    def __init__(self,notebook_path='.',*args,**kwargs):
        self.notebook_path = notebook_path
        super(NotebookSite,self).__init__(*args,**kwargs)
        self.load_notebooks()

    def load_notebooks(self):
        self.notebooks = []
        for filename in os.listdir(self.notebook_path):
            name,ext = os.path.splitext(filename)
            if ext=='.ipynb':
                notebook = Notebook(os.path.join(self.notebook_path,filename),filename)
                self.notebooks.append(notebook)

    def build(self):
        super(NotebookSite,self).build()
        site.make_file('index.html','index.html',{'notebooks':self.notebooks})

        for notebook in self.notebooks:
            pass

parser = argparse.ArgumentParser(description='Build the jupyter-interactions site')
parser.add_argument('--config',dest='config',default='',help='name of the config file to use')

args = parser.parse_args()
config_file = 'config_{}.yml'.format(args.config) if args.config else 'config.yml'

config = yaml.load(open('config.yml').read())
site = NotebookSite(**config)
site.build()
