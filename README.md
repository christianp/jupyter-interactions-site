# Tools to build the jupyter-interactions website

This tool builds a website showing off Jupyter interactions, from [mikecroucher/jupyter-interactions](https://github.com/mikecroucher/jupyter-interactions).

**You can see the gallery at [mikecroucher.github.io/jupyter-interactions/](https://mikecroucher.github.io/jupyter-interactions/)**

Here's how to build the site:

* Clone this repository.
* Run `git submodule init` to retrive [jupyter-interactions](https://github.com/mikecroucher/jupyter-interactions)
* Copy `config.yml.dist` to `config.yml`, and modify the paths as required.
    * `build_path` is where the generated site should go.
    * `notebook_path` is the path to your clone of the jupyter-interactions repository
    * `notebook_runner_url` is the root of the URL to run notebooks - the notebook's name will be appended to this to make the link.
    * `ignore_notebooks` is a list of notebook files to ignore.
* Install the dependencies with 

        pip install -r requirements.txt
* To build the site, run

        python build_site.py
* If you want to have different configurations for local and production use, make a `config_prod.yml` and use the `--config` option to use that instead:

        python build_site.py --config=prod
* To automatically regenerate the site whenever a source file changes, use `--watch`:

        python build_site.py --watch
