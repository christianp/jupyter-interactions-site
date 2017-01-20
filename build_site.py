import os
import jinja2
import shutil
from get_metadata import Notebook, NotebookInvalidException
from distutils.dir_util import copy_tree
from nbconvert.filters.markdown_mistune import markdown2html_mistune
import yaml
import codecs
import argparse
import time
import re
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import http.server

class EventHandler(FileSystemEventHandler):
    def __init__(self,site):
        self.site = site

    def dispatch(self,event):
        if not (os.path.isdir(event.src_path) or re.match(r'.*\d+$',event.src_path)):
            super(EventHandler,self).dispatch(event)

    def on_modified(self,event):
        print("File changed: {}".format(event.src_path))
        os.chdir(self.site.cwd)
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

        server_address = ('', 8000)
        httpd = http.server.HTTPServer(server_address, http.server.SimpleHTTPRequestHandler)
        httpd.timeout = 1
        self.cwd = os.getcwd()
        serve_path = os.path.join(self.cwd,self.build_path)
        try:
            while True:
                os.chdir(serve_path)
                httpd.handle_request()
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

class NotebookSite(Site):
    def __init__(self,*args,**kwargs):
        self.notebook_path = kwargs.get('notebook_path','.')
        self.ignore_notebooks = kwargs.get('ignore_notebooks',[])
        self.verbose = kwargs.get('verbose',False)
        self.config = kwargs
        super(NotebookSite,self).__init__(*args,**kwargs)
        self.load_notebooks()

    def load_notebooks(self):
        print("Loading notebooks...")
        self.notebooks = []

        for filename in os.listdir(self.notebook_path):
            name,ext = os.path.splitext(filename)
            if ext=='.ipynb' and filename not in self.ignore_notebooks:
                notebook = Notebook(filename, self.notebook_path)
                self.notebooks.append(notebook)

        num_valid = len([nb for nb in self.notebooks if nb.is_valid()])
        num_invalid = len(self.notebooks) - num_valid

        print('\n{} notebooks found.'.format(len(self.notebooks)))

        if num_invalid:
            print("1 notebook is invalid." if num_invalid==1 else '{} notebooks are invalid.'.format(num_invalid))
            print("To see error messages, open {}/errors.html\n".format(self.build_path))

    def build(self):
        print('Building in {}'.format(self.build_path))

        super(NotebookSite,self).build()

        context = {'config': self.config, 'notebooks':self.notebooks}
        self.make_file('index.html','index.html', context)
        self.make_file('errors.html','errors.html', context)

        print("Success!")

parser = argparse.ArgumentParser(description='Build the jupyter-interactions site')
parser.add_argument('--config',dest='config',default='',help='name of the config file to use')
parser.add_argument('--watch',action='store_true',dest='watch',default=False,help='Automatically rebuild when a file is changed')
parser.add_argument('--verbose',action='store_true',dest='verbose',default=False,help='Give more verbose output')

args = parser.parse_args()
config_file = 'config_{}.yml'.format(args.config) if args.config else 'config.yml'

config = yaml.load(open(config_file).read())
site = NotebookSite(verbose=args.verbose,**config)

if args.watch:
    site.build()
    print("Open http://localhost:8000 in your browser\n")
    site.watch()
else:
    site.build()
    print("Open {}/index.html in your browser".format(site.build_path))
