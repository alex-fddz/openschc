Documenting Guidelines
**********************

Following the guidelines below when documenting the project would be appreciated.

Syntax
======

Sphinx's default syntax is called ReStructuredText.

Sphinx's documentation provides a `syntax guide <http://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html>`_.

The original RST documentation is available `here <http://docutils.sourceforge.net/rst.html>`_.

Building the documentation
==========================

The documentation is built using `Sphinx <https://www.sphinx-doc.org>`_.

After installing Sphinx (depending on your OS), you have to add the sphinx-doc bin directory to your PATH environment variable.

Type::

  sphinx-build --version

for a check.

Then you need to setup the Git environment.

We advise you to synchronize the OpenSCHC project in two separate directories.
One for the source code, synchronized with the branch you want to build the documentation for, another synchronized with the gh-pages branch in which the documentation will be stored.

An example of how to do this::

  $ git clone https://github.com/openschc/openschc.git
  $ cd openschc
  $ git checkout my_branch
  $ cd ..
  # create directory for compiled documentation
  $ mkdir openschc_doc
  $ cd openschc_doc
  $ git clone https://github.com/openschc/openschc.git html
  $ cd html
  $ git checkout gh-pages
  $ cd ../..

  $ tree
  .
  ├ openschc
  │   ├ _static
  │   ├ docs
  │   │   ├ _build
  │   │   ├ _static
  │   │   └ _templates
  │   └ src
  └ openschc_doc
      ├ doctrees
      └ html
          ├ _images
          ├ _sources
          └ _static

An important thing to do before building the documentation is to tell Sphinx where to build the documentation.
This information is provided in the Makefile that is located under the **docs** folder::

  $ cd openschc/docs
  $ head -n 10 Makefile
  # Minimal makefile for Sphinx documentation
  #
  
  # You can set these variables from the command line.
  SPHINXOPTS    =
  SPHINXBUILD   = sphinx-build
  SPHINXPROJ    = OpenSCHC
  SOURCEDIR     = .
  BUILDDIR      = ../../openschc_doc
  
Another good thing to do is add the Makefile to your .gitignore file in order to prevent your changes to be forced on everyone::

  $ pwd
  openschc/docs
  $ echo "docs/Makefile" >> ../.gitignore

Then you can build the documentation (in the master branch or your own development branch)::

  $ pwd
  openschc/docs
  $ make html

Normally the documentation will be built automatically, you can open it in your browser or push it to your remote gh-pages branch to publish the website::

  $ cd openschc_doc/html
  $ git add xxx
  $ git commit -m "meaningful comment"
  $ git push
