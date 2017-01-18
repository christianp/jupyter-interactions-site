# Tools to build the jupyter-interactions website

Here's how to build the site:

* Clone this repository
* Copy `config.yml.dist` to `config.yml`, and modify the paths as required.
    * `build_path` is where the generated site should go.
    * `notebook_path` is the local path to the jupyter-interactions repository
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
