RST Syntax Examples
===================

This file demonstrates common RST (reStructuredText) syntax patterns.

Headings
--------

RST uses underlines (and optionally overlines) to create headings:

Main Title
==========

Chapter Title  
-------------

Section Title
~~~~~~~~~~~~~

Subsection Title
^^^^^^^^^^^^^^^^

Sub-subsection Title
""""""""""""""""""""

Text Formatting
---------------

**Bold text** using double asterisks
*Italic text* using single asterisks
``Inline code`` using double backticks
This is normal paragraph text.

You can also use:

- :strong:`Strong emphasis` (alternative to bold)
- :emphasis:`Emphasis` (alternative to italic)
- :literal:`Literal text` (alternative to inline code)

Lists
-----

Bullet Lists
~~~~~~~~~~~~

* First item
* Second item

  - Nested item
  - Another nested item

* Third item

Numbered Lists  
~~~~~~~~~~~~~~

1. First numbered item
2. Second numbered item

   a. Nested letter item
   b. Another letter item

3. Third numbered item

Definition Lists
~~~~~~~~~~~~~~~~

Term 1
    Definition of term 1

Term 2
    Definition of term 2, which can span
    multiple lines if needed

Code Blocks
-----------

Simple code block with double colons::

    def hello_world():
        print("Hello, World!")
        return True

Code block with syntax highlighting:

.. code-block:: python

   from typing import List, Dict
   
   class ExampleClass:
       def __init__(self, name: str):
           self.name = name
       
       def greet(self) -> str:
           return f"Hello from {self.name}!"

.. code-block:: yaml

   # YAML example
   experiment:
     language: English
     agents:
       - name: Alice
         model: gpt-4.1-mini
         temperature: 0.3

.. code-block:: bash

   # Shell commands
   python main.py config/default.yaml
   pip install -r requirements.txt

Links and References
--------------------

External Links
~~~~~~~~~~~~~~

Visit `Python.org <https://python.org>`_ for more information.

You can also use: Python.org_

.. _Python.org: https://python.org

Internal References
~~~~~~~~~~~~~~~~~~~

See the `Code Blocks`_ section above.

You can reference sections by name: `Text Formatting`_

Cross-document references (in Sphinx):

- :doc:`api/core` - Link to another document
- :ref:`some-label` - Link to a labeled section
- :py:func:`my_module.my_function` - Link to Python function

Tables
------

Simple Table
~~~~~~~~~~~~

=====  =====  ======
   Inputs     Output
------------  ------
  A      B    A or B
=====  =====  ======
False  False  False
True   False  True
False  True   True
True   True   True
=====  =====  ======

Grid Table
~~~~~~~~~~

+------------------------+------------+----------+----------+
| Header row, column 1   | Header 2   | Header 3 | Header 4 |
| (header rows optional) |            |          |          |
+========================+============+==========+==========+
| body row 1, column 1   | column 2   | column 3 | column 4 |
+------------------------+------------+----------+----------+
| body row 2             | ...        | ...      |          |
+------------------------+------------+----------+----------+

CSV Table (Sphinx directive)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. csv-table:: Experiment Results
   :header: "Agent", "Principle", "Confidence", "Time (s)"
   :widths: 15, 30, 15, 10

   "Alice", "Maximizing Floor", "High", "23.4"
   "Bob", "Maximizing Average", "Medium", "18.7"
   "Carol", "Max Avg with Floor", "High", "31.2"

Admonitions (Call-out Boxes)
-----------------------------

.. note::
   This is a note admonition.
   It can span multiple lines and contain other RST elements.

.. warning::
   This is a warning about something important.

.. danger::
   This indicates something dangerous or critical.

.. tip::
   Here's a helpful tip for users.

.. important::
   This marks important information.

.. seealso::
   Related information can be found in other sections.

.. todo::
   This marks a todo item (requires sphinx.ext.todo extension).

Custom Admonitions
~~~~~~~~~~~~~~~~~~

.. admonition:: Custom Title
   
   You can create custom admonitions with any title.
   This is useful for project-specific call-outs.

Images and Figures
------------------

Simple Image
~~~~~~~~~~~~

.. image:: path/to/image.png
   :width: 400px
   :alt: Alternative text
   :align: center

Figure with Caption
~~~~~~~~~~~~~~~~~~~

.. figure:: path/to/figure.png
   :scale: 50%
   :alt: Figure description
   :align: center

   This is the figure caption. It can be quite long
   and span multiple lines if needed.

Sphinx-Specific Directives
---------------------------

Auto-documentation
~~~~~~~~~~~~~~~~~~

.. automodule:: mypackage.mymodule
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: MyClass
   :members:
   :special-members:
   :private-members:

.. autofunction:: my_function

Content Inclusion
~~~~~~~~~~~~~~~~~

.. include:: other_file.rst

.. literalinclude:: example.py
   :language: python
   :lines: 1-10
   :emphasize-lines: 3,5

Table of Contents
~~~~~~~~~~~~~~~~~

.. contents:: Table of Contents
   :local:
   :depth: 2

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   intro
   tutorial
   api/index

Modern Sphinx Extensions
------------------------

Tabs (sphinx-tabs)
~~~~~~~~~~~~~~~~~~

.. tabs::

   .. tab:: Python

      .. code-block:: python

         def example():
             return "Python code here"

   .. tab:: JavaScript

      .. code-block:: javascript

         function example() {
             return "JavaScript code here";
         }

   .. tab:: Shell

      .. code-block:: bash

         echo "Shell command here"

Design Elements (sphinx-design)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. grid:: 2

   .. grid-item-card:: Card Title 1
      
      Card content goes here with some text
      and maybe some code examples.

   .. grid-item-card:: Card Title 2
      
      Another card with different content.
      Cards are great for organizing information.

.. dropdown:: Click to expand

   This content is hidden until clicked.
   Great for FAQ sections or optional details.

.. button-ref:: some-reference
   :color: primary
   :outline:

   Click Me Button

Mermaid Diagrams
~~~~~~~~~~~~~~~~

.. mermaid::

   graph TD
       A[Start] --> B{Is it working?}
       B -->|Yes| C[Great!]
       B -->|No| D[Fix it]
       D --> B
       C --> E[End]

Comments and Substitutions
--------------------------

.. This is a comment - it won't appear in output

.. |project| replace:: Frohlich Experiment
.. |version| replace:: 2.0.1

You can use substitutions like |project| version |version|.

Footnotes and Citations
-----------------------

This text has a footnote [#f1]_ and a citation [Smith2020]_.

.. [#f1] This is the footnote text.

.. [Smith2020] Smith, J. (2020). "Documentation Best Practices." 
   Journal of Software Engineering, 15(3), 123-145.

Mathematical Expressions
------------------------

Inline math: :math:`a^2 + b^2 = c^2`

Block math:

.. math::

   \sum_{i=1}^{n} x_i = \frac{n(n+1)}{2}

Raw HTML (use sparingly)
------------------------

.. raw:: html

   <div style="color: red; font-weight: bold;">
   This is raw HTML content.
   </div>

Field Lists (Metadata)
----------------------

:Author: John Doe
:Version: 1.0
:Date: 2025-01-22
:Status: Draft

Advanced Features
-----------------

Option Lists
~~~~~~~~~~~~

-a            command-line option "a"
-b file       options can have arguments
--long        options can be long also
--input=file  long options can also have arguments

Literal Blocks with Options  
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python
   :linenos:
   :emphasize-lines: 2,3
   :caption: Example with line numbers

   def complex_function():
       # This line is emphasized
       # This line too
       return "result"

Cross-References
~~~~~~~~~~~~~~~~

.. _my-reference-label:

Section Referenced Elsewhere
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can reference this section using :ref:`my-reference-label`.

Glossary
~~~~~~~~

.. glossary::

   RST
      reStructuredText, a markup language

   Sphinx
      Documentation generator that uses RST

Use glossary terms with :term:`RST` and :term:`Sphinx`.

Production Tips
---------------

1. **File Extensions**: Use `.rst` for reStructuredText files
2. **Indentation**: Use spaces (not tabs), typically 3 spaces for directive content
3. **Line Length**: Keep lines under 79-100 characters when possible
4. **Blank Lines**: Use blank lines to separate sections clearly
5. **Preview**: Use Sphinx's auto-build feature to preview changes live

Common Pitfalls
---------------

.. warning::
   
   - **Indentation matters**: Directive content must be properly indented
   - **Underline length**: Must match or exceed title length exactly
   - **Blank lines**: Required before and after directives
   - **Special characters**: Need escaping in some contexts

Best Practices for Documentation
--------------------------------

1. **Structure**: Use consistent heading hierarchy
2. **Examples**: Include practical code examples
3. **Cross-references**: Link related sections together
4. **Audience**: Write for your target audience level
5. **Maintenance**: Keep examples up-to-date with code changes

This covers the most commonly used RST features. For advanced usage,
consult the official reStructuredText specification and Sphinx documentation.