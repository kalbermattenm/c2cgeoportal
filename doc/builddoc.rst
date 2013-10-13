.. _build_doc:

Build this doc
==============

* Change to the ``doc`` directory
  
  .. prompt:: bash

      cd doc

* Create a virtual env

  .. prompt:: bash

      wget http://www.mapfish.org/downloads/virtualenv-1.4.5.py
      python virtualenv-1.4.5.py --distribute --no-site-packages env

* Activate the virtual env

  .. prompt:: bash

      source env/bin/activate

* Install requirements

  .. prompt:: bash

    pip install -r requirements.txt

* Build the doc

  .. prompt:: bash

    make html

The HTML should now be available in the ``_build/html`` directory.
