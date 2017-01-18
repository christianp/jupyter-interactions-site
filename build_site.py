import os
import jinja2
import shutil
from get_metadata import Notebook
from distutils.dir_util import copy_tree
from markdown_mistune import markdown2html_mistune
import yaml
import codecs
import argparse
import time
import re
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class EventHandler(FileSystemEventHandler):
    def __init__(self,site):
        self.site = site

    def dispatch(self,event):
        if not re.match(r'.*\d+$',event.src_path):
            super(EventHandler,self).dispatch(event)

    def on_modified(self,event):
        print("File changed: {}".format(event.src_path))
        self.site.build()

class Site(object):
    def __init__(self,build_path='build',template_path='templates',static_path='static',site_context={},**kwargs):
        self.build_path = build_path
        try:
            os.mkdir(self.build_path)
        except FileExistsError:
            pass

        self.static_path = static_path

        self.site_context = site_context

        self.template_path = template_path
        self.env = jinja2.Environment(loader=jinja2.FileSystemLoader(self.template_path))
        self.env.filters['markdown'] = markdown2html_mistune

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

    def watch(self):
        observer = Observer()
        event_handler = EventHandler(self)

        for path in [self.template_path,self.static_path]:
            observer.schedule(event_handler,path,recursive=True)

        observer.start()
        print("Watching for changes...")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

class NotebookSite(Site):
    def __init__(self,notebook_path='.',*args,**kwargs):
        self.notebook_path = notebook_path
        self.ignore_notebooks = kwargs.get('ignore_notebooks',[])
        super(NotebookSite,self).__init__(*args,**kwargs)
        self.load_notebooks()

    def load_notebooks(self):
        print("Loading notebooks...")
        self.notebooks = []
        for filename in os.listdir(self.notebook_path):
            name,ext = os.path.splitext(filename)
            if ext=='.ipynb' and filename not in self.ignore_notebooks:
                notebook = Notebook(os.path.join(self.notebook_path,filename),filename)
                self.notebooks.append(notebook)

    def build(self):
        print('Building in {}'.format(self.build_path))

        super(NotebookSite,self).build()
        site.make_file('index.html','index.html',{'notebooks':self.notebooks})

        for notebook in self.notebooks:
            pass

        print("Success!")

parser = argparse.ArgumentParser(description='Build the jupyter-interactions site')
parser.add_argument('--config',dest='config',default='',help='name of the config file to use')
parser.add_argument('--watch',action='store_true',dest='watch',default=False,help='Automatically rebuild when a file is changed')

args = parser.parse_args()
config_file = 'config_{}.yml'.format(args.config) if args.config else 'config.yml'

config = yaml.load(open('config.yml').read())
site = NotebookSite(**config)
print('{} notebooks found\n'.format(len(site.notebooks)))

if args.watch:
    site.watch()
else:
    site.build()
    print("Open {}/index.html in your browser".format(site.build_path))
